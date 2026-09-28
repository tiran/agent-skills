---
name: bootstrap-python-project
description: >-
  Scaffold a new Python project from zero: src/ layout, PEP 621 metadata, a chosen
  build backend (hatchling for pure Python; meson-python / scikit-build-core /
  maturin for compiled) with dynamic VCS versioning, py.typed, ruff, a type checker,
  pytest + coverage, tox or nox via uv, and hardened GitHub Actions CI (SHA-pinned,
  Trusted Publisher, CodeQL/Scorecard/Dependabot). Always writes a README, LICENSE,
  and .gitignore. Orchestrates the choose-python-build-backend,
  modernize-python-metadata, ship-type-information, and secure-python-release-pipeline
  skills. Use when
  asked to start a new package, scaffold/bootstrap a Python project, set up a repo
  from zero, turn a loose script into a proper package, or bring an existing project
  up to this standard (adopt the layout, metadata, tooling, or CI it lacks).
---

# Bootstrap a new Python project

**Status: Experimental** — encodes one house style (the `tiran/*` repos: `pycxxfilt`,
`zipwire`, `retread`) plus current PyPA / Astral / Hynek Schlawack practice. Have a
human review the generated tree and first CI run.

Create a project that is correct, typed, tested, and releasable **on day one** — not
a bare `uv init`. This skill **orchestrates** four others rather than duplicating
them: [`choose-python-build-backend`](../choose-python-build-backend/SKILL.md) (the
backend), [`modernize-python-metadata`](../modernize-python-metadata/SKILL.md) (the
`[project]` table),
[`ship-type-information`](../ship-type-information/SKILL.md) (the typing pass — new
projects are typed unless the user opts out; see step 5), and
[`secure-python-release-pipeline`](../secure-python-release-pipeline/SKILL.md) (the
release CI). Work in order.

**Two modes.** *New project* — run the steps to build the tree from zero. *Improve an
existing project* — run the same steps as a **gap analysis**: for each, compare what's
there against the target shape, adopt only what's missing, and **respect the project's
existing choices** (don't swap a working backend, task runner, or layout just to match
the house style — propose, don't impose). The four orchestrated skills already
operate on existing projects. Never overwrite or delete without the user's OK
([`../GUARDRAILS.md`](../GUARDRAILS.md)).

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it: work in a
> project-local `.venv` with **uv**; prefer `uvx` for one-off tools; never touch
> global/user site-packages; don't commit/push without approval (never straight to
> `main`); keep comments terse. **Capitalize "Python"/"Torch"** as product names.

> **Resolve current versions/pins at scaffold time — don't copy the template
> literals.** Every version, action tag, SHA, and `rev:` in `reference/scaffold.md`
> is illustrative and stale. Pin GitHub Actions to the full commit SHA of their
> latest release (`# vX.Y.Z` comment), pre-commit `rev:`s to latest tags, tool/dep
> versions to current floors, Python versions to those supported now (step 1).
> `reference/scaffold.md` has the exact `gh`/PyPI lookup commands.

**Bundled references — open each only at the step that cites it:**

- `reference/scaffold.md` — the file tree and every file's contents (`pyproject.toml`
  pure + compiled, `tox.ini` / `noxfile.py`, ruff/pytest/coverage, CI workflows,
  `.gitignore`, `SECURITY.md`, pre-commit, changelog).
- `reference/tooling-choices.md` — decisions with >1 good answer: type checker, license,
  tox vs nox, and template tools (recommended `scientific-python/cookie`; copier).
- `reference/task-runners.md` — nox vs tox rationale, and *why not* make / shell.
- `reference/containers.md` — the container house rule (only if containers are used).

**Authoritative sources** (they win if this skill disagrees): [PyPA — writing
pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/);
[Scientific-Python Development Guide](https://learn.scientific-python.org/development/);
reference repos [`tiran/zipwire`](https://github.com/tiran/zipwire) /
[`retread`](https://github.com/tiran/retread) (pure) and
[`pycxxfilt`](https://github.com/tiran/pycxxfilt) (compiled).

**Definition of done:** a repo that installs (`uv sync`), lints clean (ruff),
type-checks clean, tests pass, builds a valid inspected sdist+wheel, and has hardened
CI + a Trusted-Publisher release workflow — with a README, a LICENSE file, and a
`.gitignore`. Nothing committed without the user's OK.

## 1. Gather requirements

First establish the **mode**: an empty/new directory (build from zero) or an existing
project (improve). For an existing project, **inventory what it already has** — build
backend, layout, metadata, tooling, CI — and treat the rest of this skill as a
checklist of gaps; don't re-ask decisions the repo has already made, check upstream
first ([`../GUARDRAILS.md`](../GUARDRAILS.md) → *Prior work*), and don't clobber files.

> **Safeguard — get existing code into VCS with a clean tree before editing it.** If
> the project holds any code that isn't safely committed (not a git repo, or a dirty
> working tree), **stop and ask the user how to proceed** — to commit or stash
> outstanding changes, or to initialize a repo and commit the current code — before
> you change anything. Don't `git init` or commit on their behalf without their OK.
> This keeps every change this skill makes a reviewable, revertible diff and
> guarantees nothing pre-existing is lost — never modify code you can't diff against a
> committed baseline.

New projects have sticky defaults (name, import path, license, Python floor), so
**ask before scaffolding**. Collect (use `AskUserQuestion` where a default isn't
obvious):

- **Project type** — drives everything: *pure-Python library* (default) → hatchling +
  hatch-vcs; *compiled extension* (C/C++/CUDA/Cython/Rust) → meson-python /
  scikit-build-core / maturin (step 2); *CLI app* → library + `[project.scripts]`;
  *app, not a library* → packaged but may pin deps and skip PyPI.
- **Name** — pick a **distribution name that's free on PyPI**: check
  `https://pypi.org/pypi/<name>/json` (404 = available) or `uv pip index versions
  <name>`. PEP 503 normalizes `-`/`_`/`.`/case, so check the *normalized* form (and
  steer clear of confusable/typosquat-adjacent names). The **import (package) name
  should match the distribution name**, hyphens → underscores (`my-pkg` → `my_pkg`),
  unless there's a special reason to differ.
- **Python versions** — from <https://devguide.python.org/versions/>: by default
  support only the versions still in `bugfix`/`security` status (**not EOL**). Floor
  (`requires-python` + tool target-versions) = oldest supported; matrix = all
  supported. Optionally add the next release once it reaches **RC** (not alpha/beta).
- **License** — **ask; don't pick for them.** Offer the options and explain permissive
  vs weak/strong copyleft (table in `reference/tooling-choices.md`); record as SPDX.
- **Owner / URL** — GitHub `owner/repo`.
- **Docs?** If yes, ask which generator (no default): **Sphinx + MyST + furo** (house
  style, Read the Docs), **MkDocs-Material**, or **Zensical**
  (`reference/tooling-choices.md`).
- **Publish to PyPI?** Decides whether to wire the release workflow now.

Reuse the answers everywhere downstream. Don't invent metadata you weren't given
(author email, description) — ask or leave a marked TODO.

## 2. Choose the build backend

Run [`choose-python-build-backend`](../choose-python-build-backend/SKILL.md) with the
project type. Defaults:

| Project type | Backend | Versioning |
| --- | --- | --- |
| Pure Python (**default**) | `hatchling` + `hatch-vcs` | `[tool.hatch.version] source = "vcs"` → generated `_version.py` |
| Compiled C/C++/CUDA/Cython | `meson-python` + `vcs-versioning` | computed in `meson.build` |
| Rust | `maturin` | maturin VCS / Cargo |

**Prefer a purpose-built backend for new projects** — hatchling for pure Python (no
`setup.py`, hatch-vcs tag-derived versions); reach for a compiled backend only when
there's native code, handing the build details to
[`port-to-meson-python`](../port-to-meson-python/SKILL.md) /
[`port-to-scikit-build-core`](../port-to-scikit-build-core/SKILL.md). These are
preferred over setuptools; `choose-python-build-backend`'s `reference/why-not-setuptools.md`
has the rationale (`setup.py` deprecations, license-attribution history). setuptools
stays reasonable when *migrating* an existing project. `[build-system]` blocks are in
`reference/scaffold.md`.

If you pick **meson-python**, note its **commit-before-build gotcha** and record it in
the project's `AGENTS.md` (step 7) and release docs: `uv build`/`python -m build`
package the sdist from the **latest git commit**, silently ignoring uncommitted and
untracked changes — so contributors must commit before building or releasing. **For
day-to-day development, use an editable install** (`pip install -e . --no-build-isolation`,
or `uv sync` which installs the project editable): it builds from the working tree and
rebuilds the extension on import, so local edits are picked up without a commit — the
commit rule only bites at `uv build`/release. Details in
[`port-to-meson-python`](../port-to-meson-python/SKILL.md) (step 8).

## 3. Lay out the source tree

**`src/` layout** (prevents importing the un-built package), house conventions:

```
src/<pkg>/__init__.py   # curated public API      tests/conftest.py
src/<pkg>/py.typed      # empty PEP 561 marker     tests/test_*.py
src/<pkg>/_*.py         # private implementation
src/<pkg>/__main__.py   # only if there's a CLI
```

Keep implementation in **private underscore modules**, re-export the public surface
from `__init__.py`, and add the empty `py.typed` marker now (this skill ships typed
code). Minimal `__init__.py` / `__main__.py` / `conftest.py` in `reference/scaffold.md`.

## 4. Write PEP 621 metadata

Run [`modernize-python-metadata`](../modernize-python-metadata/SKILL.md) for the
`[project]` table: `name`, `dynamic = ["version"]`, `description`, `readme`, SPDX
`license` + `license-files`, `requires-python`, `authors`, `keywords`, classifiers
(**include `Typing :: Typed`** + the per-version Python rows; `Private :: Do Not
Upload` if it must never hit PyPI), `[project.urls]`, and dependencies **with floors,
no upper caps**. `[project.scripts]` for a CLI. Dev/test/docs deps go in **PEP 735
`[dependency-groups]`**. Worked blocks (both cases) in `reference/scaffold.md`.

> **Default runtime deps to the top-level `[project.dependencies]`.** Use
> `[project.optional-dependencies]` (extras) **only for genuinely optional, additional
> features the user explicitly asks to gate behind an extra** (e.g. `pdf`, `s3`, `gpu`) —
> a feature a consumer can reasonably run without. Do **not** split core runtime deps into
> extras just to keep an install slim: that pushes complexity onto every consumer (import
> guards, lazy imports, degraded default behaviour). If a dependency is needed for the
> project's normal operation, it's a core dependency.

## 5. Configure quality tooling (in `pyproject.toml`)

From `reference/scaffold.md`:

- **ruff** (lint **and** format) — replaces black/isort/flake8; `select =
  ["E","W","F","I","UP","B","SIM","TC","ANN","RUF"]`, `ignore = ["E501","ANN401"]`, and a
  per-file `"tests/**" = ["ANN"]` ignore. (`TC` = flake8-type-checking, enforces the
  `TYPE_CHECKING` convention below; `ANN` enforces annotations. Resolve the current rule
  codes — the set evolves, e.g. `TCH` was renamed to `TC`.)
- **Type checker** — **Pyrefly**, **ty**, and **mypy** are all good choices; pick one.
  **mypy** is the mature, most widely adopted standard (best plugin/ecosystem support:
  Django/SQLAlchemy/Pydantic-v1); **Pyrefly** and **ty** are the fast Rust newcomers (both
  still 0.x — pin them). Default to Pyrefly for a new project if the user has no preference,
  but ty or mypy are equally valid. Trade-off + config in `reference/tooling-choices.md`.
- **pytest + coverage** — `testpaths`, an `integration` marker deselected by default
  (`addopts = "-m 'not integration'"`), `asyncio_mode = "auto"` if async; coverage
  `branch`/`parallel`, `omit` the generated `_version.py`.

**Imports & typing conventions** (apply in generated code AND record in `AGENTS.md`):
- **All imports at module top-level.** Reach for a function-local (deferred) import only
  for a genuine special case — breaking an import cycle, or a heavy/optional dependency
  that must not load unless a feature is used — and comment *why*.
- **Type-annotate by default** (the project ships `py.typed`) — **new projects are typed
  unless the user opts out.** Use modern syntax (PEP 604 `X | None`, PEP 585 `list[...]`,
  `collections.abc` over `typing` aliases); add `from __future__ import annotations` for
  forward refs and to keep annotations cheap. If the user opts out, skip annotations and
  don't ship `py.typed`.
- **Typing-only imports go under `if typing.TYPE_CHECKING:`** — satisfies ruff `TC`,
  avoids runtime cost, and sidesteps cycles.
- **Check typeshed before `# type: ignore`.** If a dependency is untyped, add its stub
  package (e.g. `types-requests`) to the dev group so it's type-checked. Reserve
  `# type: ignore` for libraries with neither inline types nor a stub package.

For the deeper typing work — annotating an existing untyped codebase (autotyping,
`pyrefly infer`, MonkeyType), generating and packaging `.pyi` **stubs for a compiled
C/C++/Cython/Rust extension**, choosing modern syntax against the `requires-python` floor
(and `typing_extensions` vs. raising it), and **verifying type completeness** so the
built wheel actually carries its types — run
[`ship-type-information`](../ship-type-information/SKILL.md).

## 6. Task runner (tox by default, nox optional)

Default **tox 4 + `tox-uv` + `tox-gh`** (fast uv envs, `[gh]` CI mapping); envs:
`py3XX`, `lint`, `fix`, `typecheck`, `coverage-report`, `docs`. **nox** is the
recommended alternative when env setup needs real logic. **Don't** scaffold a
Makefile or shell scripts as the task runner (not portable, no env isolation) — a
Makefile is at most a power-user alias on top of tox/nox. CI invokes the same runner.
Templates in `reference/scaffold.md`; full rationale in `reference/task-runners.md`.

## 7. Required repo files

Mandatory (first three per the request):

- **README** — title, one-line description, install, quickstart, badges.
- **LICENSE** — text matching the chosen SPDX id (one `LICENSE*` file per license).
  - **Vendored third-party source → ship and reference *every* bundled license.** Add
    each `LICENSE.<dep>`, list them in `license-files = ["LICENSE*"]`, and use a
    combined SPDX expression (e.g. `Apache-2.0 AND BSD-3-Clause`). `tiran/pycxxfilt`
    (vendored LLVM → `LICENSE.llvm`) is a good model; setuptools' unattributed
    vendoring is the counter-example (`why-not-setuptools.md`). A missing vendored
    license is a real compliance defect.
- **`.gitignore`** — fetch GitHub's canonical
  [`Python.gitignore`](https://github.com/github/gitignore/blob/main/Python.gitignore)
  and prepend a short project block (`.claude/`, the hatch-vcs `src/<pkg>/_version.py`).
- **`SECURITY.md`** — supported versions + GitHub private-advisory reporting.
- **`AGENTS.md`** + a **`CLAUDE.md` → `AGENTS.md` symlink** (`ln -s AGENTS.md
  CLAUDE.md`) — a brief agent guide: the project's key **rules/conventions** (use uv;
  the task-runner commands for test/lint/typecheck; ruff for lint+format; typed code;
  **imports at module top-level — local imports only for cycles/optional-heavy deps;
  typing-only imports under `TYPE_CHECKING`; annotate by default; prefer typeshed stubs
  over `# type: ignore`**; don't edit the generated `_version.py`; **for meson-python,
  develop with an editable install (`pip install -e .`) and commit before
  `uv build`/release — the sdist packages the committed revision, not the working tree
  (step 2)**; branch and don't commit without approval) and a **map of the
  layout** (`src/<pkg>/` public API vs `_*.py`, `tests/`, config in `pyproject.toml`, CI
  in `.github/`). Keep it short — a pointer, not a manual. Template in
  `reference/scaffold.md`.

**Opt-in, default off** (the `tiran/*` style lints via tox + CI). Offer each; don't
scaffold unless the user says yes, and keep declined config out of the tree:

- **`.pre-commit-config.yaml`** — common hook set (ruff-check/format, codespell,
  validate-pyproject, pre-commit-hooks basics; `prek` runner). Template in `scaffold.md`.
- **Changelog** — lowest-effort first: **GitHub auto-generated release notes** (zero
  maintenance, grouped via `.github/release.yml`), a hand-kept **Keep-a-Changelog**
  `CHANGELOG.md`, or **towncrier** fragments for frequent releases. All in `scaffold.md`.
- **`.editorconfig`** — on request.
- **Containers** — only if used. Per `reference/containers.md`: OCI-standard
  `Containerfile` building under both **Podman and Docker**, `ARG` over hard-coded
  values, no dockerisms, a ready-made Python base (UBI/Fedora for Red Hat, Ubuntu for
  Debian), **multi-stage** when building code, a **venv in the image**, run **non-root
  `1001:0`**, Compose Spec, and the **Dev Container standard** for dev.

## 8. Hardened CI (GitHub Actions)

Generate from `reference/scaffold.md`, then run
[`secure-python-release-pipeline`](../secure-python-release-pipeline/SKILL.md) to
finish the release path. Non-negotiable hardening: top-level `permissions: {}` +
least-privilege per job, **every `uses:` SHA-pinned** (`# vX` comment),
`persist-credentials: false`, concurrency cancel, uv throughout.

- **`ci.yml`** (push/PR): `lint`, `typecheck`, `test` matrix over supported Pythons
  (incl. free-threaded `3.Xt` where relevant), `coverage`, and a `build-package` job
  via [`hynek/build-and-inspect-python-package@v3`](https://github.com/hynek/build-and-inspect-python-package)
  (sdist+wheel, check-wheel-contents + twine, uploads `Packages`). Docs job if applicable.
- **`release.yml`** (tags `v*`): pure-Python → `uv build` → publish; compiled → split
  sdist → `cibuildwheel` from the sdist → verify tags → publish. Publish via **PyPI
  Trusted Publisher (OIDC)** with `id-token: write` + `attestations: write`,
  `environment: pypi`, `attestations: true`. `secure-python-release-pipeline` owns this.
- **`codeql.yml`** (`python`, + `c-cpp` for compiled), **`scorecard.yml`**,
  **`zizmor.yml`** (`persona: pedantic`) — all covered by the release-pipeline skill.
- **`dependabot.yml`** — `github-actions` (+ `pip` for compiled), weekly, cooldown +
  CodeQL grouping.

**Opt-in (default off): keep supported-Python declarations in sync** across the four
places they drift (classifiers, `requires-python`, tox `env_list`, GHA `matrix`):
**derive** the CI matrix from classifiers via baipp's
`supported_python_classifiers_json_array` (snippet in `scaffold.md`), and/or the
**`check-python-versions`** linter (`uvx check-python-versions .` / pre-commit hook).

## 9. Initialize, verify, and hand off

> **hatch-vcs vs. "don't commit without approval."** hatch-vcs / setuptools-scm derive the
> version from git; with `git init` but no commit or tag yet, `uv sync` and `uv build`
> **fail to determine a version** — but you must not commit without the user's OK. Resolve
> this by running the pre-approval gate with a pretend version:
> `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv sync` / `... uv build`. After the user approves
> committing, make the initial commit **and an initial tag** (`git tag v0.1.0`) so real
> versions are derived — don't leave the project depending on the pretend value.

1. `git init`; make the initial tree.
2. `uv venv && uv sync`; commit `uv.lock` for reproducible dev envs (the pure-Python
   reference repos do). (No commit yet? see the pretend-version note above.)
3. **Run the full gate and report real results** (don't claim unseen green):
   ```bash
   uvx ruff check src/ tests/ && uvx ruff format --check src/ tests/
   uvx pyrefly check            # or: uvx ty check src/  /  uvx mypy src/
   uv run pytest
   uv build && uvx twine check dist/*
   ```
   Or `tox` for the whole matrix.
4. **Confirm no stale template literals remain** — grep for unpinned action tags
   (`uses:.*@v[0-9]` with no SHA), leftover pins, and `<pkg>`/`<dist>`/`<owner>` markers.
5. **Commit only with the user's OK**, on a branch, signed off. The first `v*` tag
   triggers the release; walk the user through the one-time PyPI Trusted-Publisher
   setup (`secure-python-release-pipeline`) before tagging.

## 10. (Optional) reusable template

For a standard project (especially compiled), **recommend `scientific-python/cookie`**
— a copier template across 10 backends that emits a hardened project passing
`sp-repo-review` by construction. Use this skill's from-scratch path for the `tiran/*`
house style or full control. To reuse *this* style across many projects, capture it as
a **copier** template (`copier update` re-syncs generated repos). Full detail + the
`uvx sp-repo-review .` audit in `reference/tooling-choices.md`.
