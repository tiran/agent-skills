# `torch.compile` and fake/meta kernels (step 12)

A fake (meta) kernel lets fake-tensor tracing infer an op's output metadata without
running it. Whether you need one — and whether `fullgraph=True` works at all —
depends on the op's shape. Detect the case **per registered op**, not once for the
package.

These rules are verified against upstream (if they disagree, upstream wins):

- [Python custom ops](https://docs.pytorch.org/tutorials/advanced/python_custom_ops.html)
  — "add a FakeTensor kernel … specifies how to compute the metadata of output
  tensors given the metadata of input tensors."
- [Mutable custom ops](https://docs.pytorch.org/tutorials/advanced/python_custom_ops_mutable.html)
  — "Because the operator doesn't return anything, there is no need to register a
  FakeTensor kernel (meta kernel) to get it to work with `torch.compile`." (and:
  "If a mutable operator also returns a fresh Tensor, register a fake kernel.")
- [`torch.library`](https://docs.pytorch.org/docs/stable/library.html) —
  `register_fake` example 2 (`custom_nonzero`) for data-dependent shapes via
  `get_ctx().new_dynamic_size()`; `register_autograd` for backward.

## Detect the case

1. **Read the schema / registration.** `grep -rnE 'm\.def\("' csrc/` (C++) and
   `grep -rnE 'custom_op|register_fake|register_autograd|mutates_args' <pkg>/`
   (Python). In each schema the `-> …` tail is the return and `(a!)`/`mutates_args`
   are the declared mutations:
   - `-> ()` (or a Python op typed `-> None`) = **returns nothing** → likely the
     no-fake case; confirm step 2.
   - `-> Tensor` / `-> (Tensor, Tensor)` = **returns tensors** → fake required.
2. **Find where the returned/output tensors are allocated.** Look at the Python
   wrapper that calls the op: outputs built with `torch.empty_like` / `zeros_like` /
   `new_empty` *before* the call and passed in as mutated args = metadata already
   known to the tracer → **no fake**. Outputs allocated inside C++ and returned =
   fake needed.
3. **Check `mutates_args` completeness** — cross-check every declared `(a!)` /
   `mutates_args` entry against what the kernel actually writes (`mutable_data_ptr`,
   `copy_`, `out`-style params). A write with no matching declaration is the silent
   failure below; grep the kernel for stores into each pointer.
4. **Flag data-dependent output shapes** — scan for an output whose size comes from a
   tensor *value* (`nonzero`, `unique`, `masked_select`, cumulative-length /
   `cu_seqlens` indexing) rather than input `.sizes()`. Those need a dynamic fake.
5. **Confirm empirically (cheap, CPU-only).** `torch.compile(fn, fullgraph=True)`
   then call it on CPU tensors — fake tracing runs no kernel, so no GPU is needed. A
   clean trace = no care required; an error / graph break names the op and case that
   does. This is the ground truth; the greps above just tell you where to look.

## Act by case

- **Op returns `None` and only mutates pre-allocated outputs** (allocated in a
  Python wrapper via `torch.empty_like`/`zeros_like`, the causal-conv1d pattern):
  **no fake needed.** There is no output metadata to infer, so
  `torch.compile(fullgraph=True)` traces fwd *and* bwd (even through a
  `torch.autograd.Function`) with nothing registered — verified on CPU, which
  suffices since fake tracing runs no kernel. Registering a `return None` fake is
  harmless but adds no behavior; don't add code — or a test asserting it — the
  design doesn't require.
- **Op returns tensors:** **fake required.** Write a `register_fake` that allocates
  outputs of the right shape/dtype/device from the inputs. Without it,
  `fullgraph=True` errors and `fullgraph=False` graph-breaks to eager
  (state-spaces/mamba#1042).
- **Data-dependent output shape** (shape depends on tensor *values*, not just input
  shapes): a plain fake can't express it — use
  `torch.library.get_ctx().new_dynamic_size()` for the unbacked dim, and expect
  guards/recompiles.
- **`mutates_args` must be complete** (step 11) regardless of the above — an
  *undeclared* mutation silently corrupts the compiled graph (no error), so this is
  the one thing to get right even when no fake is needed.
- **Autograd under compile:** a Python `torch.autograd.Function` is traced by Dynamo
  directly; a C++/dispatcher-registered backward needs
  `torch.library.register_autograd` (step 12). Either way the underlying fwd/bwd ops
  follow the fake rules above.
