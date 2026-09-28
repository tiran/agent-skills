# Migrating from Poetry to PEP 621

Backs the "Coming from Poetry?" note in the skill. Translates a Poetry project's
`[tool.poetry]` configuration into the standard PEP 621 `[project]` table, then hands
back to the main workflow. For *why* the skills prefer a standards-based stack over
Poetry — and when Poetry is still a fine choice — see
[`choose-python-build-backend/reference/why-not-poetry.md`](../../choose-python-build-backend/reference/why-not-poetry.md).
Authoritative:
[Poetry `pyproject.toml`](https://python-poetry.org/docs/pyproject/),
[Poetry dependency specification](https://python-poetry.org/docs/dependency-specification/),
[Poetry 2.0 announcement](https://python-poetry.org/blog/announcing-poetry-2.0.0/),
[PEP 621](https://peps.python.org/pep-0621/).

## First: which Poetry are you on?

- **Poetry ≥ 2.0 (Jan 2025)** reads a standard `[project]` table. Many 2.0 projects
  already keep metadata in `[project]` and use `[tool.poetry]` only for
  Poetry-specific bits — for those the "migration" is mostly a **build-backend +
  lockfile swap** (see the last two sections), not a metadata rewrite.
- **Poetry < 2.0** keeps everything under `[tool.poetry]`. That legacy table is
  where the real translation work is, and what the tables below cover.

Detect it: `grep -c '^\[project\]' pyproject.toml` (0 → legacy layout) and check the
installed `poetry --version`.

## Field map: `[tool.poetry]` → `[project]`

| Poetry (`[tool.poetry]`) | PEP 621 (`[project]`) | Notes |
| --- | --- | --- |
| `name`, `version` | `name`, `version` | Or make `version` dynamic via a backend VCS plugin (below). |
| `description` | `description` | One-line summary (SKILL step 2). |
| `authors = ["A B <a@b.io>"]` | `authors = [{name="A B", email="a@b.io"}]` | Poetry uses a single `"Name <email>"` string; split it (SKILL step 5). |
| `maintainers` | `maintainers` | Same string→table split. |
| `license = "MIT"` | `license = "MIT"` | Already an SPDX id in most cases; add `license-files = ["LICENSE*"]` (SKILL step 4). |
| `readme = "README.md"` | `readme = "README.md"` | A **list** of readmes → a dynamic readme provider (SKILL step 3). |
| `homepage`, `repository`, `documentation` | `[project.urls]` | `Homepage`/`Source`/`Documentation` (SKILL step 6). |
| `keywords` | `keywords` | Unchanged. |
| `classifiers` | `classifiers` | Poetry **auto-adds** license/Python classifiers; list them explicitly now (SKILL step 5). |
| `python = "^3.9"` | `requires-python = ">=3.9"` | **Drop the implicit `<4.0` cap** (see constraints below). |
| `[tool.poetry.dependencies]` | `[project.dependencies]` | Minus the `python` entry; translate constraints (below). |
| `[tool.poetry.extras]` + `optional = true` deps | `[project.optional-dependencies]` | Poetry marks a dep `optional = true` and lists it under `[tool.poetry.extras]`; PEP 621 puts the whole spec in the extra (SKILL step 8). |
| `[tool.poetry.group.<g>.dependencies]`, `[tool.poetry.dev-dependencies]` | `[dependency-groups]` (PEP 735) | Dev/test/docs sets → groups, not extras (SKILL step 8; consumer caveat in `dependencies.md`). |
| `[tool.poetry.scripts]` | `[project.scripts]` | Console entry points; same `name = "pkg.mod:func"` form. |
| `[tool.poetry.plugins."group"]` | `[project.entry-points."group"]` | Generic entry points. |
| `packages`, `include`, `exclude` | backend build config | Not `[project]` — becomes e.g. `[tool.hatch.build.targets.wheel] packages = [...]`. |

## Constraint translation: Poetry operators → PEP 440 floors

Poetry's caret/tilde defaults bake in **upper caps**. The house style is
**floors, no speculative caps** — the reasoning is in
[`dependencies.md`](dependencies.md) and
[Henry Schreiner's write-up](https://iscinumpy.dev/post/bound-version-constraints/).
Translate, dropping the implicit ceiling unless you have *evidence* a newer release
breaks you (then keep a narrow `!=`/`<` with a TODO comment):

| Poetry | Means | PEP 440 (house style) |
| --- | --- | --- |
| `^1.2.3` | `>=1.2.3,<2.0.0` | `>=1.2.3` |
| `^0.2.3` | `>=0.2.3,<0.3.0` | `>=0.2.3` |
| `~1.2.3` | `>=1.2.3,<1.3.0` | `>=1.2.3` |
| `~1.2` | `>=1.2,<1.3` | `>=1.2` |
| `1.*` | `>=1.0,<2.0` | `>=1.0` |
| `*` | any | omit the constraint |
| `1.2.3` (bare) | `==1.2.3` (exact) | `>=1.2.3` — exact pins belong in a **lock file**, not library metadata |
| `>=1.2,<2.0` | as written | `>=1.2` (drop the cap unless known-bad) |
| `!=1.4.0` | exclusion | `!=1.4.0` (keep) |
| `python = "^3.9"` | `>=3.9,<4.0` | `requires-python = ">=3.9"` (prefer `>=3.11`, SKILL step 2) |

If a caret/tilde was a *deliberate* compatibility boundary (a dep that truly breaks
across majors), keep a documented cap — but the default when translating is to
loosen to a floor.

## Build backend: `poetry-core` → a standard backend

```toml
# Poetry
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

Replace per [`choose-python-build-backend`](../../choose-python-build-backend/SKILL.md):

- **Pure Python (the common case)** → **hatchling** (`requires = ["hatchling"]`,
  `build-backend = "hatchling.build"`). Move any `packages`/`include` rules to
  `[tool.hatch.build.targets.wheel]`.
- **VCS versioning** (you used `poetry-dynamic-versioning`) → **hatch-vcs**
  (`dynamic = ["version"]` + `[tool.hatch.version] source = "vcs"`).
- **Compiled extension** (C/C++/Cython/Rust) → poetry-core never really supported
  this; pick **meson-python** / **scikit-build-core** / **maturin** via
  `choose-python-build-backend` and its migration skills.

## Lockfile & workflow

- **Library** → don't ship a lockfile; delete `poetry.lock`. Consumers get your
  floors from `[project]`.
- **Application/service you deploy** → regenerate a standard lock: `uv lock` →
  `uv.lock` (replaces `poetry.lock`; the emerging PEP 751 `pylock.toml` is the
  cross-tool format).
- Command mapping: `poetry install` → `uv sync`; `poetry add X` → `uv add X`;
  `poetry build` → `uv build` (or `python -m build`); `poetry publish` → a
  **Trusted Publisher** release (see
  [`secure-python-release-pipeline`](../../secure-python-release-pipeline/SKILL.md)),
  not a stored token.

## Then follow the main workflow

Once the metadata is in `[project]`, the rest of `SKILL.md` applies unchanged:
verify with `validate-pyproject` + `twine check` (step 11), confirm the built wheel's
`METADATA`, and delete the leftover `[tool.poetry]` tables once `[project]` covers
them. **Definition of done for the Poetry part:** no `[tool.poetry]` metadata remains
(only Poetry-specific build config, if you deliberately kept Poetry as the backend),
constraints are floors without speculative caps, and the backend is a standards-based
choice.
