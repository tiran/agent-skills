---
name: choose-python-build-backend
description: >-
  Recommend the right PEP 517 build backend for a new or existing Python package,
  and give enough context to migrate. Chooses by three axes: purelib (pure
  Python) vs platlib (compiled C/C++/Rust/Torch), static vs dynamic/VCS metadata,
  and native language/build system. Covers uv-build, flit-core, hatchling
  (incl. compiled via scikit-build-core[hatchling] / a custom build hook),
  meson-python, scikit-build-core, maturin, and setuptools (legacy). Weighs
  compiled-project concerns: Cython, PyTorch extensions, pybind11/nanobind
  bindings, the stable Python ABI (abi3 / limited API), and fast parallel
  builds (CMake+Ninja, Meson). Use when asked "which build backend should I use",
  to pick a backend for a new project, or to decide whether to move an existing
  project off setuptools.
---

# Choose a Python build backend

**Status: Experimental** — grounded in the PyPA tool recommendations and current
backend docs (linked below); the decision procedure is a new draft. Backends are
swappable (that's the point of PEP 517), so a wrong call is cheap to reverse — but
get it right up front and you avoid churn.

A **build backend** turns your source tree into an sdist and wheel. It does *not*
manage environments, resolve dependencies, or upload — PEP 517 standardizes the
interface so any frontend (pip, uv, build, cibuildwheel) drives any backend. That
means **for a simple pure-Python package the choice barely matters and is trivial
to change later**; it matters most for compiled projects and for dynamic metadata.
This skill picks a backend and points at the migration skill that does the work.

## Authoritative sources (if this skill disagrees with them, they win)

- PyPA tool recommendations —
  <https://packaging.python.org/en/latest/guides/tool-recommendations/>
- Writing pyproject.toml —
  <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
- pyOpenSci — Python packaging build tools —
  <https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-build-tools.html>
- Backends: [uv-build](https://docs.astral.sh/uv/concepts/build-backend/),
  [flit](https://flit.pypa.io/en/stable/),
  [hatchling](https://hatch.pypa.io/latest/config/build/) (["Why Hatch?"](https://hatch.pypa.io/latest/why/)),
  [meson-python](https://mesonbuild.com/meson-python/),
  [scikit-build-core](https://scikit-build-core.readthedocs.io/en/stable/),
  [maturin](https://www.maturin.rs/)
- Cython — build backend recommendation:
  <https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html>
  (Cython's own docs now recommend a modern backend, not setuptools, for new
  projects)

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Classify the project on three axes

```bash
# compiled code? (platlib vs purelib)
grep -rnE 'ext_modules|Extension|extension_module|pybind11|nanobind|\.pyx|Cargo.toml|CMakeLists.txt|meson.build' \
  setup.py pyproject.toml . 2>/dev/null | head
# current backend / metadata style
grep -nE 'build-backend|^\[project\]|dynamic\s*=|setuptools_scm|hatch-vcs' pyproject.toml setup.py setup.cfg 2>/dev/null
```

- **A. purelib vs platlib.** Pure Python (only `.py`, no compiled step) →
  **purelib**. Any C/C++/CUDA/Cython/Fortran/Rust that compiles per-platform →
  **platlib** (many wheels: OS × arch × ABI).
- **B. static vs dynamic metadata.** Can every field be written literally in
  `[project]` (**static**), or must something be computed at build time —
  version from a **git tag/VCS**, `readme` assembled, classifiers generated
  (**dynamic**)? See [`modernize-python-metadata`](../modernize-python-metadata/).
- **C. native language / build system.** **Cython** (`.pyx`)? Rust
  (`Cargo.toml`)? An existing CMake or Meson build? A Torch C++/CUDA extension?
  Plain hand-written C/C++? This is a primary selector — the language/toolchain,
  not just "compiled or not", picks the backend in step 3.

## 2. Pick — pure Python (purelib)

For a simple pure-Python library, **any PEP 517/621 backend works**; pick by
metadata needs and which project manager you use. Full per-backend assessment:
`reference/backends.md`.

- **Static metadata, using uv** → **uv-build** (`uv_build`). Fastest (10–35×),
  the default of `uv init`. Pure-Python only, **no dynamic/VCS version**,
  generated files must pre-exist, enforces one `src/<pkg>/` matching the name.
- **Static metadata, minimal, no uv** → **flit-core**. Deliberately no-frills.
  It *can* read the version from a module's `__version__` string (`dynamic =
  ["version"]`) — the one bit of dynamic it supports. Pure-Python only.
- **Dynamic metadata, VCS versioning, build hooks, or room to grow** →
  **hatchling**. A common, safe general-purpose choice — the backend PyPA uses in
  its *Writing your pyproject.toml* worked example, and one of two PyPA-maintained
  backends. Full dynamic metadata, VCS versioning via **hatch-vcs**, and a real
  plugin/hook system. Start here when in doubt.

Rule of thumb: **hatchling** is the safe general-purpose choice; drop to
**flit-core**/**uv-build** only when the package is simple, static, and you want
minimalism/speed.

## 3. Pick — compiled (platlib)

Choose by the native toolchain; each has a dedicated migration skill:

- **Rust** (PyO3/cffi) → **maturin**. Cargo-native, produces abi3 wheels,
  supports mixed Rust+Python projects.
- **CMake-based, nanobind, or consumes a CMake package** (e.g.
  `find_package(Torch)`) → **scikit-build-core**. CMake does the build; parallel
  by default via Ninja. → [`port-to-scikit-build-core`](../port-to-scikit-build-core/).
- **Meson-based, or plain C/C++/Fortran** (the numpy/scipy world) →
  **meson-python**. → [`port-to-meson-python`](../port-to-meson-python/).
- **Cython** → **meson-python** *or* **scikit-build-core** (both have first-class
  Cython support); pick by Meson-vs-CMake preference. meson-python is the
  mainstream scientific choice (NumPy and SciPy moved to Meson for fast
  incremental/parallel builds and cross-compilation). **Not setuptools for new
  Cython projects.** See `reference/backends.md`.
- **PyTorch C++/CUDA extension** → usually **scikit-build-core** (CMake +
  `find_package(Torch)`), especially if adopting the stable ABI. →
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) +
  `port-to-scikit-build-core`.
- **Mostly pure Python with a small compiled piece, and you want the hatchling
  ecosystem** → **hatchling + compiled**: either `scikit-build-core[hatchling]`
  (drives CMake as a Hatchling build hook) or a custom
  `tool.hatch.build.targets.wheel.hooks.custom` + `hatch_build.py`. Keeps
  hatchling's metadata/versioning while compiling. Details in `reference/backends.md`.
- **Legacy C/C++ extension you don't want to re-architect the build for** →
  **setuptools** (native C/C++) or **setuptools-rust** (Rust), with
  **setuptools-scm** for VCS versions. Valid, but see step 4.

All compiled backends support VCS/dynamic versioning through their own mechanism
(maturin from `Cargo.toml`/VCS, scikit-build-core via metadata providers,
meson-python computed in `meson.build`).

### Cross-cutting criteria for compiled projects

Beyond the language, three concerns often decide (or confirm) the pick — details
and a table in `reference/backends.md`:

- **Binding library (C++).** **nanobind** is CMake-native and produces **one abi3
  wheel** → **scikit-build-core** (pairs with
  [`pybind11-to-nanobind`](../pybind11-to-nanobind/)). **pybind11** works with
  scikit-build-core (CMake) or meson-python, but is **not abi3-capable** — you
  get a wheel per Python version.
- **Stable Python ABI (abi3 / limited API).** Want one wheel across CPython
  versions? **scikit-build-core** (`wheel.py-api = "cp3x"`, or nanobind
  `STABLE_ABI`), **meson-python** (`limited-api = true`), and **maturin** (abi3
  feature) all support it; **flit/uv/hatchling are purelib** (abi3 is moot);
  setuptools can but it's manual. Free-threaded CPython **before 3.15** has no
  abi3 — emit per-version free-threaded wheels there. Introduced in **Python
  3.15**, [PEP 803](https://peps.python.org/pep-0803/) adds **abi3t**, whose set
  of compatible interpreters is a *superset* of abi3's: a `.abi3t.so` loads on
  **both** GIL-enabled and free-threaded CPython ≥3.15, so a single wheel with the
  combined **`abi3.abi3t`** tag (scikit-build-core 1.0
  `wheel.py-api = "cp315.cp315t"`, maturin, and meson-python) covers regular *and*
  free-threaded Python from 3.15 — one stable-ABI wheel for everything.
- **Fast parallel / incremental builds.** **scikit-build-core (CMake + Ninja)**
  and **meson-python (Meson + Ninja)** are parallel and incremental by default —
  the reason NumPy/SciPy left setuptools. **setuptools has no isolation for
  parallel builds** sharing a work dir (they can trample each other); if you
  build many wheels concurrently, that alone points away from it.

### PyTorch extensions — the combined case

A Torch C++/CUDA extension usually hits several of the above at once: it needs
`find_package(Torch)` (CMake) → **scikit-build-core**; if you want one wheel
across Torch/Python versions, adopt the **Torch stable ABI** + **nanobind** for
**abi3**, and get CMake+Ninja parallelism for the heavy CUDA build. See
[`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) +
[`port-to-scikit-build-core`](../port-to-scikit-build-core/) +
[`pybind11-to-nanobind`](../pybind11-to-nanobind/).

## 4. Should an existing project move off setuptools?

**setuptools is not deprecated** and remains a fully valid PEP 517 backend
(≥61 reads `[project]`; ≥77 does PEP 639 licenses). What *is* deprecated is the
**legacy `python setup.py …` workflow** and the setuptools-specific editable
fallback. Reasons people move, and reasons to stay, are in
`reference/why-not-setuptools.md`; the short version:

**Reasons to prefer a modern backend (pure-Python especially):**
- **Better, safer defaults** — hatchling takes sdist contents from `.gitignore`
  (no `MANIFEST.in`) and is strict about what goes in the wheel; setuptools
  auto-discovers packages and can ship test/tooling dirs by accident.
- **Reproducible builds** by default (setuptools doesn't guarantee this).
- **Cleaner editable installs / IDE static analysis**; the old
  `setup.py develop` path is being removed from the pip/setuptools stack.
- **Simpler config** (one file, no `setup.py`/`setup.cfg`/`MANIFEST.in`) and a
  real plugin system.
- **More stable as a build dependency.** setuptools ships ~5 major versions/year
  and has a run of breaking changes and broken releases (seven yanked since early
  2024); because it builds *everyone's* packages, a bad release breaks builds
  broadly. Narrower backends change far less. (Details:
  `reference/why-not-setuptools.md`.)

**Reasons to stay on setuptools:**
- A **working compiled C/C++ build** via `Extension` you don't want to rewrite —
  setuptools natively supports C/C++ (and Rust via setuptools-rust). Migrating the
  *build* is the expensive part; don't churn it without a reason.
- Deep reliance on setuptools-specific features.

**Caveat — parallel builds:** setuptools has **no isolation against concurrent
builds sharing a working dir** (they can trample each other / fail
non-deterministically). If you build many wheels in parallel from one tree, this
alone is a reason to move compiled projects to scikit-build-core (CMake/Ninja
handle parallelism natively) or meson-python.

Bottom line: **new pure-Python project → hatchling** (or uv-build/flit for simple
static). **New compiled project → the language-appropriate backend above, not
setuptools.** **Existing setuptools pure-Python project → worth modernizing.
Existing setuptools C-extension that builds fine → migrate only when you have a
reason** (parallel builds, abi3, CMake/Meson features).

## 5. Migrating (the mechanics)

Switching backends is mostly declarative because PEP 517 standardizes the
interface — frontends don't care which backend you use:

1. **Metadata → `[project]`.** Move name/version/deps/etc. into a PEP 621
   `[project]` table (keep it static where you can). Use
   [`modernize-python-metadata`](../modernize-python-metadata/).
2. **Swap `[build-system]`.** Set `requires` + `build-backend` to the chosen
   backend (exact strings per backend in `reference/backends.md`).
3. **Backend-specific config.** File selection (`tool.hatch.build` /
   `tool.scikit-build` / `tool.meson-python`), dynamic version plugin, etc.
4. **Compiled builds are the real work** — authoring `CMakeLists.txt` /
   `meson.build` / Cargo config — and that's what the dedicated port-to-* skills
   cover. A pure-Python backend swap is usually a few lines.
5. **Verify:** `uv build` (or `python -m build`) produces sdist + wheel; install in a clean env
   and import/test; `uvx twine check dist/*`.

## Definition of done

A recommendation stating the backend, *why* (the three axes), the exact
`[build-system]` block, whether metadata should be static or dynamic, and — if
migrating — a pointer to the specific migration skill and the mechanical steps
above. For compiled projects, the recommendation names the native build system
(CMake/Meson/Cargo), not just the backend.
