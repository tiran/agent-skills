# Background: the ABIs, wheel tags, and the benefit/drawback call

The "why" behind the port — read when you need rationale, are deciding whether it's
worth it, or need to explain a wheel tag. Grounded in the CPython C-API stability
docs and Quansight's *What Every Python Developer Should Know About the CPython ABI*
(<https://labs.quansight.org/blog/python-abi-abi3t>).

## API vs ABI

- **API** (Application *Programming* Interface) — the source-level contract in
  `Python.h`: function signatures, macros, typedefs, inline functions. What you
  compile against.
- **ABI** (Application *Binary* Interface) — the binary contract: exported symbol
  names, struct sizes/field offsets, calling conventions. What a compiled `.so`
  actually depends on at load time.

The gap matters because macros and `static inline` functions live only in the API —
they bake struct offsets into *your* binary at compile time. `PyList_GET_ITEM(o, i)`
reads a field at a fixed offset; if that layout changes in a later CPython, your
prebuilt `.so` reads the wrong bytes. The limited API removes exactly these
layout-dependent shortcuts so a binary can outlive the CPython it was built on.

## The three CPython ABIs (and their wheel tags)

| ABI | Wheel tag | Build once? | Covers |
| --- | --- | :-: | --- |
| Version-specific (GIL) | `cp313-cp313` | ❌ per release | one CPython minor, GIL build |
| Version-specific (free-threaded) | `cp314-cp314t` | ❌ per release | one CPython minor, free-threaded build |
| **Stable / limited (`abi3`)** | `cp312-abi3` | ✅ | that CPython **and every later GIL build** |
| **Free-threaded stable (`abi3t`)** | `cp315-abi3.abi3t` | ✅ (3.15+) | GIL **and** free-threaded 3.15+ |

- **`cp3XY`** is frozen at that minor's first release candidate and guaranteed only
  within the `3.Y.*` series — so you rebuild every year. NumPy targets this because
  it has the resources to track CPython annually.
- **`abi3`** is the payoff of this skill: symbols in the stable ABI *never* go away,
  so a wheel built against the 3.12 limited API imports on 3.12 and every later
  CPython **with no rebuild**. The `abi3` version in the tag (`cp312`) is the
  **minimum**, not the exact, interpreter.
- **`abi3t`** (PEP 803, new in 3.15) is the stable ABI for the free-threaded build,
  which changed `PyObject`'s layout and so needs its own ABI. Its compatible
  interpreters are a *superset* of `abi3`'s, so the combined **`abi3.abi3t`** tag on
  one `*.abi3t.so` serves both GIL and free-threaded 3.15+.

The `.so` **suffix** encodes the same thing: `foo.cpython-312-x86_64-linux-gnu.so`
(version-specific) vs `foo.abi3.so` (stable) vs `foo.abi3t.so` (free-threaded
stable; loaded by both GIL and free-threaded 3.15+). CPython does **not** verify the
tag — see `abi3audit` in the SKILL's tooling note.

## Why free-threading forced a new ABI

Through 3.11, `PyObject` was `{ Py_ssize_t ob_refcnt; PyTypeObject *ob_type; }` — a
GIL serialized every refcount change. The free-threaded build (PEP 703) replaced
that with biased reference counting and a per-object lock, so on 3.15 the struct is
larger and `ob_type` **moved offset**:

```c
struct PyObject {              // free-threaded 3.15
    uintptr_t   ob_tid;
    uint16_t    ob_flags;
    PyMutex     ob_mutex;
    uint8_t     ob_gc_bits;
    uint32_t    ob_ref_local;
    Py_ssize_t  ob_ref_shared;
    PyTypeObject *ob_type;     // no longer at offset 8
};
```

An extension compiled against the old layout reads `ob_type` at the wrong offset →
crash or silent corruption. That's why existing `abi3` wheels won't load on
free-threaded builds, and why `abi3t` makes `PyObject` **opaque** (accessed only
through functions), which in turn forces the PyModExport module-init change (step 7).

## Benefits

- **One wheel per platform, forever forward.** No annual rebuild for new CPython;
  new releases "just work."
- **Smaller everything** — build matrix, CI time, PyPI upload count, wheel storage.
  `cryptography` ships a single `cp311-abi3` wheel instead of one per version.
- **Faster ecosystem support** — users get a working wheel on a brand-new CPython on
  day one, without waiting for the project to cut a release.
- **`abi3t`** extends all of the above to free-threaded Python from 3.15.

## Drawbacks / costs

- **The limited API is a subset.** Fast layout-dependent macros
  (`PyList_GET_ITEM`, direct field access) are unavailable; you call functions
  instead. Cython measured roughly an 18–33 % speed-up under the limited API vs 38 %
  with the full API on object-heavy code — a real but usually modest hit; C-heavy
  code barely notices.
- **The port is a genuine refactor** — static→heap types, module state, multi-phase
  init. Days, not minutes, for a non-trivial extension.
- **Not a complete guarantee.** `Py_LIMITED_API` only covers *definitions*; it won't
  catch passing `NULL` where an older version dereferences it, and a few struct
  fields/private symbols leak through. **Test on every version you claim.**
- **`abi3t` is a hard boundary.** It requires 3.15 APIs (`PyModExport`, opaque
  `PyObject`), is source- *and* binary-incompatible with ≤3.14, and **cannot** wrap
  variable-size types (`tp_itemsize`). Single-source with `abi3` is reasonable only
  down to 3.12.
- **Not universal.** PyPy and GraalPy don't support the limited API; pybind11 is
  incompatible (use nanobind). Tooling for `abi3t` was still maturing as of mid-2026.

## Transition strategy (Quansight's recommendation)

If you already ship `abi3` wheels and want free-threading now, ship **three**
artifacts per release during the transition, then collapse back to one once 3.15 is
your minimum:

| CPython | Non-free-threaded | Free-threaded |
| --- | --- | --- |
| 3.12 | `cp312-abi3` | — |
| 3.14 | — | `cp314t` |
| 3.15+ | `cp315-abi3.abi3t` | (same wheel) |

## What real projects do (top-PyPI survey, Sept 2026)

A scan of the top 360 PyPI packages: **17 ship an `abi3` wheel**, 64 more ship
compiled-but-version-specific extensions, the rest are pure Python. Adopters (with
their floor): psutil `cp36`; charset-normalizer, pycryptodome `cp37`; bcrypt, pynacl,
hf-xet `cp38`; cython, tornado `cp39`; protobuf, litellm, watchfiles, tokenizers,
safetensors, pymupdf, wcwidth `cp310`; cryptography `cp311`; pyzmq `cp312`. Patterns
worth copying:

- **Rust/PyO3 dominates** (7 of 17) — for PyO3, abi3 is one Cargo feature
  (`abi3-py310`), so those projects adopt it almost for free. Hand-written C
  (psutil, pymupdf, pycryptodome, protobuf's C++) is the harder path this skill is
  written for.
- **Pick a low floor.** psutil at `cp36` and charset-normalizer/pycryptodome at
  `cp37` get one wheel spanning many years; the floor is the *minimum*, so lower =
  more reach, bounded only by the C API you need.
- **Ship a pure-Python fallback alongside abi3** when a pure implementation exists.
  protobuf ships `cp310-abi3` **and** a `py3-none-any` wheel; wcwidth's C extension
  falls back to pure Python if compilation is unavailable. Install then succeeds even
  where no binary matches.
- **Free-threading is two wheel families today.** Until 3.15's `abi3t`, projects that
  want both ship `cpXX-abi3` for GIL builds *plus* version-specific `cp313t`/`cp314t`
  wheels (cryptography, bcrypt, pynacl, charset-normalizer do exactly this) — the
  transition table above, in the wild.
- **Code generators reach abi3 without hand-editing output** — cython (self-hosted, C)
  and charset-normalizer (mypyc) flip the generator's limited-API switch.

Empirically these hold up: `abi3audit` on a sample of them (cryptography, protobuf,
cython, pyzmq, tokenizers, psutil, bcrypt, charset-normalizer, hf-xet, watchfiles)
found **zero** violations — the top adopters tag honestly.

## Verify the artifact, not the tag

Step 9's discipline — inspect the built wheel, run `abi3audit`, read the sdist — is
also how you tell a legitimate pure→compiled transition from a supply-chain attack.
When wcwidth (long a *pure-Python* library) suddenly shipped `cp310-abi3` binaries at
a version far above its previous release, all uploaded the same day, that matched an
account-takeover profile on the surface. The artifact evidence cleared it: the sdist
carried a coherent C library with its own test suite, the shipped Python had no
obfuscation or network calls, the author was unchanged, `abi3audit` passed, and a
public commit documented the C-extension rewrite. The `abi3` tag alone proves
nothing about *what* is in the binary — only the audit and the source do.
