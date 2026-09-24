# Non-limited → limited API substitutions

SKILL step 5. Run `upgrade_pythoncapi.py` first for the mechanical cases, then
hand-finish the rest with this table. The rule: anything that reads a struct field
directly, or is a macro/`static inline` that bakes in a layout, has a function form
in the limited API — use it. `abi3audit` (step 9) catches what you miss.

## Object header / identity

| Non-limited (macro / field access) | Limited API |
| --- | --- |
| `op->ob_type` | `Py_TYPE(op)` |
| `Py_TYPE(op) = t` / `op->ob_type = t` | `Py_SET_TYPE(op, t)` |
| `op->ob_refcnt` | `Py_REFCNT(op)` |
| `op->ob_refcnt = n` | `Py_SET_REFCNT(op, n)` |
| `op->ob_size` (var-objects) | `Py_SIZE(op)` |
| `Py_SIZE(op) = n` | `Py_SET_SIZE(op, n)` |
| `x == Py_None` / `!= Py_None` | `Py_IsNone(x)` / `!Py_IsNone(x)` |
| `x == Py_True` / `Py_False` | `Py_IsTrue(x)` / `Py_IsFalse(x)` |
| new ref idioms | `Py_NewRef(o)` / `Py_XNewRef(o)` |

Most of the above are exactly what `upgrade_pythoncapi.py` rewrites (adding
`#include "pythoncapi_compat.h"` so they still compile on old Pythons).

## Container fast-paths (the perf trade-off)

| Non-limited (fast macro) | Limited API (function) |
| --- | --- |
| `PyList_GET_ITEM(l, i)` | `PyList_GetItem(l, i)` (borrowed) / `PyList_GetItemRef` (3.13+, strong) |
| `PyList_SET_ITEM(l, i, v)` | `PyList_SetItem(l, i, v)` |
| `PyList_GET_SIZE(l)` | `PyList_Size(l)` |
| `PyTuple_GET_ITEM(t, i)` | `PyTuple_GetItem(t, i)` |
| `PyTuple_GET_SIZE(t)` | `PyTuple_Size(t)` |
| `PyDict_GET_SIZE(d)` | `PyDict_Size(d)` |
| `PyBytes_AS_STRING(b)` | `PyBytes_AsString(b)` |
| `PyUnicode_DATA` / `..._GET_LENGTH` / `..._READ` | `PyUnicode_AsUTF8AndSize`, `PyUnicode_GetLength`, `PyUnicode_ReadChar` |

These functions add bounds checks / a call the macro skipped — the source of the
limited-API slowdown. In hot loops, hoist the length and fetch once rather than
per-iteration.

## Types and slots

| Non-limited | Limited API |
| --- | --- |
| `static PyTypeObject T = {...}` | `PyType_Spec` + `PyType_FromModuleAndSpec` (see `heap-types.md`) |
| `Type.tp_alloc`, `Type.tp_free`, any `tp_*` read | `PyType_GetSlot(type, Py_tp_alloc)` etc. |
| `&SubclassOfBuiltin.base.field` | getter functions on the base type |
| `PyObject_HEAD_INIT` in a static object | build the object at runtime |

## Not in the limited API (needs a rethink, not a swap)

- **Private `_Py*` / internal API** — no stable equivalent by definition. Find a
  public function or drop the optimization.
- **`PyUnstable_*`** — deliberately outside abi3; using it forfeits stability.
- **Direct access to another type's instance struct** (e.g. reaching into
  `PyDictObject`) — only via public accessors.
- **`tp_print`** and other removed slots — gone.
- **`PyType_FromMetaclass` / `PyObject_GetTypeData` / relative offsets** — available,
  but 3.12+; below that floor, restructure or raise the floor.

## Reference-leak traps (the swap changes ref semantics)

Some substitutions don't just rename a call — they hand back a **different kind of
reference**, so a mechanical swap without a matching `Py_DECREF` leaks (or an extra
one crashes). Audit each of these by hand:

| Borrowed before | Strong (`*Ref`) after | Fix |
| --- | --- | --- |
| `PyList_GET_ITEM` / `PyList_GetItem` | `PyList_GetItemRef` (3.13+) | `Py_DECREF` the result when done |
| `PyDict_GetItem` (also swallows errors) | `PyDict_GetItemRef` (3.13+) | `Py_DECREF`; check for error |
| `PyDict_GetItemWithError` | `PyDict_GetItemRef` | `Py_DECREF` |
| `PyWeakref_GetObject` | `PyWeakref_GetRef` | `Py_DECREF` |
| `PyImport_AddModule` | `PyImport_AddModuleRef` | `Py_DECREF` |

- **`PyModule_AddObject` → `PyModule_AddObjectRef`** flips the other way: the old one
  **steals** your reference *only on success*, the new one **doesn't steal**. When you
  migrate (recommended — the old contract is a classic leak-on-error), delete the
  now-wrong `Py_DECREF` on the success path.
- **Heap types hold a reference to their type.** After the static→heap conversion,
  `tp_traverse` must `Py_VISIT(Py_TYPE(self))` and `tp_dealloc` must
  `Py_DECREF(Py_TYPE(self))` (after untracking). Omit the visit → uncollectable
  cycles; omit the decref → the type leaks. See `heap-types.md`.
- Reference **stealers** to re-check while editing: `PyList_SetItem`,
  `PyTuple_SetItem`, `PyStructSequence_SetItem`.

Step 9 has an easy temporary check to catch whatever slips through.

## Gotchas the define won't catch

- `Py_LIMITED_API` covers *definitions only* — passing `NULL` to a function that
  accepts it on new Python but dereferences it on old, or relying on a struct field
  that's "leaked" through the limited headers, compiles fine and crashes at runtime.
  This is why step 9 tests on the **lowest** floor, not just the newest.
- A `.so` that imports fine can still call a non-abi3 symbol via `dlsym` at runtime —
  `abi3audit` can't see that. Don't do it.
