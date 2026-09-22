# Substitution tables (steps 5–10)

Look these up while doing the mechanical rewrite. Traps are called out in
`SKILL.md`; this file is the full lookup.

## 5. Swap the includes

| Remove (unstable) | Add (stable) |
| --- | --- |
| `<torch/extension.h>`, `<torch/all.h>`, `<torch/python.h>` | `<torch/csrc/stable/library.h>`, `<torch/csrc/stable/tensor.h>` |
| `<ATen/*.h>`, `<ATen/cuda/CUDAContext.h>` | `<torch/csrc/stable/ops.h>` (stable tensor ops) |
| `<c10/cuda/CUDAGuard.h>`, `<c10/core/DeviceGuard.h>` | `<torch/csrc/stable/accelerator.h>` |
| `<c10/util/Half.h>`, `<c10/util/BFloat16.h>` | `<torch/headeronly/util/Half.h>`, `<torch/headeronly/util/BFloat16.h>` |
| `<c10/core/ScalarType.h>` | `<torch/headeronly/core/ScalarType.h>` |
| `<c10/cuda/CUDAException.h>` | `<torch/csrc/inductor/aoti_torch/c/shim.h>` (stream shim) |

For an abi3 module also `#include <Python.h>` **first**, before any torch header.

## 6. Type substitutions

| Unstable | Stable |
| --- | --- |
| `at::Tensor`, `torch::Tensor` (params/returns/locals) | `torch::stable::Tensor` |
| `c10::optional<at::Tensor>` | `std::optional<torch::stable::Tensor>` |
| `at::ScalarType::X`, `c10::ScalarType::X`, `torch::kInt32`/`kFloat32`/… | `torch::headeronly::ScalarType::X` (`kInt8`→`Char`, `kInt64`→`Long`) |
| `at::Half`, `at::BFloat16`, `c10::util::Half` (incl. `.cu` template params) | `torch::headeronly::Half`, `torch::headeronly::BFloat16` |
| `at::Device`, `torch::Device` | `torch::stable::Device` |
| `at::IntArrayRef` | `torch::headeronly::IntHeaderOnlyArrayRef` |

## 7. Checks and error macros

| Unstable | Stable |
| --- | --- |
| `TORCH_CHECK`, `TORCH_CHECK_EQ(a,b)`, `TORCH_CHECK_GE(a,b)` | `STD_TORCH_CHECK(cond, msg)` — rewrite `_EQ`/`_GE` as `STD_TORCH_CHECK(a == b)` etc. |
| `AT_ERROR(...)` | `STD_TORCH_CHECK(false, ...)` (drop `toString()`; stream the `ScalarType` directly) |
| `C10_CUDA_CHECK` | `STD_CUDA_CHECK` |
| `C10_CUDA_KERNEL_LAUNCH_CHECK` | `STD_CUDA_KERNEL_LAUNCH_CHECK` |

## 8. Tensor methods → stable free functions

Most `tensor.method()` calls become `torch::stable::fn(tensor, …)`:

| Unstable | Stable |
| --- | --- |
| `t.contiguous()` | `torch::stable::contiguous(t)` |
| `t.view({...})` / `t.transpose(a,b)` / `t.flatten(a,b)` / `t.sum(dims)` | `torch::stable::view/transpose/flatten/sum(t, …)` |
| `at::zeros(...)` / `torch::empty(...)` | `torch::stable::new_zeros(t, …)`, `new_empty`, `empty(sizes, ScalarType, std::nullopt, device)` |
| `t.data_ptr<T>()` | `t.const_data_ptr<T>()` (read) or `t.mutable_data_ptr<T>()` (write) — const-correctness now propagates into kernel params |
| `t.data_ptr()` (void\*, with `reinterpret_cast`) | unchanged |
| `t.dtype()` | `t.scalar_type()` |
| `t.itemsize()` | `t.element_size()` |
| `t.get_device()` | `t.get_device_index()` |
| `x.sizes() == y.sizes()` | `x.sizes().equals(y.sizes())` |
| `t[i][j].item<int64_t>()` | read `const_data_ptr<int64_t>()` + `stride()` arithmetic — `.item()`/element indexing absent (also avoids a per-element GPU→CPU sync) |
| `t.stride(-1)`, `t.size(-1)` | **no negative dims** — use `t.dim()-1` |

If a method has no stable equivalent, use the dispatcher escape hatch in `ports.md`.

## 9. Device and stream

```cpp
// guard
torch::stable::accelerator::DeviceGuard guard(t.get_device_index());

// current CUDA stream — via the AOTI shim (needs -DUSE_CUDA, on CUDA and ROCm)
cudaStream_t stream;
TORCH_ERROR_CODE_CHECK(aoti_torch_get_current_cuda_stream(t.get_device_index(), (void**)&stream));
```

For Torch ≥ 2.13 you may instead use
`torch::stable::accelerator::getCurrentStream(idx).nativeHandle()`; version-gate if
you support both. **Wrap this in one helper header** (`get_current_cuda_stream()`,
`get_device_prop()`) — every surveyed project does.

## 10. Dispatch macros

ATen dispatch macros pull in unstable headers. Replace with:

- `AT_DISPATCH_FLOATING_TYPES(...)` → `THO_DISPATCH_V2(scalar_type, name, lambda,
  AT_FLOATING_TYPES)` (`<torch/headeronly/core/Dispatch_v2.h>`), used by
  torchaudio/torchvision.
- For custom sets, hand-write pure-C++ `if/else`/`switch` dispatch macros (vLLM's
  `VLLM_STABLE_DISPATCH_*` — no ATen dependency).
