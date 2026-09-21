# pybind11 → nanobind API map

The complete rename table and the removed-feature list, from the upstream
[porting guide](https://nanobind.readthedocs.io/en/latest/porting.html). Cite
this from `SKILL.md` steps; do not inline it into the workflow.

## Renames (mechanical)

| pybind11 | nanobind |
| --- | --- |
| `namespace py = pybind11;` | `namespace nb = nanobind;` |
| `#include <pybind11/pybind11.h>` | `#include <nanobind/nanobind.h>` |
| `PYBIND11_MODULE(name, m)` | `NB_MODULE(name, m)` |
| `PYBIND11_OVERRIDE_*(...)` | `NB_OVERRIDE_*(...)` — drop the base-type + return-type args |
| `error_already_set` | `python_error` |
| `type::of<T>()` | `type<T>()` |
| `py::type` | `nb::type_object` |
| `reinterpret_borrow<T>(x)` | `borrow<T>(x)` |
| `reinterpret_steal<T>(x)` | `steal<T>(x)` |
| `.def_readwrite(...)` | `.def_rw(...)` |
| `.def_readonly(...)` | `.def_ro(...)` |
| `.def_property(...)` | `.def_prop_rw(...)` |
| `.def_property_readonly(...)` | `.def_prop_ro(...)` |
| `.def_readwrite_static(...)` | `.def_rw_static(...)` |
| `.def_readonly_static(...)` | `.def_ro_static(...)` |
| `.def_property_static(...)` | `.def_prop_rw_static(...)` |
| `.def_property_readonly_static(...)` | `.def_prop_ro_static(...)` |
| `register_exception<T>(...)` | `nb::exception<T>(...)` |
| `py::init<Other>()` + `py::implicitly_convertible<Other,T>()` | `nb::init_implicit<Other>()` |

## STL caster headers (opt-in — include what you use)

pybind11's main header dragged these in; nanobind requires an explicit include
per type, or you get long template errors at the binding call.

| Type | Header |
| --- | --- |
| `std::string`, `std::string_view` | `<nanobind/stl/string.h>` |
| `std::vector` | `<nanobind/stl/vector.h>` |
| `std::pair` / `std::tuple` | `<nanobind/stl/pair.h>` / `<nanobind/stl/tuple.h>` |
| `std::map` / `std::unordered_map` | `<nanobind/stl/map.h>` / `<nanobind/stl/unordered_map.h>` |
| `std::optional` / `std::variant` | `<nanobind/stl/optional.h>` / `<nanobind/stl/variant.h>` |
| `std::function` | `<nanobind/stl/function.h>` |
| `std::shared_ptr` / `std::unique_ptr` | `<nanobind/stl/shared_ptr.h>` / `<nanobind/stl/unique_ptr.h>` |
| iterators (`nb::make_iterator`) | `<nanobind/make_iterator.h>` |

## Semantic differences (not just renames)

- **Holders removed.** `py::class_<T, std::shared_ptr<T>>` → `nb::class_<T>`.
  Instance data lives in the `PyObject`. Still pass `std::shared_ptr<T>` across
  functions (with `<nanobind/stl/shared_ptr.h>`). `py::nodelete` →
  `nb::never_destruct`.
- **`enable_shared_from_this`.** A Python-constructed object often has no
  associated `shared_ptr` until passed to a C++ function taking one. A function
  taking raw `T*` that calls `shared_from_this()` may fail — take
  `std::shared_ptr<T>` instead.
- **`std::unique_ptr` arguments** have limitations; prefer
  `std::unique_ptr<T, nb::deleter<T>>`.
- **Custom constructors** use placement-new on `__init__`:
  `.def("__init__", [](T *self, ...) { new (self) T(...); })`. For a factory:
  `new (self) T(T::create());`.
- **`None` arguments rejected by default.** Opt in with `"arg"_a.none()` or a
  `"arg"_a = nb::none()` default. Works for bindings/wrappers, **not** type
  casters.
- **Trampolines** need `NB_TRAMPOLINE(Base, N)` (N = number of overridable
  methods); `NB_OVERRIDE_*` no longer takes the base type / return type.
- **Custom type casters:** `load()` → `from_python(handle, uint32_t flags,
  cleanup_list*)` (return `bool`; `PyErr_Clear()` on failure); `cast()` →
  `from_cpp(value, rv_policy, cleanup_list*)` (return `handle`; leave the error
  *set* on failure). Both **must be `noexcept`**. `cleanup` may be `nullptr`.
- **Iterators** (`nb::make_iterator` / `make_key_iterator` /
  `make_value_iterator`) now take a Python scope + name as the first two args and
  need `<nanobind/make_iterator.h>`.

## Removed features (design around them — scan for these first)

- **`py::array` and buffer protocol `.def_buffer()`** → `nb::ndarray<>` (DLPack;
  API not compatible — a rewrite).
- **C++ multiple inheritance** of bound classes → combine one nanobind base with
  Python mixins.
- **Module-local bindings** (`py::module_local`) for types and exceptions.
- **Embedding / multiple interpreters** — nanobind is bindings-only.
- **Custom metaclasses.**
- **`pos_only`** annotation — use unnamed / keyword-only arguments instead.
- **Classes with overloaded or deleted `operator new`/`operator delete`.**
- **`options`** class for docstring customization.
- **Evaluating Python files** (may return later).
- **Compiler workarounds** — nanobind requires a modern C++17 toolchain and
  Python ≥3.10.

## Gradual (side-by-side) porting

Both frameworks can live in one extension during migration. Keep
`PYBIND11_MODULE` as the entry point and call `nb::register_module(m.ptr())`
(throws on failure) before any other nanobind API use. The frameworks do **not**
recognize each other's bound types — a type crossing the pybind11/nanobind
boundary must be migrated in a single step.
