---
name: port-to-meson-python
description: >-
  Build a Python package (usually with a compiled C/C++/Cython/Fortran/Rust
  extension) with the meson-python PEP 517 backend, or port one off a bespoke
  setuptools setup.py. Covers the pyproject.toml backend, the meson.build
  (project / extension_module / install_sources), VCS/dynamic versioning
  computed in meson.build, editable installs, config-settings, and abi3 /
  limited-API wheels. Use when asked to adopt meson-python or Meson, scaffold a
  new meson-python project, drop setup.py, or produce standards-based wheels.
---

# Build (or port) a Python package with meson-python + Meson

**Status: Experimental** — distilled from a real shipping project (pycxxfilt,
see `reference/example.md`) plus the upstream docs, but the workflow itself is a
new draft. Follow it, adapt, and have a human review the wheel on every target
platform.

meson-python is a PEP 517 backend that turns a **Meson** build into wheels and
sdists. It is the Meson-based sibling of scikit-build-core (which uses CMake);
reach for it when the native build is (or should be) Meson. Two entry points,
one destination — a declarative `pyproject.toml` + `meson.build`:

- **Track N — new project.** Scaffold `pyproject.toml` + `meson.build` from
  scratch (steps 2–5, 8).
- **Track P — port from setuptools.** Replace `setup.py` (setuptools
  `Extension`, `MANIFEST.in`, custom `build_ext`) by translating it to Meson
  (adds step 6), then delete the old build (step 11).

## Why meson-python

- **Purpose-built for compiled extensions** — C, C++, Cython, Fortran, Rust —
  with Meson's real dependency graph, fast incremental ninja rebuilds, and
  cross-compilation, instead of hand-rolled `build_ext`.
- **Standards.** PEP 517/518 build, PEP 621 metadata; `pip`, `build`, `uv`,
  `cibuildwheel` all target it directly.
- **Editable installs that rebuild on import** with near-negligible overhead.
- **abi3 / limited API** first-class (`limited-api = true`) — one wheel across
  Python versions.

**Which backend?** meson-python if the project uses/wants **Meson**;
[`port-to-scikit-build-core`](../port-to-scikit-build-core/) if it uses/wants
**CMake** (e.g. it consumes a CMake package like `find_package(Torch)`). Same
PEP 517/621 shape either way.

**Authoritative sources** (if this skill disagrees with them, they win):

- meson-python docs — <https://mesonbuild.com/meson-python/>
- Tutorial (minimal project) —
  <https://mesonbuild.com/meson-python/tutorials/introduction.html>
- `[tool.meson-python]` reference —
  <https://mesonbuild.com/meson-python/reference/pyproject-settings.html>
- Editable installs —
  <https://mesonbuild.com/meson-python/how-to-guides/editable-installs.html>
- Limited API / abi3 —
  <https://mesonbuild.com/meson-python/how-to-guides/limited-api.html>
- Config settings —
  <https://mesonbuild.com/meson-python/reference/config-settings.html>
- Meson's Python module — <https://mesonbuild.com/Python-module.html>

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Check upstream, then assess and pick the track

**First, check upstream for prior work** ([`../GUARDRAILS.md`](../GUARDRAILS.md) →
*Prior work*): someone may already have a meson-python branch, PR, or a discussion
about why it stalled. Find the upstream repo (`git remote -v`, `[project.urls]`)
and search its issues + PRs (open/merged/closed) for `meson`, `meson-python`,
`pyproject`, `scikit-build`. Report what you find before porting.

Then inventory locally:

```bash
ls setup.py setup.cfg pyproject.toml MANIFEST.in meson.build 2>/dev/null
grep -nE 'Extension|ext_modules|build_ext|cmdclass|package_data' setup.py 2>/dev/null
```

No `setup.py` → **Track N**. A `setup.py` with `Extension(...)` / custom
`build_ext` → **Track P**; inventory what it does imperatively (generated files,
include dirs, link libs, compiler flags, data files, version source). Confirm
Meson is the right native tool (see "Which backend?" above).

## 2. Declare the build backend

```toml
[build-system]
build-backend = "mesonpy"
requires = ["meson-python>=0.17", "meson>=1.6"]
```

Add any tools the *build* needs (Cython, a VCS-version tool, numpy for headers)
to `requires`.

## 3. Project metadata (`[project]`, PEP 621)

meson-python fills `name`/`version` from `project()` in `meson.build` by default;
richer metadata lives in `[project]` (`description`, `readme`, `license` +
`license-files`, `requires-python`, `dependencies`, `classifiers`,
`[project.urls]`, `[project.scripts]`). If the version comes from VCS, declare it
dynamic and compute it in `meson.build` (step 5):

```toml
[project]
name = "mypkg"
dynamic = ["version"]
```

## 4. Write `meson.build`

Minimal native module (from the tutorial):

```meson
project('mypkg', 'c',
    meson_version: '>=1.6.0',
    version: '0.1.0',                       # or dynamic — see step 5
)

py = import('python').find_installation(pure: false)   # pure:false => platlib

py.extension_module('_core', '_core.c',
    install: true,
    subdir: 'mypkg',                        # install into the package dir
)

py.install_sources(                         # pure-Python sources
    'mypkg/__init__.py', 'mypkg/api.py',
    subdir: 'mypkg',
)
```

**Only installed targets land in the wheel** — this is the packaging contract.
Use `install_subdir` for a whole tree, `subdir:` to place artifacts in the right
package. See `reference/meson-cookbook.md` for dependencies, generators, Cython,
and the setuptools→Meson mapping.

**Strongly prefer a `src/` layout** — keep sources under `src/mypkg/` and install
into `subdir: 'mypkg'` (reference the files as `src/mypkg/...`). Without it the
project root is on `sys.path`, so tests and tools import from your *checkout*, not
the *installed* wheel — precisely the packaging bugs meson-python's
"only installed targets ship" contract is meant to expose (a source file never
listed in `install_sources`, a missing sub-package, data files left out) stay
hidden until a user hits them. A `src/` layout forces imports through the built
artifact, so build-install-test catches them in CI. Endorsed by the Scientific
Python guide, pyOpenSci, and Hynek Schlawack. **Do not move files into `src/`
automatically** — a relayout rewrites paths and can obscure `git blame`/`log`
across the renames. Recommend it, and only do it **if the user asks**; when they
do, use `git mv` in a dedicated, rename-only commit so history follows.

## 5. VCS / dynamic version (optional but recommended)

A static `version = "…"` in `project()` is perfectly valid. Deriving it from the
git tag is optional, but useful — one source of truth, no stale version edits.
Unlike scikit-build-core (which has a
[dynamic-metadata provider](https://scikit-build-core.readthedocs.io/en/latest/configuration/dynamic.html)
system), meson-python reads the version straight from `project(... version:
...)`, so the natural place to derive it is **at configure time inside
`meson.build`**. The pattern from pycxxfilt (`reference/example.md`), using the
`vcs-versioning` tool:

```meson
project('mypkg', 'c',
    meson_version: '>=1.6.0',
    # Derive the version from the latest git tag; falls back to the sdist's
    # PKG-INFO outside a git checkout. find_program picks meson-python's build
    # interpreter (which has the versioning dep) over a bare PATH python3.
    version: run_command(
        find_program('python3', 'python', version: '>= 3.11'),
        '-m', 'vcs_versioning',
        check: true,
    ).stdout().strip(),
)
```

```toml
[project]
dynamic = ["version"]                       # required: version not static

[build-system]
requires = ["meson-python>=0.17", "meson>=1.6", "vcs-versioning>=2.3.2"]
```

Two things make this robust: `run_command(..., check: true)` fails the build
loudly if versioning breaks, and the sdist ships `PKG-INFO`, so the same
`meson.build` resolves a version when built from an sdist with no `.git`. (Any
tool that prints a version to stdout works here; `setuptools-scm` has a
`--version`-style entry point too.)

## 6. Port track only: map `Extension(...)` → Meson

Translate the setuptools build into `meson.build`:

| setuptools | Meson |
| --- | --- |
| `Extension(sources=[...])` | `py.extension_module('_x', ['a.c', ...])` |
| `include_dirs` | `include_directories(...)` → `include_directories:` kwarg |
| `libraries` / `library_dirs` | `dependency(...)` / `cc.find_library(...)` |
| `define_macros` | `c_args: ['-DFOO=1']` |
| `extra_compile_args` | `c_args:` / `cpp_args:` |
| `package_data` / `MANIFEST.in` | `install_sources` / `install_subdir` / `install_data` |
| generated files (Cython, protobuf) | `generator()` / `custom_target()` |

Prefer `dependency('foo')` (pkg-config/CMake discovery) over hard-coded paths.
Details and examples: `reference/meson-cookbook.md`.

## 7. `[tool.meson-python]` and passing Meson args

Backend options live under `[tool.meson-python]`; forward args to the Meson
stages there or per-build via config-settings:

```toml
[tool.meson-python.args]
setup = ["-Dfeature=enabled"]      # meson setup
compile = ["-j8"]                  # ninja
```

```bash
pip install . -Csetup-args=-Dfoo=bar -Ccompile-args=-j8   # one -C per arg
```

Keys: `args.setup` / `args.compile` / `args.install` / `args.dist`, plus
`limited-api`, `editable-verbose`, `wheel.exclude`/`wheel.include`. Full table:
`reference/meson-cookbook.md`.

## 8. Editable installs and the dev workflow

```bash
pip install meson-python meson ninja                     # build deps present
pip install --no-build-isolation --editable .            # rebuilds on import
uv build                                                 # sdist + wheel (or: python -m build)
```

`--no-build-isolation` is required: rebuild-on-import needs the build deps at
runtime. The build dir is named per ABI tag (`build/cp311/`), so multiple
interpreters coexist. `MESONPY_EDITABLE_VERBOSE=1` (or
`-Ceditable-verbose=true`) shows rebuild output. **Caveat:** don't locate data
files with `__file__` under an editable install — use `importlib.resources`.
Metadata changes (deps, entry points) need a reinstall.

## 9. Optional: abi3 / limited-API wheel

Three coordinated pieces (per the limited-API guide):

```meson
py.extension_module('_core', '_core.c',
    limited_api: '3.11',       # sets Py_LIMITED_API; oldest supported minor
    install: true, subdir: 'mypkg',
)
```

```toml
[tool.meson-python]
limited-api = true             # wheel ABI tag becomes abi3
```

Make it opt-in and free-threading-safe by adding
`default_options: ['python.allow_limited_api=false']` to `project()`, then enable
per build: `-Csetup-args=-Dpython.allow_limited_api=true`. Free-threaded CPython
(3.13/3.14) does **not** support the limited API — keep it off there. The wheel's
Python tag follows the *build* interpreter, so build on the oldest CPython you
support (e.g. `cp311-abi3`). pycxxfilt does exactly this (`reference/example.md`).

## 10. Wheels / CI

Drive `cibuildwheel` from `pyproject.toml`. For abi3, build the stable-ABI wheel
only on your floor Python and audit it:

```toml
[[tool.cibuildwheel.overrides]]
select = "cp311-*"
config-settings = { setup-args = "-Dpython.allow_limited_api=true" }
```

Add `abi3audit` (abi3) or `auditwheel`/`delocate` (manylinux/macOS) as the gate.

## 11. Verify and delete the old build

1. `uv build` → sdist **and** wheel, no `setup.py` involved.
2. `pip install dist/*.whl` in a clean env; `import mypkg`; run the tests.
3. Build from the *sdist* too (`pip install dist/*.tar.gz`) — this exercises the
   VCS-version fallback to `PKG-INFO` (step 5).
4. Editable install + touch one source → confirm the on-import rebuild.
5. Delete `setup.py`, `setup.cfg`, `MANIFEST.in`; update docs/CI that called
   `python setup.py`.

**Definition of done:** `uv build` yields an installable sdist + wheel
with no `setup.py`; the package imports and tests pass from both wheel and sdist;
editable install rebuilds on import; and, if targeted, one abi3 wheel loads
across Python versions.
