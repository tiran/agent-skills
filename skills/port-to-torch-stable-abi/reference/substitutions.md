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

`STD_CUDA_CHECK` / `STD_CUDA_KERNEL_LAUNCH_CHECK` live in
`<torch/csrc/stable/macros.h>` and exist since the **2.10** floor — include the
header (it expects `cuda_runtime.h` in scope) and use them directly; **don't
hand-roll a `STD_TORCH_CHECK`-based replacement** (causal-conv1d did initially,
then switched).

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

**Atomics:** `#include <ATen/cuda/Atomic.cuh>` + `atomicAdd(ptr, v)` →
`#include <torch/headeronly/cuda/Atomic.h>` + `gpuAtomicAdd(ptr, v)`. ATen's
`Atomic.cuh` `#error`s under `TORCH_STABLE_ONLY`; the headeronly one is stable-safe
and covers `Half`/`BFloat16`.

**Floor caveat — `torch/headeronly/cuda/Atomic.h` is Torch ≥ 2.14 only.** It does
not exist at 2.10–2.13, and there's no other stable `gpuAtomicAdd` there (ATen's
`Atomic.cuh` is off-limits). If your floor is below 2.14, either raise it or
**vendor upstream's header** behind `__has_include` — ≥2.14 uses the maintained
copy, older Torch the vendored one:

```cpp
#if __has_include(<torch/headeronly/cuda/Atomic.h>)
#include <torch/headeronly/cuda/Atomic.h>          // Torch >= 2.14
#else
#include "vendored/headeronly_cuda_atomic.h"
#endif
```

Copy the header **verbatim** (BSD-3 attribution + pinned version) so no new device
logic is introduced — the `Half`/`BFloat16` CAS loops are exactly what Torch ships.
Trim to just the `gpuAtomicAdd` (Add) family if that's all you use; dropping the
Mul/Max/Min atomics also drops their `torch/headeronly/util/NumericUtils.h`
dependency, another header absent at 2.10. Delete the vendored file and the
`__has_include` block once the floor reaches 2.14. `__has_include` is the right
switch because a stable TU **cannot** read `TORCH_VERSION_MAJOR/MINOR` (step 4:
`version.h` `#error`s under the target).

## 10. Dispatch macros

ATen dispatch macros pull in unstable headers. Replace with:

- `AT_DISPATCH_FLOATING_TYPES(...)` → `THO_DISPATCH_V2(scalar_type, name, lambda,
  AT_FLOATING_TYPES)` (`<torch/headeronly/core/Dispatch_v2.h>`), used by
  torchaudio/torchvision.
- `_AND_HALF`/`_AND2` variants → append the extra `ScalarType`s and wrap the group
  macro in `AT_EXPAND(...)`, e.g. `AT_DISPATCH_FLOATING_TYPES_AND_HALF` →
  `THO_DISPATCH_V2(scalar_type, name, lambda, AT_EXPAND(AT_FLOATING_TYPES),
  torch::headeronly::ScalarType::Half)`.
- For custom sets, hand-write pure-C++ `if/else`/`switch` dispatch macros (vLLM's
  `VLLM_STABLE_DISPATCH_*` — no ATen dependency).

**Trap — `THO_DISPATCH_V2` mangles raw CUDA launch-config commas.** It re-scans its
body argument through several macro-expansion layers. Commas inside `(...)` are
protected, but the commas in a **kernel launch config**
`kernel<<<grid, block, 0, stream>>>(...)` are **not** — the preprocessor splits the
launch into bogus macro arguments and the body fails to compile under nvcc/hipcc.
`AT_WRAP` does **not** fix it. This bites the *common* case of dispatching a
standard `AT_FLOATING_TYPES` set around a raw launch, not just custom sets. Two ways
out:

- **Move the launch out of the dispatch body** into a helper templated on
  `scalar_t`, and call that helper from inside `THO_DISPATCH_V2` (a parenthesized
  call, so its commas are safe); or
- **Use a single-expansion dispatch macro** that keeps the body in a variadic
  (`__VA_ARGS__`) so launch-config commas survive — a hand-rolled `switch` over
  `ScalarType` with `using scalar_t = ScalarTypeToCPPTypeT<...>` in each `case`
  (the vLLM `VLLM_STABLE_DISPATCH_*` shape; use it for **launch sites**, keep
  `THO_DISPATCH_V2` for CPU/no-launch bodies):

```cpp
#define X_DISPATCH_CASE(ENUM, ...)                                    \
  case torch::headeronly::ScalarType::ENUM: {                         \
    using scalar_t = torch::headeronly::impl::ScalarTypeToCPPTypeT<   \
        torch::headeronly::ScalarType::ENUM>;                         \
    __VA_ARGS__; break;                                               \
  }
#define X_DISPATCH_FLOATING_TYPES(TYPE, NAME, ...)                    \
  [&] { switch (TYPE) {                                               \
    X_DISPATCH_CASE(Float, __VA_ARGS__)                               \
    X_DISPATCH_CASE(Double, __VA_ARGS__)                              \
    default: STD_TORCH_CHECK(false, NAME, " unsupported dtype");      \
  } }()
```

Factor these into your shared helper header (DRY) — every `.cu` launch site uses
them.
