# Task runners — the trade-offs (nox vs tox, and why not make / shell)

A deeper look at the step-6 decision. The job a task runner does for a Python
project has two parts: **(a)** create and manage **isolated per-Python virtualenvs**
and run a **test matrix** across interpreter versions, and **(b)** give developers
and CI **one standard interface** for the common tasks (`tests`, `lint`, `typecheck`,
`docs`, `coverage`). **tox** and **nox** do both. **make** and **shell scripts** do
only a weak version of (b) and none of (a) — that's the whole story below.

## tox vs nox — both good; pick by shape of the work

They are two takes on the same idea (isolated environments + a task interface); the
difference is **config-as-data vs config-as-code**.

### tox — declarative

- **Concise for a regular matrix.** `env_list = py{311,312,313,314}` and
  factor-conditional deps/commands (`all: coverage run -m pytest --all-backends`)
  express "Pythons × a couple of variants" in a few lines of INI/TOML.
- **CI mapping for free.** `tox-gh`'s `[gh]` section maps the GitHub Actions Python
  to the right envs with no workflow boilerplate.
- **Packaging-aware by default.** tox **builds the project** (sdist/wheel) and
  installs it into each env, so tests run against the *installed* package — this
  catches missing-file / `MANIFEST` / entry-point packaging bugs that a
  `pip install -e .` loop hides (`package = wheel`, the `.pkg` build env).
- **Mature and ubiquitous**, with a small, stable plugin set (`tox-uv`, `tox-gh`).
- **Lower cognitive load** for the common case — the config is data you skim, not a
  program you read.

Best when the matrix is regular and you want the least machinery. This is the
`tiran/*` house default.

### nox — imperative

- **Sessions are real Python**, so setup can contain **arbitrary logic**:
  conditionals, loops, computed parameters, branching on `session.python` / OS / env
  vars, reading `pyproject.toml` (`nox.project.load_toml` / `python_versions` /
  `dependency_groups`), and calling external tools (`external=True`).
- **`@nox.parametrize`** builds multi-dimensional matrices with custom `ids`
  (e.g. Python × backend × dependency-resolution).
- **Explicit and debuggable** — you see exactly which install and run steps happen;
  no implicit packaging step to reason about.
- **Composable** — import helpers, share code between sessions, generate sessions
  dynamically.

Best when environment setup genuinely needs code — native/Rust builds, downstream
integration jobs, lowest-version resolution, conda backends (cryptography, numpy,
scipy, nox itself).

### The one-line call

Both isolate envs and run cross-version matrices, driven by **uv** underneath.
Choose **tox** for a compact, packaging-aware, declarative setup (the default);
choose **nox** when the matrix or install steps need real logic. Whichever you pick,
**CI invokes the same runner** so local and CI can't diverge.

## Why not `make`

`make` is a build-dependency-graph tool for C, repurposed as a task alias. As a
Python task runner it fails on the two things above and adds footguns:

- **Not portable.** GNU make and BSD make differ in real ways (`.PHONY`, pattern
  rules, `$(shell …)`, `ifeq`/conditionals, functions). macOS ships an ancient GNU
  make (3.81) or BSD make; \*BSD ships BSD make. A Makefile written against modern
  GNU make routinely breaks on a contributor's Mac or a BSD runner.
- **POSIX make is a lowest common denominator** — no functions, minimal
  conditionals, no string handling, tab-sensitive syntax — so portable Make can't
  express task logic cleanly.
- **No environment management.** make runs commands in the current shell/env; it
  can't create or manage per-Python virtualenvs or a version matrix. To do the real
  job it would just shell out to tox/nox — so it adds a layer without doing the work.
- **Footguns**: tab-vs-space errors, silent `$VAR` vs `$$VAR` mistakes, cryptic
  diagnostics.

Legitimate use: a **thin convenience layer for power users** on top of tox/nox
(`make test` → `nox -s tests`). Fine to offer; never the primary runner in a
scaffold.

## Why not shell scripts (`scripts/*.sh`)

Everything wrong with make, more so:

- **Even less portable.** bash vs POSIX sh vs zsh vs dash differ; **Windows has no
  POSIX shell by default**, so `scripts/*.sh` locks out Windows contributors and
  Windows CI (without WSL/Git-Bash). A library that tests on macOS/Windows can't run
  them uniformly.
- **No isolation or matrix** — same gap as make; you'd invoke tox/nox anyway.
- **Fragile by default.** Correct error handling is manual (`set -euo pipefail`,
  quoting, word-splitting, `[[ ]]` vs `[ ]`); it's easy to ship a script that
  silently does the wrong thing. `shellcheck` helps but doesn't close the gap.
- **No task discovery, no dependency graph, no parametrization** — you re-implement
  what nox/tox give you, per script, by hand.

For a portable, cross-platform library scaffold, prefer tox/nox — they give the
isolation and matrix for free and run identically on Linux, macOS, and Windows.
**Don't scaffold shell scripts as the task runner.**

## Bottom line

Default **tox**; reach for **nox** when setup needs logic. A **Makefile** may sit on
top as a power-user alias; **shell scripts** should not be the task runner at all.
