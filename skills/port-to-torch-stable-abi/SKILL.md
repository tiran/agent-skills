---
name: port-to-torch-stable-abi
description: >-
  Port a Python package's compiled C++/CUDA/ROCm extension to the PyTorch stable
  ABI (torch::stable, STABLE_TORCH_LIBRARY, TORCH_TARGET_VERSION) so one wheel
  works across Torch versions, then assess Python abi3 (Py_LIMITED_API). Use when
  a project ships a Torch extension that is version-locked to a single Torch
  release, or when asked to adopt the stable ABI / torch::stable / stop rebuilding
  per Torch version.
---

# Port a package to the PyTorch stable ABI

**Status: Beta** — every rule is drawn from real, source-verified ports, but this
packaged workflow has been exercised on only a few projects. Follow it, but have a
human review the resulting diff and build.

Port a compiled Torch extension from the unstable libtorch ABI to the **stable
ABI**, then **assess Python abi3**. Work in the order below. Every rule comes from
real ports (`reference/ports.md`); prefer these concrete patterns over improvising.

**Why both.** Stable ABI + abi3 is the best outcome: one wheel across *Torch*
versions (stable ABI) **and** across *Python* versions (abi3). The only axis left
is CUDA / device code — a new build is needed only for a new CUDA version, not for
each Torch or Python release. That remaining GPU axis is what PyPI wheel variants
([PEP 825](https://peps.python.org/pep-0825/), provisional) are designed to
resolve at install time. So do the stable-ABI port *and* the abi3 assessment — the
two together are the payoff, not either alone.

**Bundled references — open each at the step that cites it, not up front:**

- `reference/substitutions.md` — include / type / check / tensor-method / dispatch
  swap tables (steps 5–10) and the device/stream snippet.
- `reference/ports.md` — the reference-ports matrix + `torch_call_dispatcher`
  escape hatch for ops with no stable wrapper.
- `reference/torch-compile.md` — the fake/meta-kernel decision procedure for
  `torch.compile` (step 12): detect the op's case, then act.
- `reference/background.md` — the "why" (ABI basics, CUDA/ROCm, abi3) for humans
  or when you need rationale, not steps.

**Authoritative sources** (if this skill disagrees with them, they win):

- LibTorch Stable ABI note — <https://docs.pytorch.org/docs/stable/notes/libtorch_stable_abi.html>
- Custom C++ and CUDA Operators — <https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html>
- Shim symbol → Torch version map (the floor source of truth, steps 2 & 16) —
  <https://github.com/pytorch/pytorch/blob/main/torch/csrc/stable/c/shim_function_versions.txt>

**Tooling (recommended) — offer it in step 1, don't skip it.**
`pytorch-stable-abi-transform`
(<https://github.com/TorchedHat/pytorch-stable-abi-transform>) is a deterministic
Clang AST rewriter that automates the mechanical parts of this port — the
`audit`/`plan`/`rewrite` modes cover steps 1 and 5–10, and compile-based
verification supports step 16. Prefer running it for the bulk edit and then
handling only what it flags (`TensorOptions`, `PYBIND11_MODULE`, project dispatch
macros), rather than rewriting every file by hand. It is a **build-from-source
C++ tool** (LLVM/Clang dev libs), not a pip package, and it **ships its own
Claude Code skill** (`migrate-stable-abi`) + `CLAUDE.md`. **Proactively tell the
user it exists and offer to set it up at the start** (step 1) — do not silently
hand-rewrite the whole extension when this tool would do the bulk deterministically.

**Definition of done:** the extension builds with `-DTORCH_TARGET_VERSION` (and
`-DTORCH_STABLE_ONLY`); a symbol audit finds zero `at::`/`c10::`/unstable
`torch::` symbols in the `.so`; the test suite passes; and you have written the
abi3 assessment (step 17).

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv** (never
> global/user site-packages); don't delete content or commit/push without approval
> (never straight to `main`); **ask before installing heavy packages or starting a
> heavy compile** (Torch/CUDA are multi-GB); match the project's existing style and
> keep comments/docstrings terse. **Capitalize "Torch"** as the product name in
> prose, comments, and commit messages (the `torch` import/package stays lowercase).

## 1. Check upstream, then inventory and classify

**First, check upstream for prior work** ([`../GUARDRAILS.md`](../GUARDRAILS.md) →
*Prior work*): a stable-ABI port is exactly the kind of change a maintainer may
already have started. Find the upstream repo (`git remote -v`, `[project.urls]`;
if this is a fork, `gh repo view --json parent`) and search its issues + PRs
(open/merged/closed) for `stable ABI`, `torch::stable`, `STABLE_TORCH_LIBRARY`,
`TORCH_TARGET_VERSION`, `abi3`. Report what you find before porting.

Then inventory and classify:

```bash
grep -rnE 'PYBIND11_MODULE|py::class_|torch::class_|TORCH_LIBRARY|nanobind' csrc/ src/
grep -rnE '\bat::|\bc10::|TORCH_CHECK|AT_DISPATCH|data_ptr<|\.dtype\(\)|getCurrentCUDAStream|CUDAGuard' csrc/ src/
grep -rnE 'torch\.version\.(cuda|hip)' --include=setup.py --include='*.py' \
     --include=CMakeLists.txt --include='*.cmake' --include=meson.build .   # how the build selects CUDA/HIP/CPU
find . -name '*.cu' | head ; ls setup.py pyproject.toml CMakeLists.txt 2>/dev/null
```

- **Easy** — free-function ops only, no `py::class_`, no exotic ATen. Mechanical.
- **Medium** — many ops / custom dispatch / heavy kernels. Mechanical but large;
  port file-by-file.
- **Hard** — exports C++ **classes** (`py::class_`/`torch::class_`) or takes real
  Python objects. The stable ABI has **no class equivalent** — see step 13.

**Offer to set up `pytorch-stable-abi-transform` now** (the *Tooling* note above)
— the deterministic rewriter that does the bulk of steps 5–10 and compile-verifies
the result. Don't quietly skip it and hand-rewrite everything. It is a
build-from-source C++ tool with LLVM/Clang deps, so **ask the user before setting
it up** (per [`../GUARDRAILS.md`](../GUARDRAILS.md) → *Footprint*). Once they agree:

```bash
# LLVM/Clang dev libs + Ninja (tested with LLVM 19):
#   Fedora: sudo dnf install clang-devel llvm-devel ninja-build
#   Ubuntu: sudo apt install libclang-19-dev libclang-cpp19-dev llvm-19-dev ninja-build
git clone https://github.com/TorchedHat/pytorch-stable-abi-transform
cmake -GNinja -B build -S pytorch-stable-abi-transform && cmake --build build
./build/stable-abi-transform --init-config > .stable-abi.yaml   # set pytorch_root / project_root
```

It also ships its **own Claude Code skill** (`migrate-stable-abi`) and a
`CLAUDE.md`; if the user prefers, point their agent at those and drive the tool
from there instead. Either way, use it for a first-pass inventory —
`--mode=audit` (read-only) and `--mode=plan` (dependency-aware file grouping)
give a richer, AST-level classification than the greps above.

The rewriter operates on `.cpp` TUs; CUDA `.cu` device code (kernels, launch
wrappers, atomics, dispatch macros, the `data_ptr` const-split) still needs
hand-porting. On a CPU-only box those `.cu` files are neither compiled nor
symbol-audited (step 16) — port them by hand and flag them for a GPU reviewer.

## 2. Choose the Torch floor (`TORCH_TARGET_VERSION`)

Pick the **lowest** Torch version that has every stable API you call — it becomes
the minimum Torch the wheel loads on. **Default 2.10** unless forced higher:

| If you call… | Min floor | Encoding |
| --- | --- | --- |
| `STABLE_TORCH_LIBRARY`, `torch::stable::Tensor`, no-deleter `from_blob` | 2.10 † | `0x020a000000000000` |
| `torch::stable::from_blob` **with a deleter** | 2.11 | `0x020b000000000000` |
| `Stream::nativeHandle()` (else use the AOTI shim) | 2.13 | `0x020d000000000000` |
| `torch_tensor_from/to_pyobject` | 2.14 | `0x020e000000000000` |

† `STABLE_TORCH_LIBRARY` / `torch::stable::Tensor` first appeared in **2.9**, but
2.10 is the first release with C-shim version *enforcement* — so **2.10 is the
recommended floor** even though these APIs are technically available on 2.9.

The table above is only the common cases. For **any** shim symbol, the
authoritative "which Torch version added this" list is
[`torch/csrc/stable/c/shim_function_versions.txt`](https://github.com/pytorch/pytorch/blob/main/torch/csrc/stable/c/shim_function_versions.txt)
in the pytorch tree — one `function_name: TORCH_VERSION_MAJOR_MINOR_PATCH` per
line (e.g. `torch_from_blob: TORCH_VERSION_2_11_0`); a symbol *not* listed there
was available before 2.10. Grep it for every shim your code calls and take the
**max** version as your floor. Check the copy that ships with your installed Torch
(`python -c 'import torch,os; print(os.path.join(os.path.dirname(torch.__file__), "csrc/stable/c/shim_function_versions.txt"))'`)
so it matches the headers you build against, not just `main`.

setuptools projects usually compute the hex (`0x0MMmm00000000000`) from a
`(major, minor)` tuple defined **once at module top level**, so the floor lives in
a single place (causal-conv1d, state-spaces/mamba#1042):

```python
TORCH_STABLE_ABI_MIN = (2, 10)  # the one source of truth
TORCH_TARGET_VERSION = "0x{:02x}{:02x}000000000000".format(*TORCH_STABLE_ABI_MIN)
```

**Reuse that same tuple for the runtime version pin** so the build floor and the
install requirement can never disagree:

```python
install_requires = [
    f"torch >= {TORCH_STABLE_ABI_MIN[0]}.{TORCH_STABLE_ABI_MIN[1]}",
    ...,
]
```

Don't hand-pack the hex any other way — the bit math is easy to get subtly wrong.
Use the bundled helper to get (or check) the token, and to decode a value read back
from `_C.TORCH_TARGET_VERSION`:

```bash
python scripts/torch_target_version.py encode 2.10   # -> 0x020a000000000000
python scripts/torch_target_version.py decode 0x020a000000000000   # -> 2.10
```

amd-quark passes the token `TORCH_VERSION_2_10_0` instead; either works.

## 3. Build system

Pass both defines to `cxx` **and** `nvcc`. What must not drift is the *value*
(`TORCH_TARGET_VERSION`, from the one top-level tuple in step 2) — not the list
object. Either splat one shared list (xformers pattern) …

```python
stable_args = [f"-DTORCH_TARGET_VERSION={TORCH_TARGET_VERSION}", "-DTORCH_STABLE_ONLY"]
extra_compile_args = {
    "cxx": ["-std=c++17", *stable_args],
    "nvcc": ["-std=c++17", *stable_args, "-DUSE_CUDA"],
}
```

… or **repeat the two defines inline** in each list — equally safe, and often
clearer since it shows exactly what each compiler gets (causal-conv1d, which also
carries `-DUSE_CUDA` on both host and device — see the stream note below):

```python
extra_compile_args = {
    "cxx": [
        "-O3",
        "-DUSE_CUDA",
        f"-DTORCH_TARGET_VERSION={TORCH_TARGET_VERSION}",
        "-DTORCH_STABLE_ONLY",
    ],
    "nvcc": [
        "-O3",
        "-DUSE_CUDA",
        f"-DTORCH_TARGET_VERSION={TORCH_TARGET_VERSION}",
        "-DTORCH_STABLE_ONLY",
        ...,
    ],
}
```

CMake equivalent: `target_compile_definitions(${tgt} PRIVATE TORCH_TARGET_VERSION=0x020a000000000000)` plus `-DUSE_CUDA`/`-DUSE_MPS` where shim streams are used.

- `-DUSE_CUDA` exposes `aoti_torch_get_current_cuda_stream` in `shim.h` (guarded
  by `#ifdef USE_CUDA` only). **Only add it if the extension actually calls the
  current-stream shim** — it is not a blanket "this is a GPU build" flag, and an
  extension that never asks Torch for the current stream doesn't need it at all.
  When you do need it, add it wherever the shim is compiled — `.cpp` files too,
  not just `.cu` (torchvision gotcha). ROCm keeps the `..._cuda_stream` name (HIP
  masquerades as CUDA), so on ROCm the *same* condition applies: define
  `-DUSE_CUDA` **only for the stream shim**, alongside `-DUSE_ROCM=1` — not on
  every HIP source file by default.
- Keep the build-system Torch pin in sync (`pyproject.toml` / `install_requires`
  → `torch >= <floor>`).
- `-DTORCH_STABLE_ONLY` is strongly recommended (step 4) but optional; torchvision
  and amd-quark rely on discipline instead.

**Do most of the port on CPU-only Torch.** The stable ABI is device-agnostic, so
the mechanical rewrites (steps 5–10), the CPU build, the symbol audit (step 16),
and the cross-Torch-version load test all work against
`uv pip install torch --index-url https://download.pytorch.org/whl/cpu` — a few
hundred MB, no nvcc, no GPU. Only reach for the CUDA Torch + nvcc wheels (below)
when you build `.cu` device code or run GPU smoke tests. See
[`../GUARDRAILS.md`](../GUARDRAILS.md) → *Footprint*.

**Caveat — backend detection.** Many extensions pick their CUDA / HIP / CPU build
path from `torch.version.cuda` and `torch.version.hip` (e.g.
`if torch.version.hip: … elif torch.version.cuda: … else: CPU`). The check may live
in `setup.py`, in `CMakeLists.txt` (an `execute_process(... import torch ...)`), or
in `meson.build` (a `run_command(py, '-c', 'import torch; …')`) — check all three.
On **CPU-only Torch both are `None`**, so such a build silently takes the CPU path
and skips the `.cu`/HIP sources entirely — useful for a fast CPU-path port, but it
means the device code isn't compiled or audited. Build once against the matching
CUDA (or ROCm) Torch before you call the port done. Note also that a ROCm Torch
reports `torch.version.hip` set **and** `torch.version.cuda` `None`, which is why
the HIP branch must key off `torch.version.hip`, not the absence of CUDA.

**GPU device code (does *not* collapse with the ABI — one wheel per CUDA major +
per GPU arch; rationale in `reference/background.md`):**

- **CUDA version:** build against the **lowest minor** of a CUDA major (minor
  compat since CUDA 11); one wheel per major. Pin the build-Torch's CUDA so
  `cudart` matches the user's Torch.
- **Getting `nvcc` without a system toolkit:** the CUDA compiler and libraries are
  on PyPI as venv-local wheels — `nvidia-cuda-nvcc-cu12` (nvcc),
  `nvidia-cuda-runtime-cu12`, `nvidia-cuda-cccl-cu12` (thrust/cub headers),
  `nvidia-cuda-nvrtc-cu12`, `nvidia-cublas-cu12`, … (and a `-cu11` line) — the same
  components Torch's CUDA wheels pull in. `uv pip install nvidia-cuda-nvcc-cu12`
  drops nvcc under `site-packages/nvidia/cuda_nvcc/bin/` (no sudo, no system
  install; see [`../GUARDRAILS.md`](../GUARDRAILS.md) → *Footprint*). Match the
  CUDA major/minor to build-Torch, point the build at it (`CUDACXX=…/nvidia/cuda_nvcc/bin/nvcc`
  or `CUDA_HOME`), and remember these wheels omit profilers/debuggers and a host
  C++ compiler.
- **Arch / device code:** set `TORCH_CUDA_ARCH_LIST`, e.g. `"8.0 9.0 12.0+PTX"`.
  All archs pack into **one fatbinary** in the `.so`; `+PTX` on the top arch adds
  a driver-JIT fallback for newer GPUs. New GPU = add its `sm_XX` and rebuild.
- **Driver-API-only** (e.g. `cuMem*`, `-lcuda`, no `.cu`): no device code, no
  `cudart`, no arch list — nearly CUDA-major-agnostic.
- **ROCm / HIP:** pass `-DUSE_ROCM=1 -D__HIP_PLATFORM_AMD__=1` (auto with
  `CUDAExtension`; add manually with `CppExtension`) — this is the "build against
  ROCm Torch" switch. It is *separate* from `-DUSE_CUDA`, which on ROCm gates
  **only** the current-stream shim (add it just for that, per step 3 above — not
  to every HIP file). Link `amdhip64`; archs via
  `PYTORCH_ROCM_ARCH` (`gfx*`) → one bundled ("fat") code object. HIP-aware
  source: use `CppExtension` to skip Torch's hipify (it rewrites/breaks headers).
  hipify trap: it emits duplicate `_hip.h` for third-party headers on the include
  path → route those as raw `-I`.

## 4. `TORCH_STABLE_ONLY` and the pybind/fmt workaround

`-DTORCH_STABLE_ONLY` makes any `at::`/`c10::`/non-stable `torch::` use a hard
compile error — the single best guardrail. Defining `TORCH_TARGET_VERSION`
**already implies** it; setting it explicitly just makes intent obvious.

Gotcha (**Torch < 2.13 only**): Torch bundles pybind11 and fmt under `torch/`, and
on those versions the header-only, ABI-independent headers trip the guard. Torch
**≥ 2.13 allow-lists pybind/fmt** (pytorch/pytorch#174372), so the guard no longer
fires and the workaround below is unnecessary. If your floor is below 2.13 and a TU
still includes them, lift the guard around **only** those includes:

```cpp
// Torch < 2.13 only: pybind11/fmt ship inside torch and trip the TORCH_STABLE_ONLY
// guard the target macro implies, though they are header-only and
// Torch-ABI-independent. 2.13+ allow-lists them, making this dance a no-op.
// See pytorch/pytorch#174372, meta-pytorch/torchcodec#1260.
#pragma push_macro("TORCH_STABLE_ONLY")
#pragma push_macro("TORCH_TARGET_VERSION")
#undef TORCH_STABLE_ONLY
#undef TORCH_TARGET_VERSION
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#pragma pop_macro("TORCH_TARGET_VERSION")
#pragma pop_macro("TORCH_STABLE_ONLY")
```

Apply this to **every** TU compiled with the stable defines that transitively
includes pybind — not just the `PYBIND11_MODULE` one. An implementation `.cpp` that
only pulls pybind in through a header (e.g. a `cocoeval.cpp` with no Torch calls of
its own) still trips the guard and still needs the dance.

Also: `<torch/version.h>` `#error`s when `TORCH_TARGET_VERSION` is defined, so you
**cannot read `TORCH_VERSION_MAJOR/MINOR`** in a stable TU. Treat "target defined"
as "≥ floor"; include `version.h` only when it is *not* defined.

## 5–10. Mechanical rewrites

Prefer `pytorch-stable-abi-transform --mode=rewrite` (deterministic Clang AST
rewriter) for this bulk: it applies includes (5), types (6), checks (7),
method→function (8), `data_ptr` disambiguation, and CUDA guards (9), then flags
what it can't do. Fall back to the swap tables in **`reference/substitutions.md`**
for hand edits and to understand each change: includes (5), types (6),
checks/error macros (7), tensor methods → stable free functions (8), device/stream
(9), dispatch macros (10). The non-obvious traps to keep in mind while you go:

- **No negative dims** — `t.stride(-1)` → `t.stride(t.dim()-1)`.
- **`data_ptr<T>()` splits** into `const_data_ptr<T>()` (read) /
  `mutable_data_ptr<T>()` (write); const-ness propagates into kernel signatures.
- **`.item()` and element indexing are gone** — read `const_data_ptr<T>()` + strides
  (also avoids a per-element GPU→CPU sync).
- `kInt8` → `Char`, `kInt64` → `Long`; `t.dtype()` → `t.scalar_type()`.
- **CUDA error checks:** don't hand-roll a replacement for `C10_CUDA_CHECK` /
  `C10_CUDA_KERNEL_LAUNCH_CHECK`. Torch ships stable-ABI equivalents,
  `STD_CUDA_CHECK(expr)` / `STD_CUDA_KERNEL_LAUNCH_CHECK()`, in
  `<torch/csrc/stable/macros.h>` — present since the **2.10** floor (no version
  bump), and they route through the C10 CUDA shim for proper error formatting.
  Include that header (it expects `cuda_runtime.h`) and drop any bespoke macro
  (causal-conv1d).
- If a method has no stable equivalent, use the dispatcher escape hatch in
  `reference/ports.md`.

**Stay DRY** ([`../GUARDRAILS.md`](../GUARDRAILS.md) → *Style*): the same swap
recurs across many TUs (the stream/device-guard helper, a boxed-op wrapper, a
`const_data_ptr` accessor). Factor each into **one shared helper header** the
`.cpp`/`.cu` files include — every surveyed port does (`reference/substitutions.md`
§9) — rather than pasting the snippet into each file.

## 11. Op registration

Replace `PYBIND11_MODULE`/`TORCH_LIBRARY` with the stable macros. Schema strings
are the classic dispatcher schemas (`Tensor(a!)` mutated, `Tensor?` optional,
`-> ()` void).

```cpp
STABLE_TORCH_LIBRARY(myns, m) {              // or STABLE_TORCH_LIBRARY_FRAGMENT to split across files
  m.def("my_op(Tensor a, int n) -> Tensor");
}
STABLE_TORCH_LIBRARY_IMPL(myns, CUDA, m) {   // CPU / CUDA / MPS / CompositeExplicitAutograd
  m.impl("my_op", TORCH_BOX(&my_op_fn));
}
```

- `TORCH_BOX(&fn)` **needs an addressable symbol** — wrap `inline`/lambda helpers
  in a named free function first.
- Single-binary CPU+CUDA: register `CompositeExplicitAutograd` and branch on
  `t.is_cuda()`, or register separate `CPU`/`CUDA` impls.
- Dispatcher ops run **GIL-free**; drop any `py::gil_scoped_release`. Scalars cross
  as `int64_t`/`double`.
- **Match schema widths at the boxed boundary** — a helper's params *and* return
  must be the canonical types (`int`→`int64_t`, `float`→`double`). A plain `int`
  return against `-> int` can hit an ambiguous `from(int)` overload and fail to
  box; widen to `int64_t`.
- **One unique alias symbol per mutated tensor** (`Tensor(a!)`, `(b!)`, …). An op
  may mutate several out/scratch args and still return `int`/`()`. Over-declaring
  an input as mutated is safe; *under*-declaring silently breaks functionalization
  / `torch.compile`.

## 12. Move to Python what the ABI can't express

The stable C++ surface is forward-kernels only (torchvision is the reference):

- **Autograd** → `torch.library.register_autograd("myns::op", bwd, setup_context=…)`.
- **Autocast** → `torch.library.Library("myns", "IMPL").impl(op, fn, "AutocastCUDA")`.
- **Fake/meta** (for `torch.compile`) → `@torch.library.register_fake("myns::op")`,
  **but only when the op returns tensors.** An op that returns `None` and only
  mutates pre-allocated outputs needs no fake (causal-conv1d); one that returns
  tensors does, or `fullgraph=True` fails (state-spaces/mamba#1042); a
  data-dependent output shape needs `get_ctx().new_dynamic_size()`. Whichever case,
  `mutates_args` must be complete (step 11) — an undeclared mutation silently
  corrupts the compiled graph. Detection procedure (incl. a CPU-only empirical
  check), upstream citations, and per-case actions: **`reference/torch-compile.md`**.
- **Global context flags** (e.g. deterministic mode) → read in Python and pass as
  an op argument.

## 13. C++ classes (no `torch::class_` in the stable ABI)

If the inventory found `py::class_`/`torch::class_`, pick one:

1. **Opaque handle-in-a-tensor** (torchcodec) — heap-allocate the object, launder
   its pointer through a 1-element int64 CPU tensor via
   `torch::stable::from_blob(ptr, {1}, {1}, cpu, kLong, deleter)`; the deleter
   owns it. All-stable, `torch.compile`-safe.
2. **Small pybind11 section** in the *same* `.so` (kvcached keeps `PageAllocator`).
   Only tensor ops go stable; pass an int64 handle across. Needs the step-4
   workaround; **caps abi3** (step 17).
3. **nanobind** — keeps pybind-style classes and is abi3-capable; higher Python
   floor (cp312).

## 14. Module init / loading model

Choose based on whether you also want abi3 (step 17):

- **Plain library via `torch.ops.load_library()`** (torchvision, xformers,
  torchcodec). No `PyInit_`; ops register via static init. Override
  `get_export_symbols` to `[]` (setuptools); keep the filename plain
  (`no_python_abi_suffix=True`). Windows still needs a stub `PyInit_<name>`
  returning `nullptr`.
- **Real CPython module** (causal-conv1d, torchaudio) — needed for `import
  mypkg._C` *and* abi3. Hand-write a multi-phase init: `PyModuleDef` with
  `m_size = 0`, a `PyModuleDef_Slot` array (add `Py_mod_gil =
  Py_MOD_GIL_NOT_USED` under `#ifdef Py_GIL_DISABLED`), and
  `PyMODINIT_FUNC PyInit__C() { return PyModuleDef_Init(&def); }`.

Either way, no TU built with the stable defines — including the pybind11 section —
may include `<torch/extension.h>`; it drags in unstable ATen and trips
`TORCH_STABLE_ONLY`. Include
`<torch/csrc/stable/library.h>` plus the narrow pybind headers instead.
`PYBIND11_MODULE(TORCH_EXTENSION_NAME, m)` still works: `TORCH_EXTENSION_NAME` is a
`-D` flag setuptools injects, not something `torch/extension.h` provides.

## 15. Python-side wiring

- Importing the extension registers the ops; expose them as `torch.ops.<ns>.<op>`
  (optionally alias old names to keep call sites working).
- If you kept a pybind11 section (step 13), re-export those symbols too.

## 16. Verify

1. **Symbol audit** — the objective proof. Either `torch-abi-audit` on the built
   `.so` (labels it stable/unstable, counts stable-shim vs unstable symbols), or
   grep the `.so`: fail if any `_ZN2at`/`_ZN3c10`/`_ZN5torch` symbol (excluding
   `6stable`/`10headeronly`) is defined, or if any shim newer than your floor is
   imported. To know each imported shim's minimum version, cross-reference
   [`shim_function_versions.txt`](https://github.com/pytorch/pytorch/blob/main/torch/csrc/stable/c/shim_function_versions.txt)
   (step 2) — anything above your `TORCH_TARGET_VERSION` (e.g. `torch_from_blob` =
   2.11 on a 2.10 floor) means the wheel silently won't load on the floor.
   The raw `_ZN2at`/… grep only matches **Itanium** mangling (Linux/macOS,
   gcc/clang); a Windows `.pyd` uses **MSVC** mangling (`?…`) that it misses.
   De-mangle first so one audit works everywhere: pipe `nm -D`/`dumpbin` output
   through [`pycxxfilt`](https://github.com/tiran/pycxxfilt)
   (`python -m pycxxfilt`, or `pycxxfilt.demangle()`), which auto-detects Itanium
   vs MSVC (vs Rust), then fail on any readable `at::` / `c10::` / non-stable
   `torch::` namespace. `c++filt` works too but is Itanium-only.
2. **Build on the floor Torch and a newer Torch**; `import`; run a create/op smoke
   test on each. This is the single-wheel claim — it can't be checked by inspection.
3. Run the existing test suite and any pre-commit gates.

Complementary source check: `pytorch-stable-abi-transform` verifies each file
compiles against a shadow include tree of *only* stable headers — proof the source
is stable-clean before you build. Use it alongside the built-`.so` symbol audit.

## 17. Assess Python abi3 (`Py_LIMITED_API`)

**Do this after the Torch port** and write the findings down. abi3 is orthogonal:
the Torch stable ABI collapses the *Torch-version* axis; abi3 collapses the
*Python-version* axis (one `cpXY-abi3` wheel for all Python ≥ X.Y).

1. **Is pybind still present?** (`grep -rn 'pybind11\|py::class_' csrc/`). pybind11
   is incompatible with `Py_LIMITED_API`. A pybind11 section (step 13 option 2)
   **blocks** abi3 until removed / converted to nanobind / hand-written via
   `PyType_FromSpec`.
2. **Exported C++ classes** not yet on the handle pattern → the main blocker.
3. **If ops-only / handle-only → mostly a build-flag change:** `py_limited_api=True`
   on the extension; derive the tag from
   `torch.utils.cpp_extension.min_supported_cpython`
   (`{"bdist_wheel": {"py_limited_api": f"cp{maj}{min}"}}`) and set
   `python_requires`. Use the real-CPython init (step 14) or the `load_library`
   model (which sidesteps the CPython ABI entirely — a valid alternative).
   **Disable abi3 on free-threaded builds before CPython 3.15** (gate on
   `sysconfig.get_config_var("Py_GIL_DISABLED")` — pip refuses abi3 there). From
   Python 3.15, [PEP 803](https://peps.python.org/pep-0803/) **abi3t**'s compatible
   interpreters are a *superset* of abi3's — a `.abi3t.so` loads on **both**
   GIL-enabled and free-threaded 3.15+ — so the combined **`abi3.abi3t`** tag
   ships one wheel for regular *and* free-threaded Python ≥3.15 once Torch's
   tooling targets it.
4. **Report:** blocked / trivial-flag / not-worth-it, with the specific blocker and
   recommended route (handle pattern, nanobind at cp312, or `load_library`).
   Torch-stable ≠ abi3 — see the `abi3?` column in `reference/ports.md`.
