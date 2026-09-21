# Hardening rationale

Why each rule in `SKILL.md` exists, and the threat it addresses. Sources:
[GitHub token permissions](https://docs.github.com/actions/security-guides/automatic-token-authentication),
[PyPI trusted publishers](https://docs.pypi.org/trusted-publishers/),
[zizmor audits](https://docs.zizmor.sh/audits/),
[OpenSSF Scorecard](https://github.com/ossf/scorecard).

## Permission map

`permissions: {}` at the workflow top level makes the default **deny-all**, so a
job with no `permissions:` block gets nothing. Grant the minimum per job:

| Job | Permissions | Why |
| --- | --- | --- |
| build / test / lint | `contents: read` | Read the checkout. Nothing else. |
| sdist / wheels | `contents: read` | Build only; never needs write or id-token. |
| verify | `contents: read` | Inspect artifacts. |
| zizmor | `security-events: write`, `contents: read`, `actions: read` | Upload SARIF to code scanning. |
| **publish** | `id-token: write`, `contents: read` | OIDC token for PyPI; the same identity also signs PEP 740 attestations. |

The **publish job is the only one** with `id-token: write`. Isolating it means no
job that checks out untrusted code or runs your build can mint a PyPI credential.
Note there is **no `attestations: write`** here: PEP 740 attestations sign with the
publish OIDC identity, so `id-token: write` is sufficient. `attestations: write` is
a *different* permission for GitHub's native artifact-attestation API
(`actions/attest-build-provenance`), which this pipeline doesn't use — granting it
would be an unused, unnecessary write scope in the most privileged job.

## Why build wheels from the sdist (PEP 517 isolation)

PEP 517 builds happen in an isolated environment from a source tree. A wheel
built from your working checkout can pick up files that are present locally but
**not listed in the sdist** (headers, `meson.build`/`CMakeLists.txt`, generated
sources, data files). Those wheels ship fine, but anyone doing
`pip install --no-binary` or building on an unsupported platform gets a broken
sdist. Building every wheel *from the sdist tarball* (cibuildwheel
`package-dir=<sdist>`, or `uv build --wheel <sdist>` / `python -m build --wheel <sdist>`) turns a missing-file
bug into a red CI job before release.

## Trusted publishers vs API tokens

A long-lived PyPI API token stored as a secret is a standing liability: it leaks
via logs, malicious dependencies, or a compromised action, and it grants upload
until manually revoked. **There is no persistent credential to steal or abuse.** A
**Trusted Publisher** uses GitHub's OIDC provider to mint a **short-lived,
workflow-scoped** credential at publish time — nothing to store, nothing to leak,
automatically bound to the configured repo + workflow + environment, and expiring
minutes later. `id-token: write` is mandatory for the OIDC exchange. Pair it with
a protected GitHub **Environment** (`environment: pypi`) so releases can require a
reviewer and be restricted to tag refs.

## Attestations (PEP 740)

Since `gh-action-pypi-publish` **v1.11.0**, a **digital attestation** is generated
for each artifact **by default** on Trusted-Publisher uploads and published
alongside the release (pin ≥ v1.11.0; `attestations: false` opts out — no
`attestations: write` permission is involved). The attestation is signed
**provenance** — it records where the
artifact came from: the **org/owner, project/repo, the exact git commit SHA, the
tag or branch ref, and the workflow** that built and published it. Consumers (and
PyPI's own UI) can verify the artifact was produced by your pipeline from that
commit, not re-uploaded or built elsewhere.

Signing uses **Sigstore**: a short-lived certificate is issued from the same OIDC
identity, and the signing event is recorded in **Rekor, Sigstore's append-only
public transparency log**. Because the log is append-only and publicly auditable,
a signature can't be forged or quietly backdated after the fact — anyone can
confirm the artifact was signed by your workflow's identity at release time.

To verify from the *consumer* side, Trail of Bits' **`pypi-attestations`** CLI
(`uvx pypi-attestations verify …`) checks a downloaded artifact's PEP 740
attestation against an expected signer identity (the repo + workflow), so a
downstream can gate on provenance, not just trust PyPI's UI. Note this is distinct
from `gh attestation verify`, which validates GitHub's *native* build-provenance
attestations — a different format from the PEP 740 records this pipeline
publishes.

## SHA-pin every action

`uses: owner/action@v4` follows a **mutable tag** — the owner (or an attacker who
compromises the repo) can repoint `v4` at new code, which then runs with your
job's permissions. Pin to a full 40-char commit SHA with the version in a comment
(`@d3c42e…  # v7.0.1`); the SHA is immutable. Let Dependabot/Renovate propose
bumps so pins stay current without becoming stale.

## Dependabot: cooldown + grouping

SHA-pinning only helps if the pins are maintained; Dependabot is what keeps them
moving. Two settings make it safer and quieter (`reference/templates.md` §E):

- **`cooldown: { default-days: 7 }`** — an update PR is held for a week after the
  upstream release. Adopting a version the instant it ships is a supply-chain
  risk: a compromised or broken release is often caught and yanked within days.
  The cooldown buys that window while still keeping you current. It complements
  pinning — you get a fresh, immutable SHA, just not a *brand-new* one.
- **`groups`** — collapses related bumps into one PR. CodeQL is the canonical
  case: `github/codeql-action/init`, `/analyze`, `/autobuild` are separate actions
  that must move in lockstep, so group them under
  `patterns: ["github/codeql-action/*"]`. Some projects group *all* action bumps
  (`patterns: ["*"]`) into a single weekly PR to cut review churn.

## No cache on release builds

Build caches (`actions/cache`, `setup-uv` cache, ccache) are writable by any run,
including PR runs from forks. A poisoned cache entry can inject code or artifacts
into a later build — **cache poisoning**. For anything that gets published:

- `astral-sh/setup-uv` → `enable-cache: false`.
- `actions/cache` → skip on tags: `if: ${{ !startsWith(github.ref, 'refs/tags/v') }}`.
- Where you do cache (PR/CI), use a **per-run key** (`…-${{ github.run_id }}`)
  with `restore-keys` for warm starts, so one run can't overwrite another's entry.

Caching in non-publishing CI is fine and worth it; the rule is specifically:
*the bits you ship are built with no cache.*

## `persist-credentials: false`

By default `actions/checkout` writes the `GITHUB_TOKEN` into `.git/config`, where
any later step (including a malicious dependency) can read it. Set
`persist-credentials: false` unless a step genuinely needs to push with that
token.

## Other guardrails

- **`concurrency`** with `cancel-in-progress: true` stops superseded runs from
  racing (and from double-publishing).
- **`zizmor`** catches these mechanically: template-injection sinks
  (`${{ github.event.* }}` in `run:`), overprovisioned permissions, unpinned
  actions, credential persistence, dangerous `pull_request_target`. Run it in CI
  *and* pre-commit.
- **OpenSSF Scorecard** (`ossf/scorecard-action`) gives a broader supply-chain
  score (branch protection, pinned deps, token perms) — both example repos ship a
  `scorecard.yml`. Complementary to zizmor, not a replacement.
- **CodeQL** for the package's own source (both repos ship `codeql.yml`).
- **Artifact retention.** `actions/upload-artifact` keeps the built sdist/wheels
  for the repo's default window (up to 90 days). The release artifacts only need
  to survive until the publish job downloads them, so set a short
  `retention-days` (e.g. `1`) — a smaller window for a stray artifact to be pulled
  into a later build or leaked.
- **Pin the build dependencies too.** SHA-pinning covers *actions*, but the PEP
  517 build still resolves `build-system.requires` from PyPI at build time. For a
  fully reproducible, tamper-evident build, install those from a hash-pinned
  constraints file (`pip install --require-hashes` / `uv pip install
  --require-hashes`, or `PIP_CONSTRAINT` pointing at a hashed lockfile) so a
  compromised build backend can't slip in. Keep it maintained the same way as the
  action pins (Dependabot/Renovate) — a pin, never an upper cap.
- **Commit a lockfile with a resolution cooldown.** For the dependencies you
  install (CI, dev, and hash-pinned build tools), commit a lockfile — `uv.lock`,
  or a pip-tools/`pylock.toml` equivalent — so every run resolves to the same
  hashes. Pair it with a **resolution cooldown** so a freshly published (possibly
  compromised or broken) version isn't pulled in the moment it lands: uv's
  [dependency cooldowns](https://docs.astral.sh/uv/concepts/resolution/#dependency-cooldowns)
  reuse `exclude-newer` (with `exclude-newer-package` for per-package overrides) —
  set a duration of **≥3 days**, e.g. `[tool.uv] exclude-newer = "3 days"`. The
  timestamp is baked into the lockfile and only advances on an explicit
  `--upgrade`/`--refresh`. This is the resolver-side twin of the Dependabot
  cooldown above — one delays bump *PRs*, the other delays what a *resolve*
  accepts.
