# Stubs for compiled extensions

Type checkers **do not import compiled modules** — a C/C++/Cython/Rust extension types
as `Any` for every consumer until you ship a `.pyi` stub beside it. Pick the generator
that matches the binding; generated stubs are **drafts** — patch and verify them
(`stubtest`, step 5). Pin the generator **and** Python version: output formatting
changes between releases, which breaks the CI freshness gate.

## Pick the generator by binding

### nanobind — best fidelity
nanobind functions expose a structured `__nb_signature__` (typed signatures, overload
chains, defaults), so its stubgen produces high-quality stubs without docstring
parsing. Wire it into the CMake build so stubs regenerate from the installed module:

```cmake
nanobind_add_stub(
  my_ext_stub
  MODULE my_ext
  OUTPUT my_ext.pyi
  PYTHON_PATH $<TARGET_FILE_DIR:my_ext>
  DEPENDS my_ext
  MARKER_FILE py.typed          # also emits the PEP 561 marker
)
```

Extensions with import side effects (GPU init, etc.) can skip them: stubgen sets
`NB_STUBGEN=1` in the environment. **Full nanobind stub guidance lives in
[`pybind11-to-nanobind`](../../pybind11-to-nanobind/SKILL.md)** — defer there; this
skill just places the result and verifies it.

### pybind11
```bash
uvx pybind11-stubgen my_ext -o src
```
Works on other bindings too, but infers signatures from docstrings (brittler than
nanobind's structured data). Review overloads and container types.

### Rust / PyO3
Use **`pyo3-stub-gen`** (a crate + small generator binary you add to the project) to
emit `.pyi` from the `#[pyfunction]`/`#[pyclass]` definitions. See its docs; wire the
generator into the build like the nanobind case.

### Cython
Annotate the `.pyx`/`.pxd` with **PEP 484 annotations as the single source of truth**
(Cython 3 reads them), then generate stubs from the *source*. `stubgen-pyx` parses
Cython directly — preserving your annotations, `cdef`/`cpdef`/`cdef class`/memoryviews,
and normalizing Cython types (`bint`→`bool`, `unicode`→`str`):

```cython
# geom.pyx
def scale(data: list[int], factor: float = 1.0) -> list[int]:
    return [int(x * factor) for x in data]

cdef class Point:
    cdef public int x, y
    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y
    cpdef double norm(self):            # bint/int/double normalized in the stub
        return (self.x * self.x + self.y * self.y) ** 0.5
```
```bash
uvx stubgen-pyx . --output-dir src     # writes geom.pyi from the source
```
producing `geom.pyi`:
```python
class Point:
    x: int
    y: int

    def __init__(self, x: int, y: int) -> None: ...
    def norm(self) -> float: ...


def scale(data: list[int], factor: float = ...) -> list[int]: ...
```
Cython's own stub output (the `write_stub_file` directive / `PyiWriter`) is maturing but
still incomplete (e.g. return types). `mypy stubgen` on the *built* module also works but
loses Cython source metadata (most types become `Any`).

### Hand-written C / any other binding — fallback
`mypy`'s `stubgen` runtime-introspects the imported module:
```bash
uvx --from mypy stubgen -m my_ext -o src        # or: -p my_pkg
```
Most types default to `Any` — treat it as scaffolding and annotate the common surface by
hand (helped by `__text_signature__`, below).

## Hand-written C: expose `__text_signature__`

Introspection tools (including `stubgen`) recover a function's signature from its
`__text_signature__`. For a raw C extension, put a signature line at the top of the
method's docstring — CPython parses it into `__text_signature__`:
```c
PyDoc_STRVAR(add_doc, "add(x, y, /)\n--\n\nReturn x + y.");
static PyObject *add(PyObject *self, PyObject *args) { /* ... */ }
static PyMethodDef mymod_methods[] = {
    {"add", add, METH_VARARGS, add_doc},
    {NULL, NULL, 0, NULL},
};
```
The `"add(x, y, /)\n--\n\n"` prefix makes `add.__text_signature__ == "(x, y, /)"`, so
`stubgen` recovers the parameter names and the positional-only `/` (not the types). Ship
a hand-written `.pyi` for the real Python types:
```python
# mymod.pyi
def add(x: int, y: int, /) -> int: ...
```

> CPython's **Argument Clinic** generates `__text_signature__` (and the `PyArg_Parse*`
> boilerplate) from a DSL — which is why stdlib C functions introspect well — but it is a
> **CPython-internal tool, not packaged or supported for third-party use**. For your own
> extension, write the docstring signature by hand as above rather than adopting Clinic.

## Patch what generators can't express

Generated stubs miss things. Fix with nanobind **pattern files** (a DSL of
replacement rules passed to `nanobind_add_stub`; first matching rule wins) or by hand:

- `@overload` chains keyed on argument type.
- widening a `tuple` param that also accepts a list/sequence.
- getters that return `None` when unset (`-> X | None`).
- generated `__version__` / build-timestamp lines that shouldn't be typed as literals.

## Placement

Commit the `.pyi` **beside** the module (`src/<pkg>/my_ext.pyi` next to `my_ext.*.so`)
with a `py.typed` marker in the package — checkers read adjacent stubs only when
`py.typed` is present. Use a separate `<pkg>-stubs` distribution only when the stubs
must ship apart (step 4 / `reference/verify-and-ship.md`).

## CI freshness gate

Committed stubs drift from the code. In CI, regenerate and fail on any diff:

```bash
# regenerate into a temp dir, then diff against the committed .pyi
cmake --build build --target my_ext_stub        # nanobind
git diff --exit-code -- 'src/**/*.pyi'
```

Pin the generator + Python version (and skip the comparison under a mismatched version
rather than churn). `stubtest` (step 5) is the complementary check that stubs match the
*runtime* module, not just that they haven't changed.
