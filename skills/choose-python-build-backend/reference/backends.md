# Build backend assessment

Per-backend detail behind the SKILL decision. Each entry: **purelib/platlib**,
**metadata** (static / dynamic / VCS), **build system / language**, the exact
`[build-system]` block, and migration notes. Sources:
[PyPA tool recommendations](https://packaging.python.org/en/latest/guides/tool-recommendations/),
[pyOpenSci build tools](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-build-tools.html),
[Scientific Python compiled guide](https://learn.scientific-python.org/development/guides/packaging-compiled/),
each backend's own docs.

## Quick comparison

| Backend | purelib | platlib (compiled) | Static meta | Dynamic / VCS version | Build system | Best for |
| --- | :-: | :-: | :-: | :-: | --- | --- |
| **uv-build** | ✅ | ❌ | ✅ | ❌ | own (fast) | simple pure-Python in uv projects |
| **flit-core** | ✅ | ❌ | ✅ | ⚠️ `__version__` only | own (minimal) | simple, minimal pure-Python |
| **hatchling** | ✅ | ⚠️ via hook/plugin | ✅ | ✅ (hatch-vcs) | own + plugins | modern default; dynamic meta; light compiled |
| **meson-python** | ⚠️ | ✅ | ✅ | ✅ (in `meson.build`) | **Meson** | C/C++/Fortran/**Cython** (numpy/scipy) |
| **scikit-build-core** | ⚠️ | ✅ | ✅ | ✅ (providers) | **CMake** | CMake/CUDA/nanobind/**Cython**/Torch |
| **maturin** | ⚠️ | ✅ | ✅ | ✅ (Cargo/VCS) | **Cargo** | Rust (PyO3/cffi) |
| **setuptools** | ✅ | ✅ (C/C++; Rust via plugin) | ✅ | ✅ (setuptools-scm) | own/distutils | legacy; existing C-ext builds |

⚠️ = possible but not the primary use.

## Native language / toolchain → backend (primary selector for platlib)

For compiled projects the **language and build system decide the backend** — pick
this row first, then confirm metadata needs above.

| You have | Backend | Why |
| --- | --- | --- |
| Pure Python only | uv-build / flit-core / hatchling | no compiler involved |
| **Cython** (`.pyx`) | **meson-python** or **scikit-build-core** | both have first-class Cython support; pick by Meson vs CMake. meson-python is the mainstream scientific choice (NumPy, SciPy) for fast incremental/parallel builds + cross-compilation. **Not setuptools for new Cython projects** — Cython's own docs now recommend a modern backend. |
| C / C++ / Fortran, Meson-based | meson-python | Meson + Ninja |
| C / C++ / CUDA, CMake-based | scikit-build-core | reuses `CMakeLists.txt`; CUDA |
| **nanobind** bindings | scikit-build-core | CMake-native; one **abi3** wheel |
| **pybind11** bindings | scikit-build-core or meson-python | both work; **not** abi3-capable (wheel per Python) |
| Rust (PyO3/cffi) | maturin | Cargo-native, abi3 |
| PyTorch C++/CUDA extension | scikit-build-core (+ torch stable-ABI) | `find_package(Torch)` |
| Small C bit inside a mostly-pure package, want hatchling | hatchling + `scikit-build-core[hatchling]` or custom hook | keep hatchling metadata |
| Existing, working setuptools C-extension | setuptools (+ setuptools-rust for Rust) | don't churn a healthy build without a reason |

Cython source: the Cython
[Source Files and Compilation guide](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html)
now recommends a modern build backend for larger packages and points to the
Scientific Python ecosystem's Meson-first choice.

## Compiled-project considerations: bindings, abi3, parallel builds

Three cross-cutting concerns for platlib projects, and how each backend fares:

| Concern | scikit-build-core | meson-python | maturin | setuptools |
| --- | --- | --- | --- | --- |
| C++ **binding lib** | pybind11, **nanobind**, SWIG, Cython, f2py | pybind11, Cython, Boost.Python (via Meson deps) | n/a (Rust) | pybind11, Cython (manual) |
| **abi3 / stable ABI** (one wheel/Python) | ✅ `wheel.py-api="cp3x"`; nanobind `STABLE_ABI` | ✅ `limited-api=true` + `limited_api:` | ✅ abi3 feature | ⚠️ manual |
| **Parallel / incremental** | ✅ CMake + Ninja, default | ✅ Meson + Ninja, default | ✅ Cargo | ❌ no parallel-build isolation |

Notes:

- **nanobind vs pybind11 for abi3.** Only **nanobind** produces a stable-ABI
  (abi3) extension — one wheel loads on all CPython ≥3.12. **pybind11 cannot** do
  abi3 (its type machinery isn't limited-API-compatible), so it emits a wheel per
  Python version. If a single abi3 wheel is a goal, that's a reason to choose
  nanobind (→ [`pybind11-to-nanobind`](../../pybind11-to-nanobind/SKILL.md)) on a
  CMake backend (scikit-build-core). Related: hand-written `PyType_FromSpec`
  modules can also be abi3.
- **Free-threaded CPython and abi3** — the limited API isn't available on
  free-threaded builds **before 3.15**, so keep abi3 off there and emit a
  per-version free-threaded wheel. From **CPython 3.15**,
  [PEP 803](https://peps.python.org/pep-0803/) introduces **abi3t**, a stable ABI
  whose set of compatible interpreters is a *superset* of abi3's (a `.abi3t.so`
  loads on **both** GIL-enabled and free-threaded 3.15+). Ship it with the
  **combined `abi3.abi3t` tag** — scikit-build-core 1.0
  (`wheel.py-api = "cp315.cp315t"`, needs CMake ≥4.4), maturin (`abi3t-py315`),
  or meson-python — and one stable-ABI wheel serves regular *and* free-threaded
  CPython ≥3.15. (An `abi3t`-*only* tag would restrict the wheel to free-threaded
  interpreters, so emit the combined tag.)
- **Parallel builds** are why NumPy and SciPy left setuptools for Meson: Ninja
  gives fast incremental and parallel compilation; setuptools does neither well
  and has **no isolation** when parallel builds share a working directory
  ([issue #3119](https://github.com/pypa/setuptools/issues/3119)). CMake respects
  `CMAKE_BUILD_PARALLEL_LEVEL`; Meson/Ninja parallelize by default.
- **PyTorch** extensions typically combine all three: `find_package(Torch)`
  (CMake → scikit-build-core), the Torch **stable ABI** + **nanobind** for a
  single abi3 wheel, and CMake+Ninja parallelism for CUDA. See
  [`port-to-torch-stable-abi`](../../port-to-torch-stable-abi/SKILL.md).

## uv-build (`uv_build`)

- **purelib only.** No extension modules — stop here if you have C/Cython/Rust.
- **Metadata:** static only. **No dynamic/VCS version**, no build hooks/scripts
  (generated files must exist before the build).
- **Build system:** Astral's own, **10–35× faster** than the others; the default
  declared by `uv init` since mid-2025.
- **Layout constraint:** expects one module dir named after the project,
  normalized (`acme-widgets` → `src/acme_widgets/`).

```toml
[build-system]
requires = ["uv_build>=0.9"]
build-backend = "uv_build"
```

Choose it when the project is pure Python, static, and you already use uv.
(`uv init` emits an upper-capped pin because `uv_build` tracks the uv version;
that's uv's own template, not a cap you need to author or maintain by hand — a
lower bound is enough.)

## flit-core

- **purelib only.**
- **Metadata:** static; the one dynamic feature is reading the version from a
  module's `__version__` string:

  ```toml
  [project]
  dynamic = ["version"]
  [tool.flit.module]
  name = "mypkg"          # flit reads __version__ (and the docstring for description)
  ```
- **Build system:** deliberately minimal; no plugin system, no compiled support.

```toml
[build-system]
requires = ["flit_core>=3.11"]
build-backend = "flit_core.buildapi"
```

Choose it for a small, static, pure-Python package when you want the least config.

## hatchling

- **purelib** (simple → complex) and **platlib via a build hook** (below).
- **Metadata:** full dynamic metadata; **VCS versioning via `hatch-vcs`**:

  ```toml
  [build-system]
  requires = ["hatchling", "hatch-vcs"]
  build-backend = "hatchling.build"
  [project]
  dynamic = ["version"]
  [tool.hatch.version]
  source = "vcs"
  ```
- **Build system:** Hatchling's own, with a real **plugin/hook** system.
- **Defaults:** sdist contents follow `.gitignore` (no `MANIFEST.in`); wheel
  inclusion is strict (errors rather than silently shipping stray dirs);
  reproducible builds by default.
- **Compiled with hatchling:** two routes —
  - `scikit-build-core[hatchling]` — runs a CMake build as a Hatchling build hook,
    so you keep hatchling metadata/versioning while CMake compiles.
  - a **custom build hook**:
    `[tool.hatch.build.targets.wheel.hooks.custom]` + a `hatch_build.py`
    implementing a `BuildHookInterface` that compiles the extension.
  For anything beyond a small extension, prefer a dedicated compiled backend.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

A safe general-purpose choice — the backend in PyPA's *Writing your pyproject.toml*
example, and one of two PyPA-maintained backends.

## meson-python (`mesonpy`)

- **platlib** (its reason to exist); can do purelib but that's not the point.
- **Metadata:** static in `[project]`; version can be **computed in
  `meson.build`** at configure time (VCS or from `PKG-INFO` in an sdist).
- **Build system:** **Meson** (+ Ninja) — fast incremental & parallel builds,
  strong cross-compilation. Native **Cython**, C, C++, Fortran support.
- **Adoption:** NumPy and SciPy migrated to it, explicitly for build speed,
  incremental/parallel builds, and cross-compilation that setuptools lacked.

```toml
[build-system]
requires = ["meson-python>=0.17", "meson>=1.6"]
build-backend = "mesonpy"
```

→ Migration: [`port-to-meson-python`](../../port-to-meson-python/SKILL.md).

## scikit-build-core

- **platlib.**
- **Metadata:** static, plus a **dynamic-metadata provider** system (setuptools_scm
  for VCS, regex, fancy_pypi_readme, template).
- **Build system:** **CMake** (parallel by default via Ninja). First-class
  **pybind11, nanobind, Cython, SWIG, Fortran (f2py)**; reuses an existing
  `CMakeLists.txt` with no setuptools shim. Early to support free-threaded /
  stable-ABI (abi3) tags.
- **Best for:** CMake-based projects, CUDA, nanobind, and Torch extensions
  (`find_package(Torch)`), or C/C++/Fortran too involved for setuptools.

```toml
[build-system]
requires = ["scikit-build-core>=1.0"]
build-backend = "scikit_build_core.build"
```

→ Migration: [`port-to-scikit-build-core`](../../port-to-scikit-build-core/SKILL.md)
(abi3/nanobind pairs with [`pybind11-to-nanobind`](../../pybind11-to-nanobind/SKILL.md)
and [`port-to-torch-stable-abi`](../../port-to-torch-stable-abi/SKILL.md)).

## maturin

- **platlib**, Rust — PyO3 / rust-cpython / cffi. Also supports mixed
  Rust + Python source trees.
- **Metadata:** static `[project]`; version can come from `Cargo.toml` / VCS.
- **Build system:** **Cargo**; produces abi3 wheels easily; integrates with
  cibuildwheel.

```toml
[build-system]
requires = ["maturin>=1.7"]
build-backend = "maturin"
```

The standard choice for Rust extensions.

## setuptools (legacy path)

- **purelib and platlib** — native **C/C++**; **Rust via setuptools-rust**.
- **Metadata:** static `[project]` (≥61); **VCS via setuptools-scm**; PEP 639
  licenses need ≥77.
- **Build system:** its own (distutils-derived). Widest legacy feature set and
  plugin ecosystem, but:
  - **No isolation for parallel builds** sharing a working dir — concurrent wheel
    builds can trample each other and fail non-deterministically.
  - sdist inclusion needs `MANIFEST.in`; wheel package auto-discovery can ship
    unintended dirs; sdists are **not guaranteed reproducible**.
  - The legacy `setup.py develop` editable path is being removed from the
    pip/setuptools stack (declare `requires=["setuptools>=64"]` + PEP 517 to stay
    on the modern editable mechanism).

```toml
[build-system]
requires = ["setuptools>=77", "setuptools-scm>=8"]   # scm optional; ≥77 for PEP 639
build-backend = "setuptools.build_meta"
```

Keep it for an existing, working C-extension build; for **new** compiled projects
prefer scikit-build-core / meson-python / maturin. See `why-not-setuptools.md`.

### Forcing a platlib wheel (prebuilt / external binaries)

setuptools decides **purelib vs platlib** from whether the `Distribution` reports
`ext_modules`. If you ship a **prebuilt** binary — a `.so`/`.dll`/`.dylib` built by
an external toolchain (Rust/Go/CMake, or a vendored/downloaded lib loaded via
ctypes/cffi) with **no setuptools `Extension`** — setuptools sees a pure package and
tags the wheel `py3-none-any` (purelib). That is **wrong and dangerous**: a
platform-specific wheel gets installed on every platform. Force platlib one of two
ways; they produce **different tags** — pick by whether the binary is bound to the
CPython ABI.

**Prerequisite — a `pyproject.toml` with a setuptools floor.** Both recipes keep a
`setup.py`, but under PEP 517 build isolation the build runs against whatever
`[build-system].requires` pins — not your local setuptools. So the project **must**
ship a `pyproject.toml`, and the floor **must** be high enough, or the isolated
build env can pull an older setuptools that lacks the integrated `bdist_wheel`
(recipe 2's import fails) or silently builds the purelib default:

```toml
[build-system]
requires = ["setuptools>=70.1"]
build-backend = "setuptools.build_meta:__legacy__"
```

`70.1` is the floor for recipe 2 (integrated `bdist_wheel` command); recipe 1 only
needs a setuptools new enough to build wheels, but `>=70.1` is the safe floor for
both and lets you drop the separate `wheel` build dep.

Both recipes live in `setup.py`, so use the **`:__legacy__`** backend. It puts the
project root on `sys.path`, so a `setup.py` that imports a sibling module (a local
`_build.py`, a version helper) keeps working — the same behavior a project gets with
no `[build-system]` table at all. The plain `setuptools.build_meta` is stricter and
does **not** add the root to `sys.path`; switch to it only once the `setup.py` has
no such imports.

**1. Mark the distribution impure** — full **interpreter+ABI** tag
(`cp312-cp312-linux_x86_64`). Use when the binary is linked against a specific
CPython ABI:

```python
from setuptools import setup
from setuptools.dist import Distribution


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


setup(distclass=BinaryDistribution)
```

**2. Override `bdist_wheel`** — platform-specific but **ABI-agnostic** tag
(`py3-none-linux_x86_64`), so one wheel serves all Python 3.x. Use for a prebuilt
lib loaded via **ctypes/cffi** (not linked to the CPython ABI):

```python
# setuptools >= 70.1 (older setuptools: from wheel.bdist_wheel import bdist_wheel)
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel


class bdist_wheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False  # -> platlib

    def get_tag(self):
        _, _, plat = super().get_tag()
        return "py3", "none", plat  # any Python 3, ABI-agnostic, this platform


setup(cmdclass={"bdist_wheel": bdist_wheel})
```

- `root_is_pure = False` is what flips the install location to **platlib**; the
  `get_tag` override controls the **compatibility tag**.
- Recipe 2's `from setuptools.command.bdist_wheel import bdist_wheel` is why the
  floor above is **≥ 70.1** (2024-06, when setuptools absorbed `wheel`'s command).
  To support older setuptools instead, import `from wheel.bdist_wheel import
  bdist_wheel` and add `wheel` to `requires` — but since wheel 0.46 that module is a
  deprecated alias, so for new work keep the `setuptools>=70.1` pin and drop `wheel`.
- Neither trick sets a **minimum** platform floor (manylinux / macOS deployment
  target). Use `auditwheel`/`delocate` — or just build under **cibuildwheel** — to
  get portable, correctly-floored platform tags.
