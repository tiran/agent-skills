# Module init: single-phase → multi-phase → PyModExport (abi3t)

SKILL steps 6–7. Three stages: convert single-phase `PyInit_` to multi-phase init
(required for `abi3t`, good practice everywhere), then — **only if targeting
`abi3t`** — port to the PEP 793 export hook. Authoritative: the abi3t migration
how-to (<https://docs.python.org/3.15/howto/abi3t-migration.html>), PEP 793, PEP 803.

## Stage 1 — single-phase (old)

```c
static PyModuleDef mymod_def = {
    PyModuleDef_HEAD_INIT, "mymod", "docs", -1, mymod_methods,
};
PyMODINIT_FUNC PyInit_mymod(void) {
    PyObject *m = PyModule_Create(&mymod_def);
    /* ... create types, add objects ... */
    return m;
}
```

`m_size = -1` and setup code inside `PyInit_` mean global state and no
sub-interpreter support — both incompatible with clean isolation.

## Stage 2 — multi-phase (abi3)

Split into a `PyModuleDef` with a `PyModuleDef_Slot[]` array; `PyInit_` only returns
`PyModuleDef_Init`, and the real work moves to a `Py_mod_exec` function.

```c
typedef struct { PyTypeObject *FooType; } mystate;

static int mymod_exec(PyObject *m) {
    PyObject *foo = PyType_FromModuleAndSpec(m, &Foo_spec, NULL);
    if (!foo) return -1;
    ((mystate *)PyModule_GetState(m))->FooType = (PyTypeObject *)foo;
    return PyModule_AddObjectRef(m, "Foo", foo) < 0 ? -1 : 0;
}

static PyModuleDef_Slot mymod_slots[] = {
    {Py_mod_exec, mymod_exec},
#ifdef Py_mod_gil
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},                 /* 3.13+; needed for free-threading */
#endif
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
    {0, NULL},
};

static PyModuleDef mymod_def = {
    PyModuleDef_HEAD_INIT,
    .m_name = "mymod",
    .m_doc = "docs",
    .m_size = sizeof(mystate),                         /* was -1 */
    .m_methods = mymod_methods,
    .m_slots = mymod_slots,
    .m_traverse = mymod_traverse,                      /* visit objects held in state */
    .m_clear = mymod_clear,
    .m_free = mymod_free,
};

PyMODINIT_FUNC PyInit_mymod(void) { return PyModuleDef_Init(&mymod_def); }
```

`m_traverse`/`m_clear` must visit/clear the `PyObject *`s you store in module state
(the types, cached objects), mirroring the heap-type GC rules.

This stage alone gets you a working **`abi3`** module. Stop here unless step 2 chose
`abi3t`.

## Stage 3 — PyModExport (abi3t, Python 3.15)

Free-threaded 3.15 makes `PyObject` opaque, so the static `PyModuleDef` (which
extends `PyObject`) can't exist. PEP 793 replaces `PyInit_` with
**`PyModExport_<name>`**, which returns a **slot array** instead of an object. Build
with **`Py_TARGET_ABI3T`** (`0x030f0000`), which implies `Py_LIMITED_API` +
`Py_GIL_DISABLED`. Keep the stage-2 path under `#else` so one source still builds
`abi3` for ≤3.14.

```c
#ifdef Py_TARGET_ABI3T
PyABIInfo_VAR(abi_info);

static PySlot mymod_slotarray[] = {
    PySlot_STATIC_DATA(Py_mod_abi,        &abi_info),           /* required, new */
    PySlot_STATIC_DATA(Py_mod_name,       "mymod"),
    PySlot_STATIC_DATA(Py_mod_doc,        "docs"),
    PySlot_SIZE       (Py_mod_state_size, sizeof(mystate)),     /* was m_size */
    PySlot_STATIC_DATA(Py_mod_methods,    mymod_methods),
    PySlot_STATIC_DATA(Py_mod_token,      &mymod_token),        /* replaces PyModuleDef identity */
    PySlot_FUNC       (Py_mod_exec,       mymod_exec),
    PySlot_DATA       (Py_mod_gil,        Py_MOD_GIL_NOT_USED),
    PySlot_FUNC       (Py_mod_state_traverse, mymod_traverse),
    PySlot_FUNC       (Py_mod_state_clear,    mymod_clear),
    PySlot_FUNC       (Py_mod_state_free,     mymod_free),
    PySlot_END
};

PyMODEXPORT_FUNC PyModExport_mymod(void) { return mymod_slotarray; }
#else
/* ... the stage-2 PyModuleDef + PyInit_mymod from above ... */
#endif
```

`PyModExport_` must return **only a pointer to static data** — move any pre-return
logic into `Py_mod_create`/`Py_mod_exec`. Leave out fields that were absent, **except
`Py_mod_abi`, which is mandatory**. Only **one** `Py_mod_exec` is allowed (merge
multiple exec functions).

### Consequences you must handle

- **Opaque `PyObject`.** No `->ob_type`/`->ob_refcnt`/`->ob_size` (use `Py_TYPE`,
  `Py_REFCNT`, `Py_SIZE`). Instance size is unknown at compile time.
- **No `PyObject_HEAD` in your struct.** Define **only your extra fields** in a
  separate struct and use a **negative `basicsize`** (extra bytes, not total):

  ```c
  typedef struct { int value; PyObject *name; } FooData;   /* NOT castable to PyObject* */
  static PyType_Spec Foo_spec = { .basicsize = -sizeof(FooData), /* ... */ };
  /* access: FooData *d = PyObject_GetTypeData(obj, cls); */
  ```
  With `Py_tp_members`, set `Py_RELATIVE_OFFSET` and give offsets into `FooData`.
- **No `PyModuleDef`.** `PyModule_GetDef` / `PyType_GetModuleByDef` don't apply; give
  the module a **token** (`Py_mod_token`, a `static char`) and use
  `PyModule_GetToken` / `PyType_GetModuleByToken` to identify "your" module.
- **No build-time version assumptions.** Runtime version → `Py_Version`; available
  API → `Py_TARGET_ABI3T`. `Py_GIL_DISABLED` is *always* defined under abi3t (the GIL
  may still be enabled at runtime), so **don't gate thread-safety on it** — abi3t
  code must be genuinely thread-safe.

### Hard limitations

- **Variable-size types can't be ported to abi3t 3.15** — if you use `tp_itemsize` /
  `Py_tp_itemsize`, ship `abi3` + a version-specific `cp3XYt` wheel instead.
- Prerequisites: already `abi3`-clean, multi-phase init, module isolation. Backward
  `#ifdef Py_TARGET_ABI3T` compatibility is reasonable down to **3.12** (PEP 697).
