# Workflow templates

Condensed, annotated from two real shipping projects. **The `@<sha>` pins and
`# vX.Y.Z` comments are illustrative** — pin to the current release of each action
and let Dependabot/Renovate bump them; never copy an old SHA blindly.

- Pure-Python release → <https://github.com/tiran/zipwire/tree/main/.github>
  and <https://github.com/tiran/retread/tree/main/.github>
- Compiled / cibuildwheel → <https://github.com/tiran/pycxxfilt/tree/main/.github>

## A. Pure-Python release (`release.yml`)

Tag-triggered; two jobs (build, publish). Note `permissions: {}` at top,
`enable-cache: false`, `persist-credentials: false`, OIDC publish job.

```yaml
name: Release
on:
  push:
    tags: ["v*"]

permissions: {}                       # deny-all default; grant per job

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<sha>  # v7.0.1
        with:
          persist-credentials: false
          fetch-depth: 0              # tags visible → VCS versioning works
      - uses: astral-sh/setup-uv@<sha>
        with:
          enable-cache: false         # no cache on release (anti-poisoning)
      - run: uv build                 # builds sdist, then wheel FROM the sdist
      - uses: actions/upload-artifact@<sha>
        with: { name: dist, path: dist/ }

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi                 # matches the PyPI trusted-publisher config
    permissions:
      id-token: write                 # OIDC — the ONLY permission this job needs; signs attestations too
    steps:
      - uses: actions/download-artifact@<sha>
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@<sha>   # >=v1.11.0; no token; PEP 740 attestations on by default
```

`uv build` (and `python -m build`) with no args build the sdist first, then build
the wheel **from that sdist** — that already exercises PEP 517 isolation. For an
explicit split, build the sdist in one job and `uv build --wheel <sdist>` (or
`python -m build --wheel <sdist>`) in another (mirrors template B).

## B. Compiled / platlib release with cibuildwheel (`build.yml`)

sdist job → wheel matrix that builds **from the sdist** → verify → publish. Only
the shape is shown; drop OSes/arches you don't ship.

```yaml
name: Build & Publish
on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
  workflow_dispatch:

permissions: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sdist:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@<sha>
        with:
          persist-credentials: false
          fetch-depth: 0                       # tags for VCS versioning
      - uses: astral-sh/setup-uv@<sha>
        with: { enable-cache: false }
      - run: uv build --sdist
      - uses: actions/upload-artifact@<sha>
        with: { name: sdist, path: dist/*.tar.gz }

  wheels-linux:
    needs: sdist
    runs-on: ${{ matrix.runs-on }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - { arch: x86_64,  runs-on: ubuntu-latest }
          - { arch: aarch64, runs-on: ubuntu-24.04-arm }
    steps:
      - uses: actions/download-artifact@<sha>
        with: { name: sdist, path: dist }
      - id: sdist
        run: echo "path=$(ls dist/*.tar.gz)" >> "$GITHUB_OUTPUT"
        shell: bash
      # Release builds skip the cache to prevent cache poisoning of artifacts.
      - if: ${{ !startsWith(github.ref, 'refs/tags/v') }}
        uses: actions/cache@<sha>
        with:
          path: ${{ github.workspace }}/.ccache
          key: ccache-linux-${{ matrix.arch }}-${{ github.run_id }}   # per-run key
          restore-keys: ccache-linux-${{ matrix.arch }}-
      - uses: pypa/cibuildwheel@<sha>
        with:
          package-dir: ${{ steps.sdist.outputs.path }}   # ← build FROM the sdist
        env:
          CIBW_ARCHS_LINUX: ${{ matrix.arch }}
      - uses: actions/upload-artifact@<sha>
        with: { name: wheels-linux-${{ matrix.arch }}, path: wheelhouse/*.whl }

  # wheels-macos / wheels-windows: same download-sdist → cibuildwheel
  # package-dir=<sdist> shape, with CIBW_ARCHS_MACOS / CIBW_ARCHS_WINDOWS.

  verify:
    needs: [wheels-linux]               # + macos/windows jobs
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/download-artifact@<sha>
        with: { path: wheelhouse, pattern: wheels-*, merge-multiple: true }
      - run: uvx twine check wheelhouse/*.whl
      # abi3 wheels: uvx abi3audit wheelhouse/*.whl

  publish:
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    needs: [sdist, wheels-linux, verify]   # + all wheel jobs
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write                 # mandatory; attestations sign with this same OIDC identity
      contents: read
    steps:
      - uses: actions/download-artifact@<sha>
        with: { path: dist, merge-multiple: true }   # sdist + every wheel
      - uses: pypa/gh-action-pypi-publish@<sha>   # >=v1.11.0; PEP 740 attestations on by default
```

Key points carried from the real pipeline: `package-dir` points cibuildwheel at
the downloaded **sdist tarball** (so a file missing from the sdist fails the
build); the ccache `actions/cache` step is **skipped on tags**; the publish job
is the only one with `id-token: write` and runs only on `v*` tags.

## C. zizmor security audit (`zizmor.yml` or a CI job)

```yaml
name: zizmor
on:
  push: { branches: ["main"] }
  pull_request:

permissions: {}

jobs:
  zizmor:
    runs-on: ubuntu-latest
    permissions:
      security-events: write     # upload SARIF to code scanning
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@<sha>
        with: { persist-credentials: false }
      - uses: zizmorcore/zizmor-action@<sha>   # e.g. v0.6.x
```

SARIF mode exits 0 even with findings — **gate merges with a branch ruleset**,
not the green check. Local/pre-commit:

```bash
uvx zizmor .                 # audit all workflows in the repo
uvx zizmor --persona=pedantic .
```

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/zizmorcore/zizmor-pre-commit
  rev: v1.22.0                # bump to latest
  hooks:
    - id: zizmor
```

## D. PyPI Trusted Publisher checklist (do this once, on PyPI)

1. PyPI → your project → **Publishing** → add a GitHub Actions publisher.
2. Fill: **owner**, **repository**, **workflow filename** (e.g. `release.yml` /
   `build.yml`), and **environment name** (e.g. `pypi`). For a brand-new project
   use a **pending publisher** (same fields) before the first upload.
3. In the workflow: the publish job sets `environment: pypi` and
   `permissions: id-token: write`, and calls `pypa/gh-action-pypi-publish` with
   **no** username/password/token.
4. Optional but recommended: protect the `pypi` GitHub Environment (required
   reviewers, restrict to tag refs) so only vetted releases can request the OIDC
   token.

## E. Dependabot (`.github/dependabot.yml`)

Keeps SHA-pinned actions (and Python deps) current without hand-editing pins. Two
security-relevant knobs: **`cooldown`** delays update PRs so a freshly released
(possibly compromised or broken) version isn't adopted instantly, and
**`groups`** collapses related bumps into one reviewable PR — notably the CodeQL
action, which is really several actions under `github/codeql-action/*` that must
move together.

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7          # wait 7 days after a release before proposing it
    groups:
      codeql:                  # bump init/analyze/autobuild together
        patterns: ["github/codeql-action/*"]
      # Or collapse ALL action bumps into a single PR instead:
      #   actions:
      #     patterns: ["*"]

  - package-ecosystem: pip     # Python deps (use the matching ecosystem: pip / uv)
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
```

Choose one github-actions grouping: a `codeql`-only group (leaves other actions
as individual PRs — zipwire/retread) or an `actions: ["*"]` group that batches
everything (pycxxfilt). Add the `pip` block only if the repo pins Python deps you
want bumped.
