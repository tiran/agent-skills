---
name: modernize-python-metadata
description: >-
  Improve a Python package's metadata and move it into a PEP 621 [project] table
  in pyproject.toml — filling in what's missing along the way. Covers the readme
  field (dropping the open().read() hack), SPDX license expressions, trove
  classifiers, well-known project URLs, authors/keywords/requires-python,
  dependency version constraints (avoid upper caps), PEP 735 dependency groups
  vs extras, and the build-system table. Keeps the existing build backend
  (setuptools is fine). Use when asked to clean up packaging metadata, move
  metadata out of setup.py/setup.cfg, or improve a project's PyPI page.
---

# Modernize Python packaging metadata

**Status: Experimental** — grounded in the current PyPA specifications (linked
below); the step order is a new draft. Metadata bugs are quiet (a wrong classifier
or a bad cap surfaces later), so verify with the tools in step 11.

This skill is about **metadata** — it moves author/version/license/deps/URLs into
a declarative `[project]` table and improves what's there. It is **not** about
replacing or removing the build backend: **setuptools stays a perfectly good
choice**, and it reads `[project]` from `pyproject.toml` (setuptools ≥ 61). Any
`setup.py`/`setup.cfg` build *logic* (e.g. `ext_modules`, `cmdclass`) can remain;
only the *metadata* moves out. If you separately want to change *how* the package
builds, that's a different job — see
[`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
[`port-to-meson-python`](../port-to-meson-python/). Work in the order below.

## Authoritative sources (if this skill disagrees with them, they win)

- Writing pyproject.toml (`[project]`) —
  <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
- Distribution metadata (core metadata) —
  <https://packaging.python.org/en/latest/specifications/section-distribution-metadata/>
- License expression (PEP 639) —
  <https://packaging.python.org/en/latest/specifications/license-expression/>
- Well-known project URLs —
  <https://packaging.python.org/en/latest/specifications/well-known-project-urls/>
- Dependency groups (PEP 735) —
  <https://packaging.python.org/en/latest/specifications/dependency-groups/>
- Against version caps — <https://iscinumpy.dev/post/bound-version-constraints/>
- Scientific Python Development Guide (packaging) —
  <https://learn.scientific-python.org/development/guides/packaging-simple/>
- pyOpenSci packaging guide —
  <https://www.pyopensci.org/python-package-guide/>
- Hynek Schlawack on testing/packaging (src layout) —
  <https://hynek.me/articles/testing-packaging/>

## Caveat: newer metadata needs newer tooling

Several fields below only work on recent tool versions — an old backend or
uploader will error or silently drop them. Before adopting them, bump the
relevant tools (and their floors in `[build-system].requires`):

- **`[project]` table** → setuptools ≥ 61.
- **SPDX `license` expression + `license-files`** (PEP 639, core metadata 2.4) →
  setuptools ≥ 77 / hatchling ≥ 1.27 (recent) and **twine ≥ 6.1** to upload it
  (older twine rejects Metadata-Version 2.4).
- **`[dependency-groups]`** (PEP 735) → a resolver that supports it (pip ≥ 25.1,
  or uv) — it's not build metadata, so the backend version doesn't matter, but old
  pip won't understand `--group`. If a **Hatch environment** must consume a group
  (via the `dependency-groups` env key), require **Hatch ≥ 1.16.3** and bump that
  floor wherever Hatch is pinned (e.g. a `[tool.hatch]`/CI constraint or a `hatch`
  entry in a dev group); older Hatch has no way to read a group and its `features`
  key sees extras only (step 8). This is the **Hatch** env-runner version, not
  hatchling the backend.

When in doubt, check each tool's changelog and set conservative floors. Rule of
thumb: use current setuptools/hatchling, `build`, and twine. The rest of this
skill flags the version-sensitive spots (`reference/field-guide.md` has a table).

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Find where metadata lives today

```bash
ls pyproject.toml setup.py setup.cfg 2>/dev/null
grep -nE 'name=|version=|install_requires|extras_require|classifiers|url=|author' setup.py setup.cfg 2>/dev/null
```

Metadata can be static in `setup.cfg [metadata]`, imperative in `setup.py`
`setup(...)`, or partial in `pyproject.toml`. The target is a single **static**
`[project]` table (PEP 621); only genuinely computed fields stay `dynamic`. This
is a metadata move, not a backend change — if the project builds with setuptools,
keep setuptools (it reads `[project]` since v61); build *logic* like `ext_modules`
stays where it is (step 9, step 11).

## 2. Core `[project]` fields

```toml
[project]
name = "mypkg"
version = "1.2.3"                 # or dynamic — see the versioning skills
description = "One-line summary of what it does."   # → core-metadata Summary
requires-python = ">=3.11"        # floor only; prefer >=3.11 (3.10 EOL Oct 2026)
```

`description` is the one-line summary (shown on the PyPI search list), not the
long text — that's the README (step 3). Full field reference:
`reference/field-guide.md`.

## 3. README: drop the `open("README.md").read()` hack

`setup.py` used to do `long_description=open("README.md").read()` (which breaks
when the CWD isn't the project root, e.g. during isolated builds). Declare it
instead — the backend reads and sets the content type:

```toml
[project]
readme = "README.md"             # content-type inferred from the extension
# or, to be explicit / use a non-standard name:
# readme = { file = "docs/intro.rst", content-type = "text/x-rst" }
```

If you need to *assemble* the long description at build time — splice in the
changelog, rewrite relative image links to absolute URLs so they render on PyPI,
or inject the version — use a dynamic readme provider instead of a shell hack:
Hynek's [`hatch-fancy-pypi-readme`](https://github.com/hynek/hatch-fancy-pypi-readme)
(Hatchling; also a scikit-build-core `metadata.fancy_pypi_readme` provider). That
makes `readme` dynamic: `dynamic = ["readme"]` plus the provider config.

## 4. License as an SPDX expression (PEP 639)

`license` is a **short SPDX expression**, never the license text. Put the actual
text in files and point `license-files` at them. Do **not** use `License ::` trove
classifiers (deprecated) or the legacy table form (`license = {text=...}` /
`{file=...}`).

```toml
[project]
license = "Apache-2.0"                    # SPDX expression: "MIT", "BSD-3-Clause OR GPL-2.0-only", …
license-files = ["LICENSE*"]              # globs → the full text ships from here
```

Common mistakes to fix: the whole license pasted into `license`, a filename in
`license` (e.g. `license = "LICENSE"`), or `license = { text = "MIT License\n\n…" }`.
All become `license = "<SPDX id>"` + `license-files = ["LICENSE*"]`. For
non-standard terms use a `LicenseRef-...` expression and still ship the text via
`license-files`.

## 5. People, keywords, classifiers

```toml
[project]
authors = [{ name = "Ada Lovelace", email = "ada@example.com" }]
maintainers = [{ name = "…", email = "…" }]      # only if different from authors
keywords = ["parsing", "cli", "async"]           # search terms, not classifiers
classifiers = [
  "Development Status :: 4 - Beta",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.11",       # one row per minor you test in CI
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Programming Language :: Python :: Free Threading :: 3 - Stable",  # only if you test free-threaded CPython
  "Intended Audience :: Developers",
  "Typing :: Typed",                             # if you ship a py.typed marker
]
```

Pick classifiers from the official list (`reference/field-guide.md` has the
must-haves and how to browse them). **List one
`Programming Language :: Python :: 3.X` row per minor you actually test** — these
are a good signal of your *tested* range on the PyPI page, which `requires-python`
can't give (it only states the floor, never a ceiling). Keep them in sync with
your CI matrix and drop rows when you drop the version. If you test **free-threaded
CPython**, advertise it with a `Programming Language :: Python :: Free Threading ::
3 - Stable` classifier (or `2 - Beta` / `1 - Unstable` while support is maturing) —
it's how downstreams discover which packages are free-threading-ready. **Safety net
for private packages:** add
`"Private :: Do Not Upload"` — PyPI (and Test PyPI) reject any classifier in the
`Private ::` namespace, so an accidental `twine upload` of an internal package
fails instead of leaking it. This is a **PyPI server-side** rule, not a
backend/hatchling feature — client tools don't check it, and a private index
that doesn't enforce the namespace won't stop the upload. Treat it as cheap
defense-in-depth, not the primary control: the real protections are
**project-scoped API tokens or Trusted Publishing** (so no all-projects credential
exists to leak) and awareness of **dependency-confusion** risk when a name exists
on both a private index and public PyPI. See
[`secure-python-release-pipeline`](../secure-python-release-pipeline/).

## 6. Well-known project URLs

Populate `[project.urls]` with labels that **normalize to well-known names** so
PyPI renders them consistently (labels are matched case/space/punctuation-insensitively):

```toml
[project.urls]
Homepage = "https://github.com/you/mypkg"
Source = "https://github.com/you/mypkg"
Documentation = "https://mypkg.readthedocs.io"
Changelog = "https://github.com/you/mypkg/releases"   # GitHub Releases as changelog
Issues = "https://github.com/you/mypkg/issues"
Funding = "https://github.com/sponsors/you"           # optional
```

Recognized labels include `homepage`, `source` (aliases `repository`/`github`),
`documentation` (`docs`), `changelog` (`changes`/`history`), `issues`
(`bugs`/`tracker`), `funding`, `security`, `releasenotes`, `download`. Table with
all aliases: `reference/field-guide.md`.

## 7. Dependencies: floors, not caps

```toml
[project]
dependencies = [
  "httpx>=0.27",                 # floor: the oldest you actually support
  "click>=8.1,!=8.1.4",          # exclude a KNOWN-broken release, not a range guess
]
```

**Avoid upper caps (`<N`) and never cap `requires-python` on the high side.** A
missing cap anyone can fix downstream; an over-tight cap can only be fixed by a
new release from you, and modern resolvers silently backsolve to ancient
versions instead of erroring. Cap **only** a version you *know* is incompatible
(treat it like a TODO to remove). Details and the reasoning:
`reference/dependencies.md`.

## 8. Dependency groups vs extras

Two different tools — pick by *who* the dependency is for:

- **`[project.optional-dependencies]` (extras)** — optional *features* for your
  **users**, installable as `pip install mypkg[postgres]`. Published in package
  metadata.
- **`[dependency-groups]` (PEP 735)** — internal **dev** sets (lint, test, docs).
  **Not** published to metadata, **not** installable as an extra; consumed with
  `pip install --group test` / `uv`. Use these instead of a `dev` extra.

```toml
[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.1"]

[dependency-groups]
test = ["pytest>=7", "coverage[toml]>=7"]
docs = ["sphinx>=7"]
dev  = [{ include-group = "test" }, { include-group = "docs" }, "ruff"]
```

> **Exception — the consumer must support groups.** Only move a dev set to
> `[dependency-groups]` if whatever *installs* it understands PEP 735. The common
> trap is **Hatch environments**: `[tool.hatch.envs.<name>].features = ["test"]`
> reads `[project.optional-dependencies]` (extras) **only** — it cannot consume a
> `[dependency-groups]` group, so blindly relocating a `test`/`docs` set there
> silently breaks the env wiring. Either keep those dev sets as extras, or rewire
> the env to the separate `dependency-groups` key and **require Hatch ≥ 1.16.3**
> (the key landed in 1.16.0 but 1.16.3 fixes it for non-builder envs) — pin that
> floor wherever Hatch is constrained. Same caution for any other consumer (tox,
> nox, CI) that references extras rather than `--group`. Check *how the sets are
> consumed* before moving them.

More (including `include-group` and the Hatch caveat): `reference/dependencies.md`.

## 9. The `[build-system]` table

Every modern project needs one — it's what makes the build reproducible and
isolated (PEP 517/518). **Keep your current backend if it works** — for a
setuptools project, just declare it (no need to switch to hatchling et al.):

```toml
[build-system]
requires = ["setuptools>=61"]     # ≥61 reads [project]; keep setuptools if that's what you use
build-backend = "setuptools.build_meta"
```

```toml
# other backends look the same, e.g.:
# requires = ["hatchling"]          build-backend = "hatchling.build"
# requires = ["scikit-build-core"]  build-backend = "scikit_build_core.build"
```

Pin the *build* backend's floor here; add compile-time deps (Cython, numpy
headers, a VCS-version tool). **Special case — building against a pre-installed
dependency (e.g. Torch):** some compiled extensions must build against the exact
version already in the environment. There, isolated builds are turned off
(`pip install . --no-build-isolation`) and the heavy dep is *not* listed in
`requires`; the project documents "install torch first." Note it in the README
and treat it as a deliberate exception to the isolate-everything rule.
`reference/dependencies.md` covers it.

## 10. Mark only what's truly dynamic

Anything computed at build time goes in `dynamic` and is filled by the backend
(most commonly the version from VCS — see the versioning skills). Everything else
should be static and readable in `pyproject.toml`.

```toml
[project]
dynamic = ["version"]
```

## 11. Verify, then clean up the old files

1. `uvx validate-pyproject pyproject.toml` — schema-check the metadata.
   (Worth wiring into pre-commit; the Scientific Python guide's `sp-repo-review`
   also lints packaging metadata, e.g. PP004 "no upper cap on requires-python",
   PP007 "don't mix `License ::` classifiers with the `license` field".)
   `uvx pyproject-fmt pyproject.toml` is the formatter counterpart — it
   normalizes and reorders `[project]` and can keep the
   `Programming Language :: Python` classifiers in sync with `requires-python`
   (step 5). Run it before `validate-pyproject`, and add both as pre-commit hooks.
2. `uv build` then `uvx twine check dist/*` — render-check the README
   and metadata as PyPI will see them.
3. Confirm the built wheel's `METADATA` shows the license, URLs, and classifiers.
   In CI, Hynek's
   [`build-and-inspect-python-package`](https://github.com/hynek/build-and-inspect-python-package)
   action builds sdist + wheel and prints the exact metadata and file contents —
   a fast way to catch a wrong license id, missing README, or a file left out of
   the sdist (see [`secure-python-release-pipeline`](../secure-python-release-pipeline/)).
4. Remove the metadata you moved from `setup.py` / `setup.cfg` so there's one
   source of truth — but **keep whatever build logic remains**: `ext_modules`,
   `cmdclass`, custom `build_ext`, and setuptools-specific tool config are fine
   to leave in `setup.py`/`setup.cfg`. A pure-metadata `setup.cfg [metadata]`
   section, or a `setup.py` that only calls `setup()` with metadata kwargs, can
   be deleted once `[project]` covers it. Don't delete `setup.py` just to delete
   it — this task doesn't require dropping setuptools.

## Adjacent modernizations (out of scope here, worth flagging)

While in `pyproject.toml`, these are the neighboring cleanups the community
guides recommend — mention them, but they're separate tasks:

- **Consolidate tool config** into `pyproject.toml` (`[tool.ruff]`,
  `[tool.pytest.ini_options]`, `[tool.mypy]`, `[tool.coverage]`) and delete the
  scattered `pytest.ini` / `.flake8` / `mypy.ini` / `tox.ini` files.
- **`src/` layout (strongly recommended, but don't auto-migrate).** Moving the
  package under `src/mypkg/` takes the project root off `sys.path`, so tests and
  tools import the *installed* package instead of the source tree — surfacing
  "forgot to ship a file / sub-package", empty-wheel, and missing-data bugs
  locally instead of after release (the same class the sdist→wheel check in step
  11 / the release-pipeline skill targets). Endorsed by Hynek Schlawack, James
  Bennett, the Scientific Python guide, and pyOpenSci. **Only do the move if the
  user asks** — a relayout rewrites every path and can obscure `git blame`/`log`
  across the renames; when asked, use `git mv` in a dedicated, rename-only commit
  so history follows.
- **Starting fresh?** `uvx cookiecutter gh:scientific-python/cookie` scaffolds a
  standards-based project (pick backend, license, VCS versioning) matching the
  guide.

**Definition of done:** metadata lives in a static `[project]` table (no metadata
duplicated in `setup.py`/`setup.cfg`); `validate-pyproject` and `twine check`
pass; README, SPDX license, authors, keywords, classifiers, and well-known URLs
are populated; dependencies use floors without speculative caps; dev tooling is in
`[dependency-groups]` (or stays in extras where a consumer like Hatch `features`
requires it — step 8); the build backend is declared in `[build-system]` (keeping
setuptools is fine); any remaining `setup.py`/`setup.cfg` holds only build logic,
not metadata.
