---
name: secure-python-release-pipeline
description: >-
  Build, verify, and publish a Python package from GitHub Actions securely.
  Splits sdist and wheel builds so a broken sdist is caught (wheels build FROM
  the sdist), publishes to PyPI via a Trusted Publisher (OIDC, no API token) in
  a separate download-and-upload job, uses cibuildwheel for C/C++/Rust/platlib
  wheels, and hardens the pipeline (minimal permissions, SHA-pinned actions,
  Dependabot with cooldown + CodeQL grouping, no cache on release, zizmor audit,
  attestations). Use when asked to set up or review CI/CD, release to PyPI, or
  add wheels/trusted publishing.
---

# Secure build-and-release pipeline for Python packages (GitHub Actions)

**Status: Experimental** — assembled from two real shipping projects (see
`reference/templates.md`: pycxxfilt for compiled/cibuildwheel, zipwire for
pure-Python) plus the upstream PyPI/zizmor/cibuildwheel docs. Follow it, adapt to
your project, and have a human review permissions and the PyPI publisher config.

A good pipeline proves the release is buildable, reproducible, and untampered:
build the sdist, build wheels **from that sdist**, verify, then publish with
short-lived OIDC credentials from a locked-down job. Work in the order below;
copy-paste-ready workflows are in `reference/templates.md`, the rationale for
each hardening rule in `reference/hardening.md`.

## Authoritative sources (if this skill disagrees with them, they win)

- PyPI Trusted Publishers —
  <https://docs.pypi.org/trusted-publishers/> (using:
  <https://docs.pypi.org/trusted-publishers/using-a-publisher/>)
- `pypa/gh-action-pypi-publish` — <https://github.com/pypa/gh-action-pypi-publish>
- cibuildwheel — <https://cibuildwheel.pypa.io/en/stable/>
- zizmor — <https://docs.zizmor.sh/> (usage/integrations)
- GITHUB_TOKEN permissions —
  <https://docs.github.com/actions/security-guides/automatic-token-authentication>
- PEP 517 (build isolation) — <https://peps.python.org/pep-0517/>

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Pick the shape: pure-Python vs compiled

```bash
grep -nE 'ext_modules|extension_module|cffi|setuptools-rust|maturin' pyproject.toml setup.py meson.build 2>/dev/null
```

- **Pure-Python** (no compiled code) → one `bdist_wheel`; a single `noarch`
  wheel. Build with `uv build` (or `python -m build`) — zipwire template.
- **Compiled / platlib** (C/C++/CUDA/Rust extension) → many wheels across
  OS × arch × Python/abi. **Use cibuildwheel** — it handles the build matrix,
  `manylinux`/`musllinux` containers, and repair (`auditwheel`/`delocate`).
  Don't hand-roll a per-platform matrix (pycxxfilt template).

## 2. Split sdist and wheel into separate jobs — build wheels from the sdist

This is the core correctness check. A wheel built straight from your checkout can
succeed while the **sdist** silently omits a needed file (a header, a
`meson.build`, a generated source) — PEP 517 builds run isolated, so anything not
packaged is simply absent. Catch it by making the wheel job consume the sdist:

1. **sdist job:** `uv build --sdist` (or `python -m build --sdist`); upload
   `dist/*.tar.gz` as an artifact.
2. **wheel job(s):** download the sdist artifact and build **from the tarball**,
   not the repo:
   - compiled: `pypa/cibuildwheel` with `package-dir: <path-to-sdist.tar.gz>`;
   - pure-Python: `uv build --wheel <sdist.tar.gz>` (or `python -m build --wheel` / `pip wheel`).

If the sdist is missing a file, the wheel build fails here instead of shipping a
broken sdist. (Shortcut for simple projects:
`hynek/build-and-inspect-python-package` does sdist → wheel-from-sdist → inspect
in one step — pycxxfilt uses it in CI.)

## 3. Verify before publishing

Add a gate job that depends on all wheel jobs and downloads every artifact:
`twine check dist/*`, and for compiled wheels assert the ABI/platform tags
(`abi3audit` for abi3, and confirm `manylinux`/`macos`/`win` tags). Only a green
verify job feeds the publish job.

## 4. Publish with a Trusted Publisher (OIDC, no token), in its own job

Configure the publisher **on PyPI** first (project → Publishing): GitHub owner,
repository, the **workflow filename** (e.g. `release.yml`), and the **environment
name** (e.g. `pypi`). Then a minimal publish job:

```yaml
publish:
  needs: [sdist, wheels, verify]        # everything must be green first
  runs-on: ubuntu-latest
  environment: pypi                     # matches the PyPI publisher config
  permissions:
    id-token: write                     # MANDATORY for OIDC trusted publishing (and signs attestations)
    contents: read
  steps:
    - uses: actions/download-artifact@<sha>   # collect sdist + all wheels
      with: { path: dist, merge-multiple: true }
    - uses: pypa/gh-action-pypi-publish@<sha>  # pin >=v1.11.0; no username/password/token
```

Keep this in a **separate job** so nothing that touches source or runs your build
code holds `id-token: write`. This job runs **no `checkout` and no build** — only
`download-artifact` then `pypi-publish` — so the one credentialed job executes the
least code and consumes no untrusted source. Pass the sdist/wheels between jobs as
**artifacts** (`upload`/`download-artifact`), not via the build cache, which is
best-effort and poisonable (see §6). No API tokens anywhere — there is no persistent
credential to steal or abuse; OIDC mints a short-lived, workflow-scoped token at
publish time. PEP 740 **provenance** is generated **by default** for
Trusted-Publisher uploads (since `gh-action-pypi-publish` v1.11.0 — so pin that or
newer; `attestations: false` opts out): a Sigstore-signed record of the org, repo,
commit SHA, ref, and workflow that built each artifact, logged in Sigstore's
append-only **Rekor** transparency log so consumers can verify origin. The same
`id-token: write` covers both publishing and signing — **no `attestations: write`
permission is needed** (that scope belongs to GitHub's separate native-attestation
API, not this flow). For staging, add `with: repository-url:
https://test.pypi.org/legacy/`.

**Optional — also attach artifacts to a GitHub Release with native provenance.**
If you publish the sdist + wheels as a **GitHub Release** (not just to PyPI), give
those GitHub-hosted files verifiable provenance too. Do it in a **separate job** so
the extra scopes never land on the PyPI publish job:

```yaml
github-release:
  needs: [verify]                       # same green gate as publish
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  permissions:
    contents: write                     # create the Release + upload assets
    id-token: write                     # Sigstore signing for the attestation
    attestations: write                 # write GitHub-native SLSA provenance
  steps:
    - uses: actions/download-artifact@<sha>          # no checkout — artifacts only
      with: { path: dist, merge-multiple: true }
    - uses: actions/attest-build-provenance@<sha>    # GitHub-side provenance
      with: { subject-path: "dist/*" }
    - uses: softprops/action-gh-release@<sha>        # or `gh release create`
      with: { files: dist/* }
```

This is the **only** place `attestations: write` is warranted — it feeds GitHub's
native-attestation API (`actions/attest-*`), verifiable with `gh attestation
verify`, and is entirely separate from the PyPI PEP 740 flow above. Keeping it in
its own job preserves the privilege gradient: the PyPI publish job stays
`id-token: write`-only. Skip this job if you publish to PyPI alone.

## 5. Least privilege everywhere

- Set `permissions: {}` at the **workflow top level** (deny-all default), then
  grant the minimum **per job** — most jobs need only `contents: read`.
- `id-token: write` lives **only** in the publish job — and it's the *only* write
  scope that job needs (it also covers attestation signing). The one exception is
  the optional GitHub-Release job (§4), which adds `contents: write` +
  `attestations: write` for native provenance; keep it separate so those scopes
  never touch the PyPI publish job.
- **Privilege gradient across the jobs** (one workflow, jobs chained by `needs:`).
  Each downstream job does less: the sdist job clones and builds; the wheel jobs
  consume the sdist (no clone needed); the publish job only fetches artifacts and
  uploads. Privilege is inverted — the *most*-privileged job (`id-token: write`,
  PyPI upload) runs the *fewest* and least-sensitive steps and touches no source,
  minimizing its attack surface.
- `actions/checkout` with `persist-credentials: false` (don't leave the token in
  `.git/config`).
- Add a `concurrency` group to cancel superseded runs.

Rationale and the full permission map: `reference/hardening.md`.

## 6. Pin actions, and don't cache release builds

- **SHA-pin every action** (`uses: owner/action@<40-char-sha>  # vX.Y.Z`), not a
  moving tag — a tag can be repointed at malicious code.
- **Keep pins fresh with Dependabot, with a cooldown.** Add
  `.github/dependabot.yml` for the `github-actions` (and `pip`) ecosystems, and
  set `cooldown: { default-days: 7 }` so an update PR waits a week after a release
  — long enough for a compromised or broken version to be caught/yanked before
  you adopt it. **Group** the multi-action CodeQL bundle so its sub-actions bump
  together in one PR: `groups: { codeql: { patterns: ["github/codeql-action/*"] } }`.
  Full config in `reference/templates.md` (§E).
- **No build cache on release.** A poisoned cache entry can inject artifacts into
  a release. Disable caching when building tagged releases:
  `astral-sh/setup-uv` with `enable-cache: false`; skip `actions/cache` on tags
  (`if: ${{ !startsWith(github.ref, 'refs/tags/v') }}`). Cache freely in PR/CI
  where the output isn't published. Use per-run cache keys
  (`key: …-${{ github.run_id }}`) so runs can't poison each other.
- **Lock deps and add a resolution cooldown.** Commit a lockfile (`uv.lock` or a
  pip-tools/`pylock.toml` equivalent) so CI, dev, and build deps resolve to fixed
  hashes, and set a **≥3-day resolution cooldown** so a freshly published version
  can't be pulled in before the community vets it — uv's `exclude-newer` (e.g.
  `[tool.uv] exclude-newer = "3 days"`). This is the resolver-side twin of the
  Dependabot cooldown above. Detail in `reference/hardening.md`.

## 7. Audit the pipeline with zizmor

zizmor is a static analyzer for GitHub Actions (finds injection sinks, excessive
permissions, unpinned actions, credential persistence). Run it two ways:

- **CI job** — `zizmorcore/zizmor-action@<sha>`; uploads SARIF to code scanning
  (needs `security-events: write`, `contents: read`, `actions: read`). SARIF mode
  exits 0 even with findings, so gate merges with a ruleset, not the checkmark.
- **Locally / pre-commit** — `uvx zizmor .` (or the
  `github.com/zizmorcore/zizmor-pre-commit` hook, id `zizmor`). `--persona=pedantic`
  adds code smells; `--offline` for no-network audits.

Optionally add **actionlint** for the *correctness* class zizmor doesn't cover —
shellcheck on `run:` scripts, invalid `needs`/matrix/`runs-on` references, and
malformed `${{ }}` expressions. It's complementary (security vs syntax), but a Go
tool with no `uvx` install. Prefer a prebuilt binary in a CI job (rhysd ships
release binaries and a `download-actionlint.bash` script) over the
`rhysd/actionlint` pre-commit hook, which compiles from source (`language:
golang`) and needs a Go toolchain locally.

Fix what they flag before shipping. Templates in `reference/templates.md`.

## 8. Dynamic versioning ties the release together

If the version comes from VCS/git tags (see `port-to-scikit-build-core` /
`port-to-meson-python`), **VCS versioning and tag-triggered releases work
together**:

- Trigger the release on the tag push (`on: push: tags: ["v*"]`); the tag *is*
  the version source.
- Checkout with `fetch-depth: 0` so the version tool can see tags (shallow
  clones hide them).
- The **sdist job freezes the resolved version into `PKG-INFO`**. Because step 2
  builds every wheel from that one sdist, the sdist and all wheels carry the
  **identical** version with no per-wheel git access needed — one source of
  truth, consistent across the whole release.

## Definition of done

Tag-triggered workflow builds an sdist, builds all wheels **from that sdist**,
verifies them, and publishes via a Trusted Publisher from a dedicated
`id-token: write` job; `permissions: {}` at top level with minimal per-job
grants; all actions SHA-pinned; no cache on release builds; zizmor runs clean (or
findings triaged); sdist + wheels share one VCS-derived version.
