---
name: pybind11-to-nanobind
description: >-
  Port a Python C++ extension's bindings from pybind11 to nanobind. Covers the
  mechanical API renames (NB_MODULE, def_rw/def_ro, python_error), the removed
  pybind11 features to design around (holders, py::array, multiple inheritance,
  module-local bindings), STL caster opt-in headers, custom __init__/type
  casters, the CMake nanobind_add_module build, and abi3/stable-ABI wheels. Use
  when asked to migrate to nanobind, cut binding compile time / binary size, or
  produce one abi3 wheel for a pybind11 extension.
---

# Port a C++ extension from pybind11 to nanobind

**Status: Experimental** — distilled from one real migration (the kvcached
nanobind branch, see `reference/example.md`) plus the upstream porting guide.
The API map is authoritative; the *workflow* is new, so adapt and have a human
review the result on every target platform.

nanobind is a near-drop-in successor to pybind11 by the same author, built for a
narrower slice of C++ in exchange for far smaller/faster bindings and real
stable-ABI (abi3) support. Most of the port is mechanical renaming; the work is
in the handful of features nanobind **removed** and in the build system, which
must move to CMake. Work in the order below.

## Why bother (the case over pybind11)

nanobind targets a subset of C++ so it can be smaller and faster; the codebase
adapts to the tool, not the other way around. Concretely:

- **Smaller, faster instances.** Per-instance overhead ~2.3× lower (56 → 24
  bytes); PEP 590 vector calls; the dispatch loop no longer allocates heap.
- **Faster builds, smaller binaries.** A precompiled `libnanobind` avoids
  redundant per-file compilation; STL casters are opt-in headers; LTO is no
  longer crucial.
- **Real abi3.** Targets Python's stable ABI from 3.12 (3.10 in split mode) —
  one wheel across Python versions. pybind11 cannot do this.
- **Better free-threading.** Localized locking scales across cores where
  pybind11 contends on a central `internals` lock.
- **N-d arrays via DLPack** (`nb::ndarray`, zero-copy NumPy/PyTorch/JAX) and
  automatic type-stub generation.

Rationale and numbers: `reference/example.md` and
<https://nanobind.readthedocs.io/en/latest/why.html>.

**Authoritative sources** (if this skill disagrees with them, they win):

- Porting from pybind11 — <https://nanobind.readthedocs.io/en/latest/porting.html>
- Why nanobind — <https://nanobind.readthedocs.io/en/latest/why.html>
- Building / CMake (`nanobind_add_module`) —
  <https://nanobind.readthedocs.io/en/latest/building.html>
- API reference — <https://nanobind.readthedocs.io/en/latest/api_core.html>

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse.

## 1. Assess: check upstream, is nanobind a fit, and how big is the port?

**First, check upstream for prior work** ([`../GUARDRAILS.md`](../GUARDRAILS.md) →
*Prior work*): someone may already have a nanobind branch, PR, or a discussion
about why it stalled. Find the upstream repo (`git remote -v`, `[project.urls]`)
and search its issues + PRs (open/merged/closed) for `nanobind`, `abi3`,
`pybind11`. Report what you find before porting.

Then size the port locally:

```bash
grep -rnE 'pybind11|PYBIND11_|py::' --include=*.cpp --include=*.h --include=*.hpp .
grep -rn 'PYBIND11_MODULE' .          # entry points
```

nanobind **removed** several pybind11 features. Scan for the blockers *first* —
if you rely on one, that's design work, not a rename:

- **`py::array` / `.def_buffer()`** → must become `nb::ndarray<>` (different API).
- **C++ multiple inheritance** of bound types → unsupported (use Python mixins).
- **Module-local bindings** (`py::module_local`) → removed.
- **Embedding / multiple interpreters** → unsupported (nanobind is bindings-only).
- **Custom metaclasses**, **`options`** docstring class, **`pos_only`**,
  classes with overloaded `operator new`/`delete` → removed.

Full removed-features list and every rename: `reference/api-map.md`. Decide
**big-bang** (small binding surface) vs **gradual** (keep `PYBIND11_MODULE` and
call `nb::register_module(m.ptr())`; note the two frameworks don't recognize each
other's types, so a type crossing the boundary must move in one step).

## 2. Move the build to CMake (nanobind is CMake-native)

nanobind builds through `nanobind_add_module` — there is no setuptools
`Extension` path. If the project still builds with `setup.py` / torch
`cpp_extension`, do the build migration with the **`port-to-scikit-build-core`**
skill first, then come back here. Minimum:

```cmake
find_package(Python 3.10 REQUIRED COMPONENTS Interpreter Development.Module)  # nanobind requires 3.10+
find_package(nanobind CONFIG REQUIRED)      # pip installs nanobind's CMake config
nanobind_add_module(_C ${SOURCES})          # target name must match NB_MODULE(_C, …)
install(TARGETS _C LIBRARY DESTINATION mypkg)
```

Add `"nanobind>=3"` to `build-system.requires` (nanobind 3 requires Python
3.10+ and is what enables the single-abi3-wheel *split mode* below; drop to
`>=2` only if you must support Python 3.8/3.9 without abi3). Real CMake + `pyproject.toml`
from a torch extension: `reference/example.md`.

## 3. Headers and namespace

Replace `#include <pybind11/pybind11.h>` with `#include <nanobind/nanobind.h>`
and `namespace py = pybind11;` with `namespace nb = nanobind;`. Then rename `py::`
→ `nb::` throughout. STL support is **not** implied — see step 5.

## 4. Module entry point and mechanical renames

`PYBIND11_MODULE(name, m)` → `NB_MODULE(name, m)`. Apply the rename table from
`reference/api-map.md`; the ones you hit constantly:

| pybind11 | nanobind |
| --- | --- |
| `.def_readwrite` / `.def_readonly` | `.def_rw` / `.def_ro` |
| `.def_property[_readonly]` | `.def_prop_rw` / `.def_prop_ro` |
| `error_already_set` | `python_error` |
| `reinterpret_borrow<T>` / `reinterpret_steal<T>` | `borrow<T>` / `steal<T>` |
| `register_exception<T>` | `nb::exception<T>` |
| `PYBIND11_OVERRIDE_*` | `NB_OVERRIDE_*` (drop the base-type/return args) |

## 5. STL casters are opt-in headers

pybind11 pulled in `std::string`/`std::vector`/etc. casters via the main header.
nanobind does not — include exactly what you use, or you get cryptic template
errors:

```cpp
#include <nanobind/stl/string.h>       // std::string
#include <nanobind/stl/vector.h>       // std::vector
#include <nanobind/stl/pair.h>         // std::pair
#include <nanobind/stl/shared_ptr.h>   // std::shared_ptr (holders removed, step 6)
#include <nanobind/stl/function.h>     // std::function callbacks
#include <nanobind/stl/unordered_map.h>
```

## 6. Classes: drop holder types

nanobind co-locates instance data in the `PyObject`, so **holders are gone**.
`py::class_<T, std::shared_ptr<T>>` → `nb::class_<T>`; keep passing
`std::shared_ptr<T>` across functions but include `<nanobind/stl/shared_ptr.h>`.
`py::nodelete` → `nb::never_destruct`. `enable_shared_from_this`: pass such
objects as `std::shared_ptr<T>` (not raw `T*`), or `shared_from_this()` may fail.

## 7. Constructors and implicit conversions

Factory lambdas that `return` an instance become **placement-new** on `__init__`:

```cpp
nb::class_<MyType>(m, "MyType")
    .def("__init__", [](MyType *t, int x) { new (t) MyType(x); });
```

Implicit conversion moves into the constructor:
`.def(nb::init_implicit<OtherType>())` (replaces `py::init<>()` +
`py::implicitly_convertible<>`).

## 8. `None` no longer passes by default

nanobind rejects `None` arguments unless you opt in: `"arg"_a.none()`, or a
default `"arg"_a = nb::none()`. **Gotcha:** `.none()` works for bindings and
wrappers but *not* through type casters.

## 9. Trampolines and custom type casters (only if you have them)

- **Trampolines:** add `NB_TRAMPOLINE(Base, N)` to the class; `NB_OVERRIDE_*`
  drops the base-type and return-value args that `PYBIND11_OVERRIDE_*` required.
- **Custom casters:** `load()` → `from_python(handle, uint32_t flags,
  cleanup_list*)` returning `bool` (call `PyErr_Clear()` on failure); `cast()` →
  `from_cpp(value, rv_policy, cleanup_list*)` returning `handle` (leave the error
  *set* on failure). Both must be `noexcept` — casters may not throw C++
  exceptions. Start from nanobind's `std::pair` caster.

## 10. Arrays: `py::array` / buffer protocol → `nb::ndarray`

If step 1 found `py::array` or `.def_buffer()`, rewrite them with
`nb::ndarray<>` (zero-copy CPU/GPU exchange via DLPack). The API is not
compatible with pybind11's — treat this as a rewrite, not a rename.

## 11. Optional: one abi3 wheel

nanobind's stable-ABI mode gives a single wheel for Python ≥3.12:

```cmake
nanobind_add_module(_C STABLE_ABI NB_STATIC ${SOURCES})   # → .abi3.so on ≥3.12
```

```toml
[tool.scikit-build]
wheel.py-api = "cp312"      # emit cp312-abi3; per-version wheels below 3.12
```

Disable abi3 on free-threaded builds **before CPython 3.15** (pip refuses abi3
there). Introduced in Python 3.15, [PEP 803](https://peps.python.org/pep-0803/)
**abi3t** has a set of compatible interpreters that is a *superset* of abi3's — a
`.abi3t.so` loads on **both** GIL-enabled and free-threaded 3.15+ — so nanobind's
split mode plus the combined **`abi3.abi3t`** tag ships one wheel for regular *and*
free-threaded Python ≥3.15. Gate CI with `abi3audit`. This is the same abi3 path
as `port-to-scikit-build-core` step 9 and `port-to-torch-stable-abi` step 17 — the
three skills meet here.

## 12. Verify

1. Build clean; watch for missing `nanobind/stl/*.h` includes (template errors).
2. `import mypkg`; run the full test suite — pay attention to `None` arguments,
   shared-ownership objects, and any array/buffer paths.
3. Compare binding compile time and the built `.so` size against the pybind11
   baseline (the main reason to migrate).
4. If abi3: build on one Python version, `import` on another, run `abi3audit` on
   the wheel.

**Definition of done:** the extension builds and imports through nanobind, the
test suite passes, no pybind11 headers remain (`grep -rn pybind11 .` is clean, or
only the deliberate gradual-port bridge), and — if targeted — one abi3 wheel
loads across Python versions.
