# Scaffold — concrete files

Copy-and-adapt templates for the tree the workflow builds. Placeholders:
`<dist>` = PyPI distribution name (hyphens), `<pkg>` = import name (underscores),
`<owner>` = GitHub owner, `<floor>` = Python floor (e.g. `3.11` / `py311`).
Two cases run throughout: **pure-Python** (hatchling + hatch-vcs, like `zipwire` /
`retread`) and **compiled** (meson-python + vcs-versioning, like `pycxxfilt`).

> **Every version number and pin below is illustrative — resolve the current one at
> scaffold time; do not copy these literals verbatim.** They were current when
> written and rot fast. Specifically:
> - **GitHub Actions `uses:`** — pin to the **full 40-char commit SHA** of the
>   action's latest release, with a trailing `# vX.Y.Z` comment. Resolve with `gh`:
>   `gh api repos/<owner>/<repo>/releases/latest --jq .tag_name` then
>   `gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object.sha'`
>   (deref annotated tags to the commit). The `@vN` tags shown here are for
>   readability only.
> - **pre-commit `rev:`** — the latest release tag of each hook repo
>   (`gh api .../releases/latest --jq .tag_name`).
> - **Tool + dependency versions** (`ruff`, `pyrefly`, `sphinx`, `pytest`,
>   `meson`, build backends, …) — use current sensible **floors**, not the numbers
>   here; check PyPI (`uv pip index versions <pkg>`) / the tool's releases.
> - **Python versions** (classifiers, `requires-python`, matrices, tox `env_list`)
>   — the versions **supported now** per <https://devguide.python.org/versions/>
>   (bugfix + security; not EOL), consistent across all four (see the opt-in
>   consistency guards). Optionally add the next release once it reaches RC.

## File tree

Pure-Python:

```
.github/
  workflows/{ci,release,codeql,scorecard}.yml
  dependabot.yml
docs/                        # only if docs were requested (Sphinx)
src/<pkg>/
  __init__.py                # curated public API
  __main__.py                # only if there's a CLI
  py.typed                   # empty marker
  _*.py                      # private implementation
tests/
  conftest.py
  test_*.py
.gitignore
AGENTS.md   CLAUDE.md -> AGENTS.md   (symlink)
LICENSE     README.md   SECURITY.md
pyproject.toml
tox.ini                      # or noxfile.py
uv.lock                      # committed
```

Compiled adds: `meson.build` (top-level + one per source dir),
`src/<pkg>/_<ext>.pyi` (stub for the compiled module), `.clang-format` (C/C++),
`vendor/` (bundled sources, if any), `.github/check-wheel-tags.py`, and swaps
`release.yml` for a cibuildwheel `build.yml`.

## `pyproject.toml` — pure-Python (hatchling + hatch-vcs)

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "<dist>"
dynamic = ["version"]
description = "One-line description."
readme = "README.md"
license = "<SPDX>"                        # user's choice — see tooling-choices.md
license-files = ["LICENSE*"]
requires-python = ">=<floor>"
authors = [{ name = "...", email = "..." }]
keywords = []
# PEP 639: the SPDX `license` field replaces the old `License ::` trove classifier —
# don't add one. Python rows come from devguide.python.org/versions (supported only).
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Typing :: Typed",
]
dependencies = []

# For a CLI (see retread):
[project.scripts]
<dist> = "<pkg>.__main__:main"

[project.optional-dependencies]
# runtime-optional features only, e.g. pluggable backends

[project.urls]
Homepage = "https://github.com/<owner>/<dist>"
Source = "https://github.com/<owner>/<dist>"
Issues = "https://github.com/<owner>/<dist>/issues"

[dependency-groups]                      # PEP 735 — dev/test/docs, not shipped
test = ["pytest>=8.0", "coverage[toml]>=7.0"]
typing = ["pyrefly"]                     # or ty / mypy (step 5)
dev = [{ include-group = "test" }, { include-group = "typing" }, "ruff"]
# docs = ["sphinx>=8.0", "furo", "myst-parser"]   # if docs requested
# Composing groups with {include-group = ...} is the attrs/structlog pattern:
# `dev` is the superset a contributor installs; CI installs the narrow groups.

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/<pkg>/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/<pkg>"]

[tool.ruff]
line-length = 99
target-version = "<floor-tag>"           # e.g. "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "TC", "ANN", "RUF"]
ignore = ["E501", "ANN401"]              # line length is the formatter's job; allow typing.Any

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN"]                     # don't require annotations in tests

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not integration'"
markers = ["integration: end-to-end tests hitting the network"]
# asyncio_mode = "auto"                   # if async

[tool.coverage.run]
branch = true
parallel = true
relative_files = true                    # combine across OS/Python matrix runners
source = ["<pkg>"]
omit = ["*/_version.py"]

[tool.coverage.paths]
source = ["src/<pkg>", ".tox/*/lib/python*/site-packages/<pkg>", "*/site-packages/<pkg>"]

[tool.coverage.report]
show_missing = true
```

The generated `src/<pkg>/_version.py` is git-ignored; do **not** import it in
`__init__.py` — read the version from installed metadata if needed
(`importlib.metadata.version("<dist>")`).

## `pyproject.toml` — compiled (meson-python + vcs-versioning)

```toml
[build-system]
requires = ["meson-python>=0.17", "meson>=1.6", "vcs-versioning>=2.3.2"]
build-backend = "mesonpy"

[project]
name = "<dist>"
dynamic = ["version"]
requires-python = ">=<floor>"
license = "<SPDX>"                        # user's choice — see tooling-choices.md
license-files = ["LICENSE*"]
# classifiers as above, plus (if free-threaded wheels are shipped):
#   "Programming Language :: Python :: Free Threading :: 3 - Stable"

[project.optional-dependencies]
test = ["pytest"]

[tool.meson-python]
limited-api = true                        # abi3 wheel; see port-to-python-limited-api

[tool.ty.environment]                     # this repo family uses ty for compiled
python-version = "<floor>"
[tool.ty.src]
include = ["src/", "tests/"]

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "TC", "RUF", "ANN"]
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN001", "ANN201"]
```

Version is computed in `meson.build`, not by hatch-vcs:

```python
project('<dist>', 'c', 'cpp',
  version: run_command(
    find_program('python3', 'python', version: '>= <floor>'),
    '-m', 'vcs_versioning', check: true,
  ).stdout().strip(),
  default_options: ['cpp_std=c++20', 'b_ndebug=true'],
)
py = import('python').find_installation(pure: false)
# py.extension_module('_<ext>', sources, limited_api: '<floor>', install: true, subdir: '<pkg>')
# py.install_sources('src/<pkg>/__init__.py', 'src/<pkg>/py.typed', ..., subdir: '<pkg>')
```

Delegate the full native build (hardening flags, vendored sources, abi3) to
[`port-to-meson-python`](../../port-to-meson-python/SKILL.md).

## `tox.ini` (default runner)

Pure-Python:

```ini
# SPDX-License-Identifier: <SPDX>
[tox]
min_version = 4.0
skip_missing_interpreters = true
env_list =
    lint
    typecheck
    py{311,312,313,314}
    coverage-report

[testenv]
runner = uv-venv-lock-runner
dependency_groups = dev
commands = coverage run -m pytest {posargs}

[testenv:typecheck]
skip_install = true
deps = pyrefly
commands = pyrefly check {posargs:src/ tests/}

[testenv:coverage-report]
skip_install = true
depends = py{311,312,313,314}
deps = coverage[toml]>=7.0
commands =
    coverage combine
    coverage report
    coverage html

[testenv:lint]
skip_install = true
deps = ruff
commands =
    ruff check {posargs:src/ tests/}
    ruff format --check {posargs:src/ tests/}

[testenv:fix]
skip_install = true
deps = ruff
commands =
    ruff check --fix {posargs:src/ tests/}
    ruff format {posargs:src/ tests/}

# maps the CI matrix (tox-gh)
[gh]
python =
    3.11 = py311
    3.12 = py312
    3.13 = py313
    3.14 = py314
```

Notes: the reference repos install tox in CI with `uv tool install tox --with
tox-uv --with tox-gh` (rather than listing `tox-uv` under `[tox] requires`); either
works. Add factor-conditional envs (`py311-all` with `extras = all: all`) when the
project has runtime extras to test in combination (see `zipwire`). Compiled
projects use `package = wheel` and a `typecheck` env running `ty check src/` plus a
`clang-format --dry-run --Werror` step in `lint`.

## `noxfile.py` (alternative runner)

Incorporates the widely-used nox patterns (see "nox tricks" below). `nox.project.*`
reads the Python matrix and PEP 735 groups straight from `pyproject.toml`, so they
can't drift from the metadata.

```python
import nox

nox.needs_version = ">=2025.2.9"  # for nox.project.* + run_install
nox.options.default_venv_backend = "uv|virtualenv"  # uv if present, else virtualenv
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint", "typecheck", "tests"]  # bare `nox` runs these

PROJECT = nox.project.load_toml("pyproject.toml")
ALL_PYTHONS = nox.project.python_versions(PROJECT)  # from requires-python/classifiers


@nox.session(python=ALL_PYTHONS)
def tests(session: nox.Session) -> None:
    # run_install() is skipped on `nox -R` (reuse venv, don't reinstall)
    session.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group",
        "test",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run("coverage", "run", "-m", "pytest", *(session.posargs or ("tests/",)))


@nox.session
def lint(session: nox.Session) -> None:
    session.install("ruff")
    session.run("ruff", "check", "src", "tests")
    session.run("ruff", "format", "--check", "src", "tests")
    # or, if the project opts into pre-commit:
    # session.install("pre-commit")
    # session.run("pre-commit", "run", "--all-files", "--show-diff-on-failure")


@nox.session
def typecheck(session: nox.Session) -> None:
    session.install("-e.", *nox.project.dependency_groups(PROJECT, "typing"))
    session.run("pyrefly", "check", "src", "tests")  # or: ty check src/ / mypy src


@nox.session(default=False)  # opt-in: excluded from bare `nox`
def docs(session: nox.Session) -> None:
    session.install("-e.", *nox.project.dependency_groups(PROJECT, "docs"))
    # live-reload when run interactively, one-shot strict build otherwise
    cmd = "sphinx-autobuild" if session.interactive else "sphinx-build"
    session.run(cmd, "-b", "html", "-W", "docs", "docs/_build/html")


if __name__ == "__main__":
    nox.main()
```

### nox tricks worth keeping (from cryptography / urllib3 / cookie / nox's own)

- **`default_venv_backend = "uv|virtualenv"`** — fast with uv, still works without it.
- **`nox.needs_version = ">=…"`** — guarantees the newer API (`run_install`,
  `nox.project.*`, `default=`) is present.
- **`reuse_existing_virtualenvs` + `options.sessions`** — fast local loop; a bare
  `nox` runs the sensible core set.
- **`nox.project.load_toml` / `python_versions` / `dependency_groups`** — read the
  matrix and PEP 735 groups from `pyproject.toml` (single source of truth).
- **`session.run_install(...)`** — skipped on `nox -R`, so reruns don't reinstall;
  pair with `uv sync --frozen` + `UV_PROJECT_ENVIRONMENT` for lockfile-pinned envs.
- **`session.posargs or (default,)`** — `nox -s tests -- -k foo -x` just works.
- **`@nox.session(default=False)`** for opt-in sessions (docs, build, release).
- **Docs:** `sphinx-build -W`, auto-switch to `sphinx-autobuild` when
  `session.interactive`; add a `linkcheck` builder if wanted.
- **`external=True` + `env={...}`** on `session.run` for system tools (git, cargo)
  and per-session env vars.
- **PEP 723 self-bootstrapping shebang** (optional) — `#!/usr/bin/env -S uv run
  --script` + an inline `# /// script` block with `dependencies = ["nox>=…"]` so
  `./noxfile.py` runs with no pre-installed nox.

Project-specific tricks **not** worth generalizing: Rust/LLVM coverage merges and
`maturin develop --uv` (cryptography), pip's protected-pip/wheelhouse/vendoring,
nox's conda-backend matrix, urllib3's downstream/emscripten jobs.

## `.github/workflows/ci.yml`

Pin every action to a commit SHA with a `# vX` comment (shown here as tags for
readability — resolve to SHAs, per `secure-python-release-pipeline`).

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
permissions: {}
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v5      # with: { persist-credentials: false }
      - uses: astral-sh/setup-uv@v6
      - run: uvx ruff check src/ tests/
      - run: uvx ruff format --check src/ tests/

  typecheck:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
      - run: uvx pyrefly check      # or: uvx ty check src/  /  uvx mypy src/

  test:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    strategy:
      fail-fast: false
      matrix:
        python: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
        with: { python-version: "${{ matrix.python }}" }
      # Pin tox to the matrix Python so tox-gh's [gh] section selects the right envs
      # (tox-gh keys off the interpreter tox runs under, not an env var).
      - run: uv tool install --python "${{ matrix.python }}" tox --with tox-uv --with tox-gh
      - run: tox
      - uses: actions/upload-artifact@v4
        with: { name: "coverage-${{ matrix.python }}", path: ".coverage.*", include-hidden-files: true }

  coverage:
    needs: test
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
      - uses: actions/download-artifact@v4
        with: { pattern: "coverage-*", merge-multiple: true }
      - run: uvx coverage combine && uvx coverage report

  build-package:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }        # hatch-vcs / vcs-versioning need tags
      - uses: hynek/build-and-inspect-python-package@v3
```

`hynek/build-and-inspect-python-package` builds sdist+wheel reproducibly, runs
check-wheel-contents + `twine check`, prints the package trees, and uploads a
`Packages` artifact (and can attest provenance with
`attest-build-provenance-github: true`).

**Opt-in: derive the test matrix from the trove classifiers** (structlog / attrs)
so the CI Pythons and the `Programming Language :: Python :: 3.X` classifiers can't
drift — the matrix *is* the classifiers. Have `build-package` expose baipp's output
and `fromJSON` it in `test`:

```yaml
  build-package:
    outputs:
      pythons: ${{ steps.baipp.outputs.supported_python_classifiers_json_array }}
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }
      - uses: hynek/build-and-inspect-python-package@v3
        id: baipp

  test:
    needs: build-package
    strategy:
      fail-fast: false
      matrix:
        python: ${{ fromJSON(needs.build-package.outputs.pythons) }}
    # ... rest as above
```

This covers the GHA↔classifier axis; pair it with `check-python-versions` (below)
to also guard `requires-python` and the tox `env_list`.

Worth adding for a required-check and sdist-integrity story (pydantic / fastapi):

- **Single required gate** — add a job using
  [`re-actors/alls-green`](https://github.com/re-actors/alls-green) that `needs:`
  every matrix job, and mark *only* that job required in branch protection, so a
  changed matrix doesn't churn the required-checks list.
- **sdist-integrity job** (fastapi's `test-redistribute`): build the sdist, install
  **from it**, run the tests from inside the unpacked sdist, then build the wheel
  from that sdist. Catches missing files / `MANIFEST`-level packaging bugs the
  checkout-based `test` job can't see.
- **Per-job `timeout-minutes`** so a hung job fails fast rather than burning the
  runner budget.

## `.github/workflows/release.yml` (pure-Python)

Owned by [`secure-python-release-pipeline`](../../secure-python-release-pipeline/SKILL.md);
minimal shape:

```yaml
name: Release
on:
  push: { tags: ["v*"] }
permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0, persist-credentials: false }
      - uses: hynek/build-and-inspect-python-package@v3   # reuse: build + inspect + upload "Packages"

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions: { id-token: write, attestations: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { name: Packages, path: dist }
      - uses: pypa/gh-action-pypi-publish@v1
        with: { attestations: true }
```

Compiled projects replace `build` with a split **sdist → per-platform wheel (built
from the sdist) → verify wheel tags** matrix before `publish`. Two wheel-build
routes: **cibuildwheel** (the many-Python/-arch matrix, `pycxxfilt`'s `build.yml`)
or **`uv build --wheel`** from the unpacked sdist (`pyca/cryptography`'s pattern —
one wheel per platform job, simpler when abi3 or a single ABI keeps the matrix
small). Either way wheels build **from the sdist**, not the checkout — see
`secure-python-release-pipeline`.

## `codeql.yml`, `scorecard.yml`, `dependabot.yml`

Standard hardened versions from `secure-python-release-pipeline`. CodeQL:
`languages: [python]` (add `c-cpp` for compiled), weekly cron. Scorecard: OSSF
weekly. Dependabot:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: weekly }
    cooldown: { default-days: 7 }
    groups:
      codeql: { patterns: ["github/codeql-action*"] }
  # compiled projects add a `pip` ecosystem entry
```

## `.gitignore`

Fetch GitHub's canonical template and prepend a project block — don't hand-write
it:

```bash
curl -fsSL https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore -o .gitignore
```

Then prepend (matching the reference repos):

```gitignore
# Project-specific
.claude/

# hatch-vcs generated version file
src/<pkg>/_version.py
```

## `SECURITY.md`

```markdown
# Security Policy

## Supported Versions

The latest released version is supported.

## Reporting a Vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/<owner>/<dist>/security/advisories/new).
Do not open a public issue for security reports.
```

## `AGENTS.md` (+ `CLAUDE.md` symlink)

A short guide so coding agents know the project's rules and layout. Create the
symlink so Claude Code picks it up: `ln -s AGENTS.md CLAUDE.md`.

```markdown
# AGENTS.md — <dist>

Guide for AI coding agents. Humans: read `README.md`. Claude Code reads this file
via the `CLAUDE.md` symlink.

## Rules
- Use **uv** for everything (`uv sync`, `uv run`, `uv build`); work in the `.venv`.
- Run tasks with **tox** (or `nox`): `tox` (tests) · `tox -e lint` · `tox -e typecheck`.
- **ruff** lints and formats; keep code typed (the package ships `py.typed`).
- **Imports at module top-level.** Use a function-local import only for a genuine special
  case (breaking a cycle, or a heavy/optional dependency gated behind a feature) — and say why.
- **Type-annotate by default.** Put typing-only imports under `if typing.TYPE_CHECKING:`.
  Prefer adding a **typeshed stub** (`types-*`) to the dev group over `# type: ignore`.
- **Runtime deps are core** (`[project.dependencies]`); extras
  (`[project.optional-dependencies]`) are only for genuinely optional features.
- Don't edit the generated `src/<pkg>/_version.py` (hatch-vcs writes it).
- Branch for changes; don't commit or push without approval.

## Layout
- `src/<pkg>/` — the package: public API in `__init__.py`, implementation in `_*.py`.
- `tests/` — pytest suite (`conftest.py`, `test_*.py`).
- `pyproject.toml` — metadata and all tool config.
- `.github/workflows/` — CI and release.
```

Keep it terse and current; adjust the commands to the chosen runner/type checker.

## `.pre-commit-config.yaml` (recommended)

Not in the `tiran/*` repos (they lint via tox + CI), but used by structlog, attrs,
and `scientific-python/cookie`. Common-denominator hook set — pin `rev`s to current
tags:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.6
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/codespell-project/codespell
    rev: v2.4.3
    hooks:
      - id: codespell
  - repo: https://github.com/abravalheri/validate-pyproject
    rev: v0.26
    hooks:
      - id: validate-pyproject
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
  # Opt-in: fail if the trove classifiers, requires-python, tox env_list, and the
  # GitHub Actions matrix disagree on supported Python versions.
  - repo: https://github.com/mgedmin/check-python-versions
    rev: "0.22.1"
    hooks:
      - id: check-python-versions
```

Compiled projects add `clang-format` / `cmake-format`. The newer **`prek`** runner
(`j178/prek-action` in CI) is a drop-in for `pre-commit run` and is appearing in
Hynek's and cookie's configs; either runner reads this file.

## Changelog (recommended for libraries)

Three shapes, lowest-effort first — pick one, don't mix:

- **GitHub auto-generated release notes** (lowest effort) — GitHub builds the release
  body from merged PRs when you cut a release; no file to maintain, nothing in the
  repo. Curate the grouping with `.github/release.yml`:

  ```yaml
  changelog:
    categories:
      - title: Breaking
        labels: [breaking]
      - title: Changes
        labels: ["*"]
  ```

  Good default for apps and low-cadence libraries; the trade-off is the log lives on
  GitHub, not in the sdist.
- **Manual `CHANGELOG.md`** (structlog, cryptography) — Keep-a-Changelog format,
  edited by hand. Light; ships in the repo/sdist; fine for infrequent releases.
- **towncrier** (attrs) — one news fragment per change in `changelog.d/`, assembled
  into `CHANGELOG.md` at release. Best when many PRs land between releases:

  ```toml
  [tool.towncrier]
  directory = "changelog.d"
  filename = "CHANGELOG.md"
  start_string = "<!-- towncrier release notes start -->\n"
  package = "<pkg>"
  [[tool.towncrier.type]]
  directory = "breaking"
  name = "Backwards-incompatible Changes"
  showcontent = true
  [[tool.towncrier.type]]
  directory = "change"
  name = "Changes"
  showcontent = true
  ```

  Add a tox/nox `changelog` env running `towncrier build`.

## Containers (only if the project uses them)

The house rule — OCI-standard, works under both Podman and Docker, `ARG` over
hard-coded values, avoid dockerisms, Dev Container standard for dev environments — is
its own lens: **`reference/containers.md`** (with `Containerfile` and
`devcontainer.json` examples). Don't scaffold containers unless the project needs them.

## Minimal source files

`src/<pkg>/__init__.py`:

```python
"""<dist> — one-line description."""
```

`src/<pkg>/__main__.py` (CLI only):

```python
def main() -> int:
    ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`tests/conftest.py` starts empty (add shared fixtures as needed). `py.typed` is a
0-byte file.
