# Static → heap types, and module state

The core of the port (SKILL steps 3–4). A statically-declared `PyTypeObject` bakes
the type's layout into your binary and can't be compiled under `Py_LIMITED_API`; the
limited API instead builds types at runtime from a `PyType_Spec` + `PyType_Slot[]`.
Canonical guide: the CPython **Isolating Extension Modules** HOWTO
(<https://docs.python.org/3/howto/isolating-extensions.html>) + PEP 630, and the
type-objects reference (<https://docs.python.org/3/c-api/type.html>). There is **no**
automatic static→heap rewriter — this is a guided manual edit.

## Field → slot mapping

A `PyType_Spec` carries `name`, `basicsize`, `itemsize`, `flags`; **everything else**
moves into the `PyType_Slot[]` array, keyed by `Py_tp_*` / `Py_nb_*` / `Py_sq_*` /
`Py_mp_*` IDs (the `PyTypeObject`/number/sequence/mapping field names with a `Py_`
prefix).

| Static `PyTypeObject` field | Heap-type home |
| --- | --- |
| `tp_name` | `PyType_Spec.name` (fully-qualified, `"pkg.mod.Type"`) |
| `tp_basicsize` / `tp_itemsize` | `PyType_Spec.basicsize` / `.itemsize` |
| `tp_flags` | `PyType_Spec.flags` |
| `tp_new` / `tp_init` / `tp_dealloc` | `Py_tp_new` / `Py_tp_init` / `Py_tp_dealloc` |
| `tp_methods` / `tp_members` / `tp_getset` | `Py_tp_methods` / `Py_tp_members` / `Py_tp_getset` |
| `tp_doc` | `Py_tp_doc` (static C string) |
| `tp_str` / `tp_repr` / `tp_richcompare` | `Py_tp_str` / `Py_tp_repr` / `Py_tp_richcompare` |
| `tp_traverse` / `tp_clear` | `Py_tp_traverse` / `Py_tp_clear` |
| `tp_base` / `tp_bases` | **bases arg** of `PyType_FromModuleAndSpec` (avoid `Py_tp_bases`) |
| `tp_as_number->nb_add`, … | `Py_nb_add`, … (flattened, no sub-struct) |

**Cannot be set** on a heap type: `tp_dict`, `tp_mro`, `tp_cache`, `tp_subclasses`,
`tp_weaklist` (CPython manages them).

## Before → after

Static (old):

```c
typedef struct { PyObject_HEAD int value; PyObject *name; } FooObject;

static PyTypeObject FooType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mymod.Foo",
    .tp_basicsize = sizeof(FooObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = Foo_new,
    .tp_dealloc = (destructor)Foo_dealloc,
    .tp_members = Foo_members,
    .tp_methods = Foo_methods,
    .tp_doc = "Foo objects",
};
/* in module init: PyType_Ready(&FooType); Py_INCREF(&FooType);
   PyModule_AddObject(m, "Foo", (PyObject *)&FooType); */
```

Heap (limited API):

```c
static PyType_Slot Foo_slots[] = {
    {Py_tp_doc,      (char *)"Foo objects"},
    {Py_tp_new,      Foo_new},
    {Py_tp_dealloc,  Foo_dealloc},
    {Py_tp_traverse, Foo_traverse},   /* required: heap types are GC types */
    {Py_tp_clear,    Foo_clear},
    {Py_tp_members,  Foo_members},
    {Py_tp_methods,  Foo_methods},
    {0, NULL},
};

static PyType_Spec Foo_spec = {
    .name = "mymod.Foo",
    .basicsize = sizeof(FooObject),   /* positive; PyObject_HEAD stays (abi3) */
    .itemsize = 0,
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .slots = Foo_slots,
};

/* in the Py_mod_exec function (step 6): */
PyObject *foo = PyType_FromModuleAndSpec(module, &Foo_spec, /*bases=*/NULL);
if (foo == NULL) return -1;
mystate *st = PyModule_GetState(module);
st->FooType = (PyTypeObject *)foo;                 /* keep a strong ref in state */
if (PyModule_AddObjectRef(module, "Foo", foo) < 0) return -1;
```

- `PyType_FromModuleAndSpec` (3.9+) links the type to its **defining module**, which
  is what makes `PyType_GetModuleState` work in methods. `PyType_FromSpec` (3.3+)
  exists for a lower floor but gives no module link.
- `PyType_FromSpecWithBases` sets `Py_TPFLAGS_HEAPTYPE` for you; pass bases via the
  argument, never `Py_tp_bases`.

## Heap types are GC types — the rules that bite

Every heap-type instance holds a strong reference to its type object, so the type
participates in reference cycles. This is mandatory, not optional:

1. **Set `Py_TPFLAGS_HAVE_GC`** in `spec.flags`.
2. **`tp_traverse` must visit the type:**

   ```c
   static int Foo_traverse(PyObject *op, visitproc visit, void *arg) {
       Py_VISIT(Py_TYPE(op));            /* the heap-type-specific line */
       FooObject *self = (FooObject *)op;
       Py_VISIT(self->name);
       return 0;
   }
   ```
   Args **must** be named `visit`/`arg` for `Py_VISIT`. (Guard `Py_VISIT(Py_TYPE(op))`
   with `#if PY_VERSION_HEX >= 0x03090000` only if your floor is below 3.9.)
3. **`tp_dealloc` must untrack, then decref the type:**

   ```c
   static void Foo_dealloc(PyObject *op) {
       PyTypeObject *tp = Py_TYPE(op);
       PyObject_GC_UnTrack(op);
       FooObject *self = (FooObject *)op;
       Py_CLEAR(self->name);
       freefunc free = PyType_GetSlot(tp, Py_tp_free);
       free(op);
       Py_DECREF(tp);                    /* static types never do this; heap types must */
   }
   ```

Skipping the `Py_VISIT(Py_TYPE)`/`Py_DECREF(tp)` pair is the classic heap-type
memory leak.

## Module state (SKILL step 4)

Static types and C globals are shared across sub-interpreters and block clean
isolation. Move them into per-module state:

```c
typedef struct { PyTypeObject *FooType; PyObject *cached_str; } mystate;
/* def.m_size = sizeof(mystate);  (or Py_mod_state_size under PyModExport) */
```

Retrieve it:

- **From module-level code** (e.g. the exec function): `mystate *st =
  PyModule_GetState(module);`
- **From a method of a heap type**: `mystate *st = PyType_GetModuleState(cls);` where
  `cls` is the defining class. Get `cls` via a `PyCMethod` (`METH_METHOD`) signature,
  or `PyType_GetModuleByToken` (abi3t / no `PyModuleDef`; see `module-init.md`), or
  `PyType_GetModule(Py_TYPE(self))` for a non-subclassable type.

Never cache a heap type in a `static PyObject *` — that reintroduces the global you
just removed and breaks sub-interpreter isolation.
