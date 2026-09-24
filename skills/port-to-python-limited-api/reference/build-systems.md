# Build systems: limited-API flags and wheel tags

SKILL step 8. Two things must line up: the **compile define**
(`Py_LIMITED_API` / `Py_TARGET_ABI3T`) that actually restricts the API, and the
**wheel/`.so` tag** (`abi3` / `abi3.abi3t`) that advertises it. `abi3audit`
(step 9) exists precisely because nothing enforces that these agree — a wheel can be
tagged `abi3` while compiled against the full API. Keep the floor hex, the tag, and
`requires-python` consistent. Examples use a **3.12** floor (`0x030C0000`).

## meson-python

Meson sets the define and the tag from one argument:

```python
py.extension_module(
    '_mymod',
    'src/mymod.c',
    limited_api: '3.12',        # defines Py_LIMITED_API=0x030C0000 and tags the wheel abi3
    install: true,
)
```

- Produces `_mymod.abi3.so` and a `cp312-abi3` wheel.
- **abi3t:** meson-python support merged (ships in a recent release); it emits the
  `abi3.abi3t` tag when building for 3.15t. Check your installed meson-python version.

## scikit-build-core

Set the wheel API level in `pyproject.toml`; scikit-build-core passes the define to
CMake:

```toml
[tool.scikit-build]
wheel.py-api = "cp312"            # abi3, floor 3.12
# wheel.py-api = "cp315.cp315t"  # combined abi3.abi3t (needs scikit-build-core 1.0 + CMake >= 4.4)
```

In `CMakeLists.txt`, use the SABI-aware target so CMake names the artifact and sets
the macro:

```cmake
python_add_library(_mymod MODULE src/mymod.c USE_SABI 3.12 WITH_SOABI)
```

(or set `target_compile_definitions(_mymod PRIVATE Py_LIMITED_API=0x030C0000)`
manually). scikit-build-core 1.0 added abi3t support.

## maturin (PyO3 / Rust)

abi3 is a **PyO3 Cargo feature**, not a pyproject key:

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.29", features = ["abi3-py312", "abi3t-py315"] }
```

- `abi3-py312` → a `cp312-abi3` wheel for GIL-enabled 3.12+.
- `abi3t-py315` → a wheel for free-threaded/GIL 3.15+ (`abi3t`).
- **One build emits at most one ABI family.** To ship both, build once per
  interpreter: `maturin build -i python3.12` and `maturin build -i python3.15t`.
- Free-threaded 3.14 has no abi3t, so maturin falls back to a version-specific
  `cp314-cp314t` wheel there.
- This skill is for hand-written C extensions; for a Rust extension the whole port is
  really "add the feature," so the primary reference is maturin itself
  (<https://www.maturin.rs/bindings.html>).

## setuptools

Two independent knobs — the compile define **and** the wheel tag — which is exactly
the split abi3audit warns about:

```python
# setup.py
from setuptools import setup, Extension

ext = Extension(
    "mymod._mymod",
    ["src/mymod.c"],
    py_limited_api=True,  # name the .so *.abi3.so
    define_macros=[("Py_LIMITED_API", "0x030C0000")],  # actually restrict the API
)
setup(ext_modules=[ext], options={"bdist_wheel": {"py_limited_api": "cp312"}})
```

- All three (`py_limited_api`, the `Py_LIMITED_API` macro, and the `bdist_wheel`
  tag) must agree, or you get a mistagged wheel.
- **abi3t:** setuptools support was pending (PR #5193) as of mid-2026 — check whether
  your setuptools release has it before promising an `abi3.abi3t` wheel from
  setuptools.
- In `pyproject.toml` set `requires-python = ">=3.12"`.

## Cython

Cython is a code generator; you enable the limited API on the generated C:

```python
# meson
py.extension_module('_mymod', cython_gen.process('mymod.pyx'), limited_api: '3.12')
```

or the setuptools `Extension(..., py_limited_api=True, define_macros=[("Py_LIMITED_API",
"0x030C0000")])` pair. Requires **Cython 3.1+**. Caveats: `cdef` classes can't inherit
from builtins; profiling/line-tracing unavailable; typed memoryviews need a 3.11
floor. **For abi3t, wait for a released Cython that supports it** (experimental branch
as of mid-2026) rather than editing generated C by hand — the same advice applies to
any code generator.

## Cross-check

After building, confirm the pieces agree:

```bash
uv build
ls dist/                       # expect *-cp312-abi3-*.whl  (or *-cp315-abi3.abi3t-*.whl)
uvx abi3audit dist/*.whl       # fails if a symbol is newer than the declared floor
```
