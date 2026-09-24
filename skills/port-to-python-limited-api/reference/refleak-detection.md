# Detecting reference leaks

SKILL step 9. Limited-API swaps flip borrowed↔strong references
(`api-substitutions.md`), so a mechanical port can leak (missing `Py_DECREF`) or
crash (extra one). These are **temporary** diagnostics — wire one in during the port,
delete it once clean. A steady per-iteration climb = leak; a steady drop =
over-decref; growth only after cycles form = a heap-type `tp_traverse`/`tp_clear` bug.

Pick at least one lens from **each** applicable column. The debug-build lenses give
exact refcounts; the standard-build lenses need no special interpreter, so they also
run in CI against the release wheel you actually ship.

## Works on any build (standard *or* debug)

- **`sys.getrefcount(obj)` — localize.** Read a *specific* known object's count before
  and after the suspect call; the delta names the culprit. (getrefcount itself holds a
  temporary ref, so compare deltas, not absolutes.)
- **`gc` object census — build-agnostic, catches cycles.** Count live instances of
  your type across a loop:
  ```python
  import gc

  before = sum(1 for o in gc.get_objects() if type(o).__name__ == "MyType")
  for _ in range(10_000):
      m.make_and_drop()
  gc.collect()
  after = sum(1 for o in gc.get_objects() if type(o).__name__ == "MyType")
  print("leaked instances:", after - before)
  ```
  `gc.set_debug(gc.DEBUG_LEAK)` then inspecting `gc.garbage` after `gc.collect()`
  surfaces uncollectable cycles specifically — the heap-type case (`heap-types.md`).
- **`tracemalloc` — allocation diff.** `tracemalloc.start()`, snapshot, run the loop,
  `snapshot2.compare_to(snapshot1, "lineno")`; growth attributed to your module is a
  leak. Pure Python, release builds included.
- **RSS smoke test — crude but universal.** Loop the call a few million times and watch
  `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`. Won't localize, but proves a
  leak exists on the exact release wheel — a good CI gate.
- **`objgraph` (third-party).** `objgraph.growth()` between iterations reports which
  types keep growing; handy when you don't yet know which object leaks.

## Needs a debug build (`--with-pydebug` / `Py_DEBUG`) — strongest signal

- **`python -X showrefcount`** prints total refs + memory blocks after the run:
  ```bash
  python -X showrefcount -c "import m; [m.f() for _ in range(10_000)]"
  ```
- **`sys.gettotalrefcount()`** — the exact interpreter-wide count; assert it holds
  across a warmed-up loop for a precise per-call delta.
- **`python -m test -R 3:3 test_m`** — CPython's own refleak hunter
  (`-R runs:warmups`); reports `test_m leaked [x, y, z] references`. `pytest-leaks`
  (Victor Stinner) wraps the same idea for a pytest suite.

## One harness for both

Prefer the exact count when the interpreter offers it, fall back to a `gc` census
otherwise — so the *same* throwaway check runs on a release and a debug build:

```python
import gc, sys


def refleak(fn, runs=10_000, warmup=10):
    for _ in range(warmup):
        fn()
    gc.collect()
    exact = hasattr(sys, "gettotalrefcount")  # True only on a debug build
    before = sys.gettotalrefcount() if exact else len(gc.get_objects())
    for _ in range(runs):
        fn()
    gc.collect()
    after = sys.gettotalrefcount() if exact else len(gc.get_objects())
    print(f"{'refs' if exact else 'objects'} delta: {after - before} over {runs} runs")
```

Run it on the **lowest** floor you tag and on the newest, and for `abi3t` on a
free-threaded build too — a swap that's balanced on one version can leak on another.

## Sanitizers (either build; needs a rebuild, not an interpreter swap)

- **ASan/LeakSanitizer** — compile the extension with `-fsanitize=address`; LSan lists
  leaked C allocations at exit. Works against a release Python; a debug Python trims
  false positives. Fast enough for CI.
- **Valgrind memcheck** with `--suppressions=<cpython>/Misc/valgrind-python.supp
  --leak-check=full` — heaviest, but finds non-refcount C leaks the others miss.
