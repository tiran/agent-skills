# Reference ports and the escape hatch

## Reference ports (all verified against source)

Copy from the one closest to your case — a spread of easy/hard and setuptools/CMake.

| Project | Floor | Build | Ops style | Module model | abi3? | Notable |
| --- | --- | --- | --- | --- | --- | --- |
| causal-conv1d [#123](https://github.com/Dao-AILab/causal-conv1d/pull/123) | 2.11 | setuptools | `STABLE_TORCH_LIBRARY` free fns | real `_C` module | **yes** | full mechanical recipe; `.add_`/`.item()` workarounds |
| kvcached (#497, [#505](https://github.com/ovg-project/kvcached/pull/505)) | 2.10 | setuptools | stable ops + 2 pybind classes | pybind + stable in one `.so` | blocked by classes | source of the `TORCH_STABLE_ONLY` include trick |
| vLLM [#43209](https://github.com/vllm-project/vllm/pull/43209)/[#43361](https://github.com/vllm-project/vllm/pull/43361)/[#43717](https://github.com/vllm-project/vllm/pull/43717) | — | CMake | `_FRAGMENT`+`_IMPL`, `TORCH_BOX` | `_C_stable_libtorch` lib | — | incremental file-by-file migration; `torch-abi-audit` gate |
| torchaudio | 2.10 | setuptools | `STABLE_TORCH_LIBRARY(_FRAGMENT/_IMPL)` | real module | **yes** | even the helper module is a stable lib; `THO_DISPATCH_V2` |
| torchcodec | 2.11 | scikit-build/CMake | `_FRAGMENT`+`_IMPL` | `load_library` + 1 pybind11 shim | no | handle-in-a-tensor for C++ objects; origin of #1260 |
| torchvision | 2.14 | setuptools | `_FRAGMENT`+`_IMPL` | `load_library` | no | autograd/autocast/fake moved to Python; `torch_call_dispatcher` shims |
| xformers | 2.10 | setuptools | `_FRAGMENT` | `load_library`, no `PyInit_` | Py-agnostic wheel (not `Py_LIMITED_API`) | one shim header; `-DTORCH_STABLE_ONLY` |
| amd-quark | 2.10 | setuptools | `CompositeExplicitAutograd`+`TORCH_BOX` | `load_library` (+JIT fallback) | no | keeps a **legacy pybind fallback** for Torch < 2.10 |

Also see PyTorch's own [`pytorch/extension-cpp`](https://github.com/pytorch/extension-cpp)
(`extension_cpp_stable/`), a minimal `mymuladd` op written both stable and
traditional — a useful side-by-side, though its code can lag the current APIs, so
prefer the real ports above where they differ.

## Escape hatch: ops missing from the stable ABI

Some ATen ops have no `torch::stable::` wrapper yet (e.g. `permute`, `cat`, `flip`,
`sort`, `masked_select`, `new_full` with a Scalar). Redispatch by name — collect
these in one compat header and delete them as upstream lands wrappers (torchvision
`StableABICompat.h`, xformers `pt_stable_utils.h`, torchcodec):

```cpp
std::array<StableIValue, N> stack{ torch::stable::detail::from(arg0), /*…*/ };
TORCH_ERROR_CODE_CHECK(torch_call_dispatcher("aten::permute", "", stack.data(), TORCH_ABI_VERSION));
auto out = torch::stable::detail::to<torch::stable::Tensor>(stack[0]);
```

Scalar args have no header-only type — push them onto the stack as `from(double)`
(or `from(int64_t)`); every stable Scalar-taking op funnels its Scalar through as
`double`.
