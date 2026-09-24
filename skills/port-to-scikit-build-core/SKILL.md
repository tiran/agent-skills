---
name: port-to-scikit-build-core
description: >-
  Migrate a Python package with a compiled (C/C++/CUDA) extension from a bespoke
  setuptools / setup.py build to scikit-build-core + CMake (PEP 517/518/621).
  Covers the pyproject.toml build backend, CMakeLists install rules, dynamic
  versioning, editable installs, wheels/CI, and optional abi3 via nanobind. Use
  when asked to modernize a package's build, adopt scikit-build-core or CMake,
  get rid of setup.py, or produce standards-based wheels for an extension module.
---

# Port a package build to scikit-build-core + CMake

**Status: Experimental** — this workflow is distilled from two real but
*experimental* migrations (see `reference/examples.md`); the reference branches
are not yet merged. Follow it, but expect to adapt, and have a human review the
build on every target platform.

Move a package from hand-written `setup.py` (setuptools `Extension` /
`CUDAExtension`, `MANIFEST.in`, custom `build_ext`) to a **declarative**
`pyproject.toml` where **CMake builds the native code** and **scikit-build-core**
turns it into wheels and sdists. Work in the order below.

## Why bother (the case over bespoke setuptools)

setuptools was never a native-build system; every hybrid project reinvents the
same glue. scikit-build-core is the maintained, standards-based PEP 517 backend
purpose-built for the CMake+Python hybrid. Concretely you gain:

- **Declarative, less code.** PyTorch's migration retires *"over 2,000 lines of
  bespoke build orchestration"* for `pyproject.toml` config. `setup.py` goes away.
- **Standards.** PEP 517/518 build, PEP 621 metadata, PEP 639 license — the
  interfaces the rest of the ecosystem (pip, build, uv, cibuildwheel) targets.
- **CMake does what it is good at.** Real dependency graphs, cross-platform and
  cross-compilation, `find_package`, incremental rebuilds — the CMake cache and
  `ccache`/`sccache` carry over between builds.
- **Editable installs done right.** Python sources import from your checkout while
  compiled artifacts import from the build location; optional auto-rebuild.
- **CMake options are first-class.** Pass them per-build with
  `-Ccmake.define.USE_CUDA=ON`; no bespoke `--global-option` hacks.

Rationale and quotes: `reference/benefits.md`. PyTorch's own switch (setup.py
removed 2026-07-20): <https://dev-discuss.pytorch.org/t/3414>.

**Authoritative sources** (if this skill disagrees with them, they win):

- scikit-build-core docs — <https://scikit-build-core.readthedocs.io/en/stable/>
  (config reference: <https://scikit-build-core.readthedocs.io/en/stable/reference/configs.html>;
  dynamic metadata: <https://scikit-build-core.readthedocs.io/en/latest/configuration/dynamic.html>)
- CMake docs — `FindPython`
  (<https://cmake.org/cmake/help/latest/module/FindPython.html>) and `install`
  (<https://cmake.org/cmake/help/latest/command/install.html>)
- PyTorch CMake / C++ extension support — LibTorch + `find_package(Torch)`
  (<https://docs.pytorch.org/cppdocs/installing.html>) and
  `torch.utils.cpp_extension` (<https://docs.pytorch.org/docs/stable/cpp_extension.html>)
- nanobind build system (abi3, step 9) —
  <https://nanobind.readthedocs.io/en/latest/building.html>

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Check upstream, then inventory the current build

**First, check upstream for prior work** ([`../GUARDRAILS.md`](../GUARDRAILS.md) →
*Prior work*): someone may already have a scikit-build-core / CMake branch, PR, or
a discussion about why it stalled. Find the upstream repo (`git remote -v`,
`[project.urls]`) and search its issues + PRs (open/merged/closed) for
`scikit-build`, `cmake`, `pyproject`, `meson`. Report what you find before porting.

Then inventory the current build:

```bash
ls setup.py setup.cfg pyproject.toml MANIFEST.in CMakeLists.txt 2>/dev/null
grep -nE 'Extension|CUDAExtension|CppExtension|build_ext|cmdclass|ext_modules' setup.py
find . -name CMakeLists.txt
```

Classify into one of two **tracks** — the destination (steps 2–11) is identical;
only steps 1 and 4 differ:

- **Track A — existing CMake core + `setup.py` glue** (PyTorch, coremltools). The
  native build already lives in `CMakeLists.txt`; `setup.py` only orchestrates it.
  Easiest path: keep the CMake build, add `install()` rules (step 4), delete the
  glue, point scikit-build-core at it.
- **Track B — torch `cpp_extension` only, no CMake** (`CppExtension` /
  `CUDAExtension` in `setup.py`, no `CMakeLists.txt`). You must *author* a
  `CMakeLists.txt` (step 4) that reproduces what the `Extension(...)` implied:
  sources, torch headers/libs, include dirs, defines, and compiler flags.

Note anything the old build did imperatively: generated files (protobuf, version),
vendored deps, data files, `package_data`, custom compiler flags.

## 2. Declare the build backend

```toml
[build-system]
requires = ["scikit-build-core>=1.0"]   # add nanobind / pybind11 / numpy / torch as needed
build-backend = "scikit_build_core.build"
```

Everything else lives under `[project]` (PEP 621 metadata) and `[tool.scikit-build]`.

## 3. Move metadata to `[project]` (PEP 621)

Translate `setup(name=…, version=…, install_requires=…, packages=…)` into a
`[project]` table: `name`, `description`, `readme`, `authors`, `license` +
`license-files`, `requires-python`, `dependencies`, `classifiers`,
`[project.urls]`. If the version is derived from git, mark it `dynamic` (step 6).

## 4. Author / adapt `CMakeLists.txt`

The contract with scikit-build-core is simple: **whatever CMake `install()`s lands
in the wheel.**

**Track A (existing CMake):** you likely only need to *add the install rules* —
point each existing target at its package dir (`install(TARGETS foo LIBRARY
DESTINATION mypkg)`) and make `find_package(Python …)` use `Development.Module`.
Skip the target-authoring below.

**Track B (torch cpp_extension → CMake):** author the target. Minimum viable
native module:

```cmake
cmake_minimum_required(VERSION 3.18)
project(mypkg LANGUAGES CXX)

# scikit-build-core supplies the hints; use the modern FindPython.
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

# pick ONE binding path:
#   pybind11:  find_package(pybind11 CONFIG REQUIRED); pybind11_add_module(_C src...)
#   nanobind:  find_package(nanobind CONFIG REQUIRED); nanobind_add_module(_C src...)
#   plain:     Python_add_library(_C MODULE src...)
Python_add_library(_C MODULE src/mymod.cpp WITH_SOABI)

# The extension must be installed INTO the package dir so it ships in the wheel.
install(TARGETS _C LIBRARY DESTINATION mypkg)
```

Details in `reference/examples.md` (real coremltools + nanobind CMake). Common
`Extension(...)` → CMake mappings: `sources` → target sources; `include_dirs` →
`target_include_directories`; `define_macros` → `target_compile_definitions`;
`libraries`/`library_dirs` → `target_link_libraries` / `find_package`;
`extra_compile_args` → `target_compile_options`. For CUDA add
`LANGUAGES CXX CUDA` and `find_package(CUDAToolkit REQUIRED)`.

**Track B, torch specifics.** `CppExtension`/`CUDAExtension` silently injected
torch's include dirs, libraries, ABI flags, and a `-DTORCH_EXTENSION_NAME`. In
CMake, reproduce them with torch's own CMake package:

```cmake
# expose torch's CMake config: -Ccmake.define.CMAKE_PREFIX_PATH=$(python -c
# 'import torch;print(torch.utils.cmake_prefix_path)') — or find it in CMake.
find_package(Torch REQUIRED)
target_link_libraries(_C PRIVATE ${TORCH_LIBRARIES})        # classic ABI: link torch
target_compile_definitions(_C PRIVATE TORCH_EXTENSION_NAME=_C)
```

If you are *also* porting to the stable ABI (`port-to-torch-stable-abi`), do
**not** link torch: use `find_package(Torch REQUIRED)` for headers/flags only,
drop `${TORCH_LIBRARIES}`, and add `-DTORCH_TARGET_VERSION=…` — the kvcached
nanobind branch in `reference/examples.md` is exactly this case.

## 5. Configure `[tool.scikit-build]`

```toml
[tool.scikit-build]
minimum-version = "1.0"
build-dir = "build/{wheel_tag}"     # per-tag cache dir → fast incremental rebuilds
cmake.version = ">=3.18"
cmake.build-type = "Release"
wheel.packages = ["mypkg"]          # pure-Python sources collected from the tree
```

Pass CMake options at build time instead of editing files:
`-Ccmake.define.USE_CUDA=ON`, `-Ccmake.args=-DFOO=BAR`.

**Strongly prefer a `src/` layout** (`src/mypkg/`, `wheel.packages =
["src/mypkg"]` — scikit-build-core auto-detects `src/`). Without it, the project
root is on `sys.path`, so tests and tools import from your *checkout* instead of
the *installed* wheel — exactly the packaging bugs this migration is meant to
catch (a compiled module not installed into the package, a missing sub-package,
data files left out of the wheel) stay hidden until a user hits them. A `src/`
layout forces every import to go through the built artifact, so `uv build`
+ install-and-test surfaces those errors in CI. Endorsed by the Scientific Python
guide, pyOpenSci, and Hynek Schlawack. **Do not move files into `src/`
automatically** — a relayout rewrites paths and can obscure `git blame`/`log`
across the renames. Recommend it, and only do it **if the user asks**; when they
do, use `git mv` in a dedicated, rename-only commit so history follows.

## 6. Dynamic version (optional but recommended)

scikit-build-core has a [dynamic-metadata](https://scikit-build-core.readthedocs.io/en/latest/configuration/dynamic.html)
system: any PEP 621 field listed in `dynamic` can be filled at build time by a
provider (built-ins live under `scikit_build_core.metadata.*`). A static
`version = "…"` is perfectly valid; deriving it is optional, but it keeps one
source of truth and avoids stale edits. Two common scenarios:

**A. From VCS (git tags), via `setuptools_scm`.** Add `"setuptools-scm>=8"` to
`build-system.requires`.

```toml
[project]
dynamic = ["version"]

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.setuptools_scm"   # version-specific: no `field` key

[tool.setuptools_scm]
# optional: also write the resolved version to an importable file
version_file = "mypkg/_version.py"  # generated at build time (gitignore it)
```

If you set `version_file` (optional — omit it if the package doesn't need
`__version__` at runtime), the file is gitignored, so force-include it (step 7)
or scikit-build-core will skip it.

**B. From a static file already in the tree, via the `regex` provider.** Keep the
version in e.g. `mypkg/__init__.py` and read it out — no setuptools-scm, no git
needed.

```toml
[project]
dynamic = ["version"]

[[tool.dynamic-metadata]]
field = "version"
provider = "scikit_build_core.metadata.regex"
input = "mypkg/__init__.py"         # regex defaults to __version__ = "…"
```

Pick A when the git tag is the source of truth (releases from CI), B when a
checked-in file is. Other built-in providers: `fancy_pypi_readme` (render the
README) and `template` (compose one field from others).

## 7. Package data, generated files, sdist

scikit-build-core **honors `.gitignore`** when collecting package files. For
generated-but-shipped files (protobuf `*_pb2.py`, `version.py`) use:

```toml
[tool.scikit-build.wheel.force-include]
"mypkg/version.py" = "mypkg/version.py"
```

Control the sdist contents under `[tool.scikit-build.sdist]` (`include`/`exclude`);
the sdist is built from the git tree, which must contain the CMake build system and
all C++/CUDA sources.

## 8. Editable installs and the dev workflow

```bash
pip install scikit-build-core cmake ninja             # build deps present for --no-build-isolation
pip install -e . --no-build-isolation                 # editable dev install
pip install -e . --no-build-isolation -Ceditable.rebuild=true   # auto-rebuild on import
uv build --wheel --no-build-isolation                 # build a wheel (or: python -m build --wheel --no-isolation)
```

`--no-build-isolation` needs the backend and native toolchain already in the
env (first line); the editable auto-rebuild also needs them present at import
time. Replace old `python setup.py …` invocations: `develop` → editable install above;
`bdist_wheel` → `uv build` (or `python -m build`); `install` → `pip install .`.

## 9. Optional: abi3 / free-threading via nanobind

If you also want one wheel across Python versions (abi3), nanobind is the natural
fit and is CMake-native — this is where this skill meets
`port-to-torch-stable-abi` (step 13/17). Pattern (kvcached nanobind branch):

```cmake
nanobind_add_module(_C STABLE_ABI NB_STATIC ${SOURCES})   # STABLE_ABI => .abi3.so on ≥3.12
install(TARGETS _C LIBRARY DESTINATION mypkg)
```

```toml
[tool.scikit-build]
wheel.py-api = "cp312"   # emit cp312-abi3 on 3.12+; per-version wheels below
```

Disable abi3 on free-threaded builds **before CPython 3.15** (pip refuses abi3
there). From 3.15, the combined **`abi3.abi3t`** tag (`wheel.py-api =
"cp315.cp315t"`, CMake ≥4.4) ships one wheel for regular *and* free-threaded
Python — see [PEP 803](https://peps.python.org/pep-0803/) and the full abi3/abi3t
model in
[`port-to-python-limited-api`](../port-to-python-limited-api/reference/background.md).
pybind11 is *not* abi3-capable; use nanobind or a hand-written `PyType_FromSpec`
module.

## 10. Wheels / CI

Drive `cibuildwheel` from `pyproject.toml` (`[tool.cibuildwheel]`): select
Python versions, `test-requires`, and an audit gate (e.g. `abi3audit` for abi3
wheels, `auditwheel`/`delocate` for manylinux/macOS). CMake caching + `ccache`
still applies inside the CI containers. For the publish/release half — building
wheels from the sdist, Trusted Publishing to PyPI, hardened permissions — see
[`secure-python-release-pipeline`](../secure-python-release-pipeline/).

## 11. Verify and delete the old build

1. `uv build` → produces both sdist and wheel with no `setup.py`. `uv build`
   (like `python -m build`) builds the wheel *from* the sdist by default, so this
   already catches a broken sdist — missing CMake sources, or a VCS-version
   fallback to `PKG-INFO` — before you install anything.
2. `pip install dist/*.whl` in a clean env; `import mypkg`; run the test suite.
3. Rebuild incrementally (touch one source) and confirm the CMake cache is reused.
4. Delete `setup.py`, `setup.cfg` (if fully migrated), and `MANIFEST.in`; update
   `BUILDING.md`/docs and any `python setup.py` calls in scripts/CI.

**Definition of done:** `uv build` yields installable sdist + wheel with no
`setup.py`; the package imports and tests pass from the wheel; editable install and
incremental rebuild work; docs/CI no longer invoke `setup.py`.
