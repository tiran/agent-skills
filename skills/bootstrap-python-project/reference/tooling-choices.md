# Tooling choices — the decisions with more than one good answer

The scaffold has one correct answer for most things (uv, ruff, hatchling, `src/`
layout, hardened CI). These three genuinely depend on the project; pick with the
user, then wire in the choice from `reference/scaffold.md`.

## Type checker — Pyrefly vs ty vs mypy (all solid)

All three read the same PEP 484/561 types and the `py.typed` marker; they differ in
speed, spec conformance, maturity, and ecosystem. As of 2026:

| | **Pyrefly** (default) | **ty** | **mypy** |
| --- | --- | --- | --- |
| Vendor / lang | Meta, Rust | Astral, Rust | python/typeshed, Python |
| Maturity | **Stable 1.0** (May 2026), Meta-scale | 0.x beta — **pin the version** | mature, reference impl |
| Speed | Rust-fast (full-project) | fastest raw engine (esp. editor) | slowest (2.0 adds parallel) |
| Spec conformance | highest (~96%) | lower (~76%), improving | high |
| Ecosystem fit | standalone | **same as uv + ruff** (Astral) | universal |
| Plugins (Django/SQLAlchemy/Pydantic-v1) | no | no | **yes** |
| Migration | `pyrefly init` reads `[tool.mypy]` | — | — |

**All three are good choices — pick the one that fits the project; there's no wrong
answer here.**

- **mypy** — the mature, most widely adopted reference implementation, with the broadest
  library/plugin support. The conservative pick, and the right one when the project relies
  on mypy **plugins** (Django ORM, SQLAlchemy, Pydantic v1) that the Rust checkers can't
  replace yet, or when maximum stability/ecosystem compatibility matters most.
- **Pyrefly** — production-ready 1.0, Rust-fast, high conformance, with a clean
  `pyrefly init` migration from `[tool.mypy]`. A strong default for a new, fully-typed
  project.
- **ty** — the Astral checker, so it fits a single-vendor uv + ruff + ty stack (what the
  reference repo `pycxxfilt` uses); fastest in-editor, but still 0.x, so **pin an exact
  version** in the `dev` group and CI.

If the user has no preference, defaulting to **Pyrefly** is reasonable — but don't push
back if they prefer ty or mypy; both are equally valid.

Config (put in `pyproject.toml`; also add a `typecheck` tox/nox session):

```toml
# Pyrefly
[tool.pyrefly]
project-includes = ["src", "tests"]
python-version = "<floor>"

# ty
[tool.ty.environment]
python-version = "<floor>"
[tool.ty.src]
include = ["src/", "tests/"]

# mypy
[tool.mypy]
python_version = "<floor>"
strict = true
files = ["src", "tests"]
```

Run in CI as `uvx pyrefly check` / `uvx ty check src/` / `uvx mypy src`. Whatever
you pick, the package still ships the empty `py.typed` marker and the `Typing ::
Typed` classifier.

> Mature libraries (structlog, attrs) run **several** checkers in parallel tox/nox
> envs — commonly mypy + pyright + ty + pyrefly — to catch spec disagreements
> before downstream consumers do. Overkill for a fresh project: scaffold **one**
> (Pyrefly), and add a second `typecheck-<tool>` env later if the package ships
> stubs to PyPI and wants the cross-check.

## License — ask the user; don't choose for them

There is **no default**. A license is a legal/policy decision the owner makes;
present the prominent options with the trade-off and record their pick as the SPDX
expression (`license = "<SPDX>"` + `license-files = ["LICENSE*"]`, PEP 639). Point
undecided users at <https://choosealicense.com/> and the
[SPDX list](https://spdx.org/licenses/); if a project has a parent org or funder,
its policy may dictate the choice.

| SPDX id | Family | In one line |
| --- | --- | --- |
| `MIT` | permissive | Shortest, most permissive: keep the copyright notice, do anything (incl. proprietary/commercial). No patent grant. |
| `BSD-3-Clause` | permissive | MIT-like, plus a "don't use our name to endorse" clause. |
| `Apache-2.0` | permissive | Permissive **with an explicit patent grant** and `NOTICE`/trademark handling — preferred for larger or company-backed projects. |
| `MPL-2.0` | weak copyleft | **File-level** copyleft: changes to MPL-licensed files stay open, but they can be combined with proprietary code. |
| `LGPL-3.0-or-later` | weak copyleft | Library copyleft: proprietary code may *use* the library, but modifications to the library itself must be shared. |
| `GPL-3.0-or-later` | strong copyleft | Derivative works must also be GPL — keeps the whole downstream open. |
| `AGPL-3.0-or-later` | strong copyleft | GPL **plus a network clause**: running a modified version as a network service triggers the share-source obligation (closes the SaaS loophole). |

Rules of thumb to explain, not to decide for them: **permissive** (MIT / BSD /
Apache-2.0) maximizes adoption — anyone, including closed-source and commercial
users, can build on it; pick **Apache-2.0** when patents or a company are involved.
**Copyleft** (MPL → LGPL → GPL → AGPL, increasing strength) keeps derivatives open;
choose the strength by how far the openness obligation should reach (a single file,
a linked library, the whole app, or a networked service). "`-or-later`" lets code
move to future versions of the license. Note downstream compatibility (e.g. GPL
imposes constraints on combining with permissively-licensed deps).

**Vendored code:** if the project bundles third-party source, ship **every** bundled
license file, list them in `license-files`, and use a combined SPDX expression (e.g.
`Apache-2.0 AND BSD-3-Clause`) — `tiran/pycxxfilt` (vendored LLVM → `LICENSE.llvm`)
is a good model; setuptools' unattributed vendoring is the counter-example. See
SKILL step 7.

## Task runner — tox (default) or nox

Default **tox** (declarative, packaging-aware, the `tiran/*` house choice; structlog,
attrs); reach for **nox** when env setup needs real logic (`scientific-python/cookie`,
pyca/cryptography). Both isolate per-Python envs, run the matrix, and drive **uv**
underneath. **Don't** use a Makefile or shell scripts as the task runner (not
portable, no env isolation). The full rationale — nox vs tox benefits, and *why not*
make/shell — is in **`reference/task-runners.md`**; templates for both runners (and
the nox tricks) are in `reference/scaffold.md`.

**CI, with or without tox.** pydantic and fastapi run the CI matrix **uv-natively**
— `astral-sh/setup-uv` → `uv sync --locked` → `uv run pytest` — with no tox layer in
the workflow, which is cleaner than shelling `tox` inside Actions. The
`reference/scaffold.md` `ci.yml` shows the `uv tool install tox …` form (matches the
`tiran/*` repos); the uv-native form is an equally good alternative. Either is fine;
don't mix — the local runner (tox/nox) and the CI invocation should run the same
commands.

## Documentation generator (ask per project — no default)

Only when docs were requested in step 1. Present all three; the user picks.

- **Sphinx + MyST + furo** — the `tiran/zipwire` house style: Sphinx with
  `myst-parser` (so pages are Markdown, not only reST), the **furo** theme, and
  `autodoc`/`intersphinx`/`napoleon`, published on **Read the Docs** via
  `.readthedocs.yaml`. The mature default for reST/Sphinx ecosystems and rich
  cross-referencing. Deps (a `docs` group): `sphinx>=8`, `furo`, `myst-parser`.
- **MkDocs-Material** — pydantic / fastapi: Markdown-native, fast to author,
  `mkdocstrings[python]` for API autodoc, `mike` for versioned docs. The de-facto
  choice for this class of project. Deps: `mkdocs-material`, `mkdocstrings[python]`.
- **Zensical** — the MkDocs/Material team's (squidfunk) next-generation static site
  generator, positioned as the Markdown-native successor to Material. Newest of the
  three and fewer projects on it yet; offer it when the user wants the cutting edge
  from the same authors.

Whichever is chosen, add a `docs` dependency group and a `docs` tox/nox session that
builds with warnings-as-errors (`-W` / `--strict`).

## Deterministic project-template tools

This skill *generates* a project in the `tiran/*` house style. Before hand-rolling
anything, **consider a ready-made template** — and if the user will bootstrap
**many** projects, capture the house style in a real template tool rather than
re-running the skill by hand each time.

- **`scientific-python/cookie`** — *the recommended ready-made template* (Henry
  Schreiner). One well-maintained scaffold across 10 backends — pure-Python (hatch,
  uv, flit, pdm, poetry, setuptools) and compiled (pybind11+setuptools,
  scikit-build-core/CMake, meson-python, maturin/Rust) — driven by **copier** (or
  cookiecutter/cruft), so `copier update` re-syncs generated repos. It emits a
  complete, hardened project (pyproject, `noxfile.py`, full pre-commit, GHA CI/CD
  with Trusted Publishing + cibuildwheel, `docs/` + Read the Docs, tests with
  `filterwarnings=["error"]`) that passes `sp-repo-review` (the Scientific-Python
  Development Guide's ~40 executable checks) by construction. **Recommend it as the
  default for a standard project, especially a compiled/native one.** Reach for this
  skill's from-scratch scaffolding instead when you specifically want the `tiran/*`
  house style (tox over nox, Sphinx+MyST+furo, ty/pyrefly), tighter control, or to
  understand each piece. Audit any generated tree — cookie's or this skill's — with
  `uvx sp-repo-review .`.
- **copier** — *the recommended template engine* if you build your own template. Deterministic, YAML-configured
  (`copier.yml`), Jinja templates. Its differentiator is **`copier update`**: it
  records the answers and template version in a tracked `.copier-answers.yml`, so
  when the template later changes (new CI action, ruff rule, packaging layout) you
  re-apply the diff to every generated repo — a git-merge-style update, conflicts
  flagged. This is what makes a fleet of projects maintainable long-term.
- **cookiecutter** — the older, larger-ecosystem generator (`cookiecutter.json`).
  Simple and fine for one-off scaffolds, but **no update mechanism**; adding one
  means bolting on **cruft** (a wrapper, with the limits of not owning
  cookiecutter's internals). Prefer copier for anything you'll maintain.
- **`uv init` / `hatch new`** — built-in minimal scaffolders. Good for a quick
  start, but they produce a *bare* project, not the hardened, CI-complete shape
  here. Use them only as a first step you then flesh out.

**Turning this scaffold into a copier template:** move the tree into a template
repo, rename per-project values (`<dist>`, `<pkg>`, `<owner>`, `<floor>`) to Jinja
variables (`{{ dist }}` …) — file/dir names too (`src/{{ pkg }}/`) — declare them
in `copier.yml` with sensible defaults and the project-type branch from SKILL step
1, and gate the compiled-only files (`meson.build`, `.clang-format`) behind a
`project_type` conditional. Then `copier copy <template> <dest>` scaffolds and
`copier update` propagates future changes. Commit the generated tree immediately
(even files you'll delete) so the first `copier update` has a clean base.
