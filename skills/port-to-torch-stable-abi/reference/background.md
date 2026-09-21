# The PyTorch stable ABI, for Python developers

Background and rationale for engineers who know Python well but haven't had to
think about C++ ABIs, wheel tags, or Torch internals. The executable steps live in
`../SKILL.md`; this doc explains *why* each step exists. Read it when you need the
reasoning, not the checklist.

The authoritative reference is PyTorch's own
[LibTorch Stable ABI note](https://docs.pytorch.org/docs/stable/notes/libtorch_stable_abi.html)
([source](https://github.com/pytorch/pytorch/blob/main/docs/source/notes/libtorch_stable_abi.md)),
backed by the
[Custom C++ and CUDA Operators](https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html)
tutorial for the dispatcher model. This guide is the friendly on-ramp to those.

## The problem: why your extension wheel is version-locked

If your package has a compiled C++/CUDA part (a `_C.so`), you have probably seen
wheels named like `mypkg-1.0+cu124torch2.4-cp311-...whl`. That single wheel works
*only* with Python 3.11, CUDA 12.4, and PyTorch 2.4. Ship support for 3
Python × 4 Torch × 2 CUDA versions and you are building and hosting 24 wheels,
and every new Torch release adds a column overnight.

The reason is the **ABI** — the Application *Binary* Interface. Source-level
compatibility (an API) is about names and signatures you write in code. An ABI is
the compiled contract: struct layouts, symbol mangling, calling conventions,
vtable order. libtorch's C++ ABI is **not stable** — the compiled layout of
`at::Tensor` and friends can change between minor releases. So a `.so` compiled
against Torch 2.4's headers links to symbols that may not exist, or may have a
different layout, in Torch 2.5. The wheel tag encodes that lock so pip doesn't
install a wheel that would crash on import.

## Two different ABIs (the part that trips people up)

"Stable ABI" is overloaded. There are **two** independent binary contracts your
extension depends on:

1. **The libtorch C++ ABI** — the contract with PyTorch's compiled library.
   Stabilizing this is what "the PyTorch stable ABI" (a.k.a. `torch::stable`)
   means, and it is what this document is about. Payoff: **one wheel across Torch
   versions**.
2. **The CPython ABI** — the contract with the Python interpreter itself.
   CPython offers a stable subset called the **Limited API** / **abi3**; using it
   gives **one wheel across Python versions** (`cp310-abi3` loads on 3.10, 3.11,
   3.12, …). This is a *separate* effort, discussed at the end.

They are orthogonal. You can do either, both, or neither. torchvision and
xformers stabilized the Torch ABI but still ship per-Python wheels; torchaudio
did both.

## What the PyTorch stable ABI actually is

Concretely, porting means three linked changes:

- **Register ops through the dispatcher, not through the interpreter.** Instead of
  a pybind11 module that exposes C++ functions directly to Python, you declare
  *operators* with `STABLE_TORCH_LIBRARY` and reach them as
  `torch.ops.myns.my_op`. PyTorch's dispatcher is a stable boundary: your op is
  called through a fixed calling convention (`TORCH_BOX` wraps your function to
  match it), so the layout of Torch's internal types never crosses into your code.
- **Use `torch::stable::` and `torch::headeronly::` types**, never `at::` / `c10::`.
  `torch::stable::Tensor` is a thin handle whose ABI is guaranteed; the
  `headeronly` types (`ScalarType`, `Half`, `BFloat16`) are pure header code with
  no compiled dependency. Where you need an ATen operation, you call it *by name*
  through the dispatcher rather than linking its C++ symbol.
- **Pin a floor with `-DTORCH_TARGET_VERSION`.** This one compile define says
  "target the stable ABI as it existed at, say, Torch 2.10." The wheel then loads
  on 2.10 and everything newer. It also turns on a guard (`TORCH_STABLE_ONLY`)
  that makes any accidental `at::`/`c10::` use a **compile error** — a mechanical
  safety net so you cannot silently reintroduce the version lock.

The result: build once against your chosen floor, and the wheel keeps working as
users upgrade Torch. That is the whole point.

## The three axes of wheel compatibility

Keep these separate in your head — each is collapsed (or not) by a different tool:

| Axis | What varies | Collapsed by |
| --- | --- | --- |
| **Torch version** | libtorch C++ ABI | the PyTorch stable ABI (`TORCH_TARGET_VERSION`) |
| **Python version** | CPython ABI | Python abi3 (`Py_LIMITED_API`) |
| **CUDA / ROCm** | GPU runtime + device code | *nothing* — see below |

The stable ABI does **not** free you from the CUDA axis. That surprises people,
so the next section covers it in detail.

## CUDA and ROCm details

The GPU toolkit is governed by NVIDIA/AMD compatibility rules, **not** by
PyTorch. Neither the Torch stable ABI nor abi3 changes this axis — Torch itself
still ships separate `cu124` / `cu128` / `cu130` wheels for exactly this reason.
What the stable ABI *does* give you is a clean, CUDA-agnostic way to talk to the
GPU (details at the end of this section).

To reason about it, separate three things a GPU extension can depend on:

- **The driver API** (`libcuda`, `cuMem*` calls) — the lowest, most stable layer.
- **The CUDA runtime** (`libcudart`, `<<<>>>` kernel launches) — carries a
  versioned soname (`libcudart.so.12`).
- **Device code** — the compiled kernels themselves, as SASS (`cubin`, tied to a
  specific GPU architecture) and/or PTX (a portable intermediate the driver
  JIT-compiles).

### Forward compatibility: minor vs major

- **CUDA minor bumps (e.g. 13.0 → 13.2): free.** Since CUDA 11, NVIDIA guarantees
  *minor-version compatibility* — an application built against 13.0 runs on any
  13.x runtime and driver. Build against the *lowest* minor in a major to
  maximize coverage; no rebuild, no extra wheel.
- **CUDA major bumps (e.g. 12 → 13): a rebuild.** The runtime soname changes
  (`libcudart.so.12` → `.13`) and device-code formats can bump. Convention —
  which Torch follows — is **one wheel per CUDA major**. The driver is
  *backward* compatible (a binary built against the CUDA 12 driver headers runs on
  a newer 13.x driver), so the code often compiles unchanged; you rebuild mainly
  to match the runtime the user's Torch links.
- **Kernel-free extensions barely feel this.** A project that only uses the driver
  API (`cuMem*` VMM calls, linked with `-lcuda`, no `.cu` kernels) ships no device
  code and no `cudart` dependency, so it is very nearly CUDA-major-agnostic.
  Kernel-heavy projects (xformers, vLLM) carry both `cudart` and device code and
  pay the full per-CUDA-major cost.

### Supporting a new GPU (device architecture)

This is a **fourth**, kernel-only axis, independent of the toolkit version.
Compiled kernels target a compute capability (`sm_80` Ampere, `sm_90` Hopper,
`sm_100`/`sm_120` Blackwell):

- **SASS (`cubin`) is forward-compatible only within a compute-capability major.**
  An `sm_80` cubin runs on `sm_86`/`sm_89`, but **not** on `sm_90`. A new GPU
  generation needs either a freshly compiled cubin for its arch, or a **PTX
  fallback** — PTX is forward-portable, and the driver JIT-compiles it to the new
  architecture at first load. Shipping PTX is how a wheel built today can run on a
  GPU released tomorrow, at the cost of a one-time JIT.
- **One binary covers many GPUs — a fatbinary.** You do *not* ship one file per
  arch. The toolchain packs several archs' SASS plus a PTX tail into a single
  **fatbinary** embedded in the one `.so`; at load the driver picks the matching
  cubin and JITs the PTX only if none fits. ROCm does the same via a **bundled
  ("fat") code object** carrying multiple `gfx*` targets. So multi-arch support is
  a build-list choice, not extra artifacts.
- So "add support for Blackwell" means adding an `sm_100`/`sm_120` target (or
  ensuring a PTX fallback) to that list and rebuilding — it has **nothing to do**
  with the Torch ABI. Kernel-free projects support new GPUs automatically.

### ROCm / HIP

The Torch stable ABI works the same on AMD: the `STABLE_TORCH_LIBRARY` macros,
`torch::stable::Tensor`, `STD_TORCH_CHECK`, and `TORCH_TARGET_VERSION` are all
device-agnostic. The differences are in the build:

- Link `amdhip64` instead of `cuda`; the ROCm analogue of the CUDA-major axis is
  the ROCm version.
- Two different `USE_*` defines do two different jobs. `-DUSE_ROCM=1`
  (with `-D__HIP_PLATFORM_AMD__=1`) is the "I'm building against ROCm torch"
  switch that makes the HIP-aware headers compile — `CUDAExtension` adds it for
  you, `CppExtension` does not. `-DUSE_CUDA` is *separate*: it's what still gates
  the current-stream shim, because Torch's ROCm build masquerades HIP as CUDA and
  keeps the `..._cuda_stream` name. So a kernel that needs the stream defines
  **both** on ROCm.
- Torch's build **hipifies** source (rewrites CUDA calls to HIP). For code that is
  already HIP-aware, use `CppExtension` rather than `CUDAExtension` to skip Torch's
  hipify pass, which otherwise rewrites your headers and can break them. amd-quark
  hit a related trap: hipify scans every header on the include path and generates
  duplicate `_hip.h` copies of third-party headers, so it routes those as raw `-I`
  flags to keep them out of the scan.
- GPU-arch selection is the same idea with `gfx*` targets instead of `sm_*`.

### What the stable ABI does buy you on the GPU axis

One concrete win: you get the current CUDA/HIP **stream as an opaque handle**
through the AOTI shim (`aoti_torch_get_current_cuda_stream`, compiled with
`-DUSE_CUDA` — on CUDA *and* ROCm; see above) and device guards through
`torch::stable::accelerator::DeviceGuard`. These don't hard-code Torch's internal
CUDA types, so your stream/device plumbing stops being a source of ABI breakage —
even though you still compile and ship kernels per CUDA major.

## Porting guide (for humans)

The bulk of a port is mechanical and safe; the judgement lives in a few
decisions. What to expect:

1. **Inventory first.** Grep for `pybind11`, `py::class_`, `at::`, `c10::`,
   `TORCH_CHECK`, `AT_DISPATCH`, and your `.cu` files. This tells you the size and
   whether you have the one genuinely hard case (below).
2. **Pick the Torch floor.** Default to **2.10**; go higher only if you need a
   newer stable API (e.g. `from_blob` with a deleter needs 2.11). Lower floor =
   more users covered.
3. **Flip the build flags** — add `-DTORCH_TARGET_VERSION=<hex>` and
   `-DTORCH_STABLE_ONLY` to both the C++ and CUDA compiler args, from one shared
   list so they can't drift.
4. **Do the mechanical rewrite.** This is most of the diff and it is
   find-and-replace in spirit: `at::Tensor` → `torch::stable::Tensor`,
   `TORCH_CHECK` → `STD_TORCH_CHECK`, `tensor.contiguous()` →
   `torch::stable::contiguous(tensor)`, `at::ScalarType::Half` →
   `torch::headeronly::ScalarType::Half`, and swap the includes. The full
   substitution tables are in `substitutions.md`. Rather than do this by hand,
   consider [`pytorch-stable-abi-transform`](https://github.com/TorchedHat/pytorch-stable-abi-transform),
   a deterministic Clang AST rewriter that applies these edits (and audits,
   plans, and compile-verifies the result) and flags what it can't rewrite; it
   also ships its own Claude Code skill and a GitHub Action for CI.
5. **Move op registration to `STABLE_TORCH_LIBRARY`** and box the implementations
   with `TORCH_BOX(&fn)`.
6. **Relocate what C++ can't express to Python** — autograd, autocast, and the
   fake/meta kernels that `torch.compile` needs all move to small
   `torch.library.register_*` calls. This is normal and expected.
7. **Verify with a symbol audit**, not by eye. Either the `torch-abi-audit`
   wheel scanner or a grep of the built `.so` for leftover `at::`/`c10::` symbols.
   Then build on your floor Torch *and* a newer Torch and import both — that is the
   single-wheel claim, and only a real build proves it.

### The one hard case: C++ classes

The mechanical path assumes your extension exposes **functions**. The stable ABI
has **no equivalent of `pybind11::class_` / `torch::class_`** — there is no way to
export a stateful C++ class across the stable boundary directly. If your inventory
found exported classes, you have three options, in rough order of preference:

- **Opaque handle-in-a-tensor** — heap-allocate the object, hide its pointer
  inside a 1-element tensor with a deleter, and expose methods as ops that take
  the handle. All-stable (torchcodec does this for its decoders).
- **Keep a small pybind11 island** in the same `.so` for just the classes, with
  the tensor ops on the stable path (kvcached keeps `PageAllocator` this way). Note
  this *caps* your Python-abi3 options later.
- **nanobind** — a pybind11-like library that *is* abi3-capable, at the cost of a
  Python 3.12 floor.

A useful pitfall to know (**Torch < 2.13 only**): on those versions
`-DTORCH_STABLE_ONLY` makes Torch's own bundled pybind11/fmt headers fail to
compile (they live under `torch/` and trip the guard). If you keep any pybind, you
wrap just those includes in a `push_macro`/`#undef`/`pop_macro` block — a small,
well-documented workaround (kvcached #505, torchcodec #1260). Torch **≥ 2.13
allow-lists pybind/fmt** (pytorch/pytorch#174372), so above that floor the guard
no longer fires and the workaround is unnecessary.

## Should you also do Python abi3?

Once the Torch port is done, abi3 is often a small add-on — *if* you have no
pybind classes left. The steps: set `py_limited_api=True` on the extension, derive
the wheel tag from `torch.utils.cpp_extension.min_supported_cpython` (e.g.
`cp310-abi3`), and either hand-write a tiny multi-phase module `PyInit` or ship
the extension as a `torch.ops.load_library` library (which sidesteps the CPython
ABI entirely — xformers ships one wheel across Python 3.9–3.13 this way). One
catch: disable abi3 on free-threaded (GIL-less) builds **before CPython 3.15**,
since pip refuses abi3 wheels there. Introduced in Python 3.15,
[PEP 803](https://peps.python.org/pep-0803/) **abi3t** has a set of compatible
interpreters that is a *superset* of abi3's — a `.abi3t.so` loads on **both**
GIL-enabled and free-threaded 3.15+ — so the combined **`abi3.abi3t`** wheel tag
serves regular *and* free-threaded Python ≥3.15 from a single wheel, once Torch's
build tooling targets it. (An `abi3t`-*only* tag would be free-threaded-only.)

The blocker, if there is one, is almost always pybind `py::class_` — it is
fundamentally incompatible with the Limited API. If you kept a pybind island for
classes, abi3 waits until those move to the handle pattern or nanobind.

## Common pitfalls

- **`.item()` and element indexing are gone.** `tensor[i].item<int64_t>()` has no
  stable form; read `const_data_ptr<int64_t>()` and index with strides (also
  faster — it avoids a per-element GPU→CPU sync).
- **Negative dims aren't supported.** `stride(-1)` → `stride(t.dim()-1)`.
- **`data_ptr<T>()` splits** into `const_data_ptr<T>()` (reads) and
  `mutable_data_ptr<T>()` (writes); getting const-ness right ripples into kernel
  signatures.
- **Not every ATen op has a stable wrapper yet** (`permute`, `cat`, `sort`, …).
  Call them by name through `torch_call_dispatcher` and keep the shims in one
  header so they're easy to delete as upstream fills the gaps.
- **You can't read `TORCH_VERSION_MAJOR/MINOR`** in stable code — `<torch/version.h>`
  errors out when `TORCH_TARGET_VERSION` is set. Treat "target defined" as "≥ floor."
- **CUDA is still its own axis.** Stabilizing the Torch ABI does not give you one
  wheel across CUDA majors — see the CUDA/ROCm section.

## Reference ports

Real, source-verified examples to copy from live in `ports.md` (a spread of
easy/hard and setuptools/CMake, with the `abi3?` status of each).
