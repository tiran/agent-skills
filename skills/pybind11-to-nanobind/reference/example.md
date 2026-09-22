# Worked example: kvcached (pybind11 → nanobind, abi3, torch stable ABI)

A real migration of a PyTorch C++ extension from pybind11 to nanobind, done
together with a scikit-build-core build and the Torch stable ABI. Branch
(experimental, unmerged): <https://github.com/tiran/kvcached/tree/nanobind-abi3>.

It exercises most of the porting steps at once, so it is a good end-to-end
reference — but note it is *also* doing the build + Torch-ABI ports, which a
pure pybind11→nanobind change would not.

## What changed, mapped to the skill steps

- **Build (step 2).** `setup.py` (193 lines, torch `cpp_extension`) was deleted
  and replaced with `CMakeLists.txt` + `pyproject.toml`. The module target is
  built with `nanobind_add_module`, installed into the package dir.
- **Header/namespace (steps 3–4).** `#include <nanobind/nanobind.h>`,
  `namespace nb = nanobind;`, entry point `NB_MODULE(_C, m)` — the target name
  `_C` matches the `nanobind_add_module` target.
- **STL casters (step 5).** Explicit opt-in includes, exactly what the bindings
  use:
  ```cpp
  #include <nanobind/stl/function.h>
  #include <nanobind/stl/pair.h>
  #include <nanobind/stl/shared_ptr.h>
  #include <nanobind/stl/string.h>
  #include <nanobind/stl/unordered_map.h>
  #include <nanobind/stl/vector.h>
  ```
- **Classes / holders (step 6).** `nb::class_<PageAllocator>` and
  `nb::class_<InternalPage>` — no `shared_ptr` holder; functions still take
  `std::shared_ptr<PageAllocator>` (covered by `stl/shared_ptr.h`). Read-only
  fields use `.def_ro("page_id", &InternalPage::page_id)`.
- **Args / defaults (step 8-adjacent).** `nb::arg("group_id") = 0`,
  `nb::arg("ipc_name") = ""`, etc. — direct `py::arg` → `nb::arg`.
- **Exceptions.** `nb::exception<StateConsistencyError>(m, "StateConsistencyError",
  base)` (pybind11 `register_exception`), and Python errors caught as
  `nb::python_error` with `error.matches(errors.attr("StateConsistencyError"))`
  (pybind11 `error_already_set` + `.matches`).
- **GIL.** `nb::gil_scoped_release` / `nb::gil_scoped_acquire` (drop-in rename of
  the pybind11 spellings) around blocking allocator calls and Python callbacks.
- **Python objects.** `nb::dict`, `nb::int_`, `nb::module_::import_(...)` replace
  the `py::` equivalents.

## The split that made this one special

Only some bindings are nanobind. The six ops that touch `torch::stable::Tensor`
are registered on the **Torch dispatcher** (`STABLE_TORCH_LIBRARY` /
`STABLE_TORCH_LIBRARY_IMPL`, reached as `torch.ops.kvcached.*`), because the
stable Tensor type crosses that boundary cleanly. The torch-free bindings —
`PageAllocator`, `InternalPage`, and the transactional map/unmap ops (int/str/
bool args) — stay on the nanobind `NB_MODULE`. If your extension is not on the
Torch stable ABI, this split does not apply: everything stays on the nanobind
module.

## abi3 (step 11)

```cmake
nanobind_add_module(_C STABLE_ABI NB_STATIC ${SOURCES})   # .abi3.so on ≥3.12
install(TARGETS _C LIBRARY DESTINATION kvcached)
```

```toml
[build-system]
requires = ["scikit-build-core>=0.10", "nanobind>=2.2.0", "torch>=2.10"]

[tool.scikit-build]
wheel.py-api = "cp312"          # one cp312-abi3 wheel for Python ≥3.12

[tool.cibuildwheel]
test-requires = ["abi3audit"]   # audit the abi3 wheel in CI
```

Full annotated `pyproject.toml` / `CMakeLists.txt` for this branch also appear in
the `port-to-scikit-build-core` skill's `reference/examples.md` (Example B) —
that skill owns the build details; this one owns the binding conversion.
