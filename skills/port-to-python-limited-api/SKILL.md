---
name: port-to-python-limited-api
description: >-
  Port a hand-written C/C++ CPython extension from the version-specific C API to
  the Limited API (Py_LIMITED_API) so one stable-ABI abi3 wheel loads on every
  later Python instead of one per version — and optionally target Python 3.15 abi3t
  (PEP 803 + PEP 793 PyModExport) for a single wheel across GIL-enabled and
  free-threaded builds. Covers the usual first step of converting static
  PyTypeObject types to heap types (PyType_FromSpec / PyType_Slot), module state,
  multi-phase init, API substitutions, and the build flags / abi3 / abi3.abi3t wheel
  tags for meson-python, scikit-build-core, maturin, and setuptools. Use to adopt
  the limited API / stable ABI / abi3 / abi3t, stop rebuilding a C extension per
  Python version, or convert static types to heap types. Not for pybind11/nanobind
  (see pybind11-to-nanobind) or the PyTorch C++ ABI (see port-to-torch-stable-abi).
---

# Port a C/C++ extension to the limited API / stable ABI

**Status: Experimental** — grounded in the CPython C-API docs and the PEP 803 / 793
texts (linked below), but the packaged workflow is a new draft: review the diff and
the built wheels, and test on every Python version you claim.

Convert a **hand-written** CPython C/C++ extension from the version-specific API (a
new `cpXY` wheel per release) to the **Limited API**, so one `abi3` wheel per platform
loads on that Python and every later one. Optionally then target **3.15 `abi3t`** for
a single wheel that also covers the free-threaded build. Work the steps in order; each
cites the reference holding its code and tables.

**Scope.** Extensions written directly against `Python.h`. **Not** pybind11 (not
limited-API-compatible — migrate to nanobind via
[`pybind11-to-nanobind`](../pybind11-to-nanobind/SKILL.md)) or the PyTorch C++ ABI
([`port-to-torch-stable-abi`](../port-to-torch-stable-abi/SKILL.md)). Cython/PyO3
projects take the *Code-generator* short path below (a build flag, not a hand port).

**Why (and why not).** Payoff: a smaller build/CI/PyPI matrix and forward
compatibility — an `abi3` wheel built at the 3.12 floor imports on 3.12 and every
later CPython with no rebuild; `abi3t` extends that to free-threaded 3.15+. Cost: the
limited API is a **subset** (fast macros like `PyList_GET_ITEM` are gone, a modest
perf hit) and the port is a real refactor (heap types, module state, multi-phase
init); `abi3t` is a hard 3.15 boundary with no variable-size types. Full analysis and
the ABI/wheel-tag model: `reference/background.md` — read it first if the port isn't
yet decided.

**References — open each only at the step that cites it:**

- `background.md` — API vs ABI, the three ABIs + wheel tags, benefits/drawbacks.
- `heap-types.md` (steps 3–4) — static `PyTypeObject` → heap type, GC rules, state.
- `module-init.md` (steps 6–7) — single- → multi-phase init → `PyModExport` (abi3t).
- `api-substitutions.md` (step 5) — non-limited → limited swaps; what's not in abi3.
- `build-systems.md` (step 8) — flags + `abi3` / `abi3.abi3t` tags per backend.

**Deterministic tooling** (offer in step 1; don't hand-edit what they automate):

- **[`pythoncapi-compat`](https://github.com/python/pythoncapi-compat)** — a header
  that back-fills modern C API onto old Pythons + `upgrade_pythoncapi.py`, which
  rewrites source to use it (step 5). Lets one source compile from a low floor up;
  regex-based, so review its diff.
- **[`abi3audit`](https://github.com/pypa/abi3audit)** — verifies a `.so`/wheel is
  actually abi3-clean (step 9); nothing in pip/CPython enforces the tag.

There is **no** automatic static→heap rewriter — step 3 is a guided manual edit.

**Authoritative sources** (they win over this skill):

- [C API Stability](https://docs.python.org/3/c-api/stable.html) and
  [type objects](https://docs.python.org/3/c-api/type.html) — the API reference.
- [Isolating Extension Modules](https://docs.python.org/3/howto/isolating-extensions.html)
  + [PEP 630](https://peps.python.org/pep-0630/) — static→heap + state (steps 3–4, 6).
- [abi3t migration how-to](https://docs.python.org/3.15/howto/abi3t-migration.html),
  [PEP 793](https://peps.python.org/pep-0793/), [PEP 803](https://peps.python.org/pep-0803/) — abi3t (step 7).
- [Quansight, *the CPython ABI*](https://labs.quansight.org/blog/python-abi-abi3t) — the overview.

**Definition of done:** builds with `Py_LIMITED_API` (or `Py_TARGET_ABI3T`) at the
chosen floor; the wheel carries the `abi3` (or `abi3.abi3t`) tag and the `.so` is
`*.abi3.so` / `*.abi3t.so`; `abi3audit` is clean; imports and passes tests on
**every** claimed version — including a free-threaded build for `abi3t`.

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md): check upstream for prior
> work first; work in a project-local `.venv` with **uv**; don't delete content or
> commit/push without approval (never to `main`); match the project's C style.

## 1. Check upstream, then inventory and classify

**Check upstream first** ([`../GUARDRAILS.md`](../GUARDRAILS.md) → *Prior work*): a
limited-API port is a common maintainer project. Find the repo (`git remote -v`,
`[project.urls]`; if a fork, `gh repo view --json parent`) and search issues + PRs for
`limited API`, `Py_LIMITED_API`, `abi3`, `abi3t`, `stable ABI`, `PyType_FromSpec`,
`heap type`, `free-threading`. Report findings before porting.

Then inventory the surface:

```bash
# static types, single-phase init, blockers
grep -rnE 'static PyTypeObject|PyVarObject_HEAD_INIT|PyType_Ready|PyModule_Create|PyInit_' src/ *.c *.cpp 2>/dev/null
# non-limited macros / field access (the refactor surface)
grep -rnE 'PyList_GET_ITEM|PyList_SET_ITEM|PyTuple_GET_ITEM|->ob_type|->ob_refcnt|->ob_size|_Py[A-Z]|tp_print' src/ *.c *.cpp 2>/dev/null
# already-limited? bindings frameworks? (→ other skills)
grep -rnE 'Py_LIMITED_API|Py_TARGET_ABI3T|pybind11|nanobind|Cython|PyO3|cffi' . 2>/dev/null | head
```

Classify and flag blockers:

- **pybind11** → **stop**: not limited-API-compatible; migrate to nanobind
  ([`pybind11-to-nanobind`](../pybind11-to-nanobind/SKILL.md)) or hand-write the types.
- **Cython / PyO3 / cffi** → take the *Code-generator projects* short path (skip
  steps 3–7).
- **Variable-size types** (`tp_itemsize` ≠ 0) → **cannot** target **abi3t** on 3.15;
  plain `abi3` is fine.
- **Private/unstable API** (`_Py*`, `PyUnstable_*`) or heavy struct access → each use
  needs a supported replacement (step 5); note any with no equivalent.

Offer the deterministic tooling now (above): `pythoncapi-compat` for step 5,
`abi3audit` for step 9; the static→heap edit (step 3) is manual.

## 2. Choose the target ABI and floor

Pick **which** stable ABI and the **lowest** Python it must load on — that floor is
the `Py_LIMITED_API` hex and the wheel's `cpXY` tag. The ABIs and tags:
`reference/background.md`. Short version:

- **`abi3` only** — one wheel across GIL-enabled CPython ≥ floor. **Default floor:
  3.12** (`0x030C0000`) — it has vectorcall and the PEP 697 APIs that make heap types
  clean, and is the single-source floor if you later add `abi3t`. The bulk of the work.
- **`abi3` + `abi3t`** — also cover free-threaded builds. `abi3t` is **3.15+ only**;
  its interpreters are a superset of `abi3`'s, so ship the combined **`abi3.abi3t`**
  tag (needs the step-7 PyModExport port). During the transition you typically ship
  three artifacts: `cpXY-abi3` (≤3.14), `cp314t` (free-threaded 3.14),
  `cp315-abi3.abi3t` (3.15+) — table in `reference/background.md`.

**Lower than 3.12 (down to 3.6, even 3.2).** The limited API exists since 3.2, so a
lower `abi3` floor broadens coverage — use `pythoncapi-compat` for modern idioms that
still compile there. Obstacles as you drop: PEP 697 negative-`basicsize`/relative
offsets are **3.12**; `PyType_FromModuleAndSpec` + `PyType_GetModuleState` are **3.9**
(below that, module isolation is clumsier); typed memoryviews **3.11**; vectorcall
**3.12**; `PyModule_AddObjectRef` **3.10** (back-filled). So **3.12 is the clean
recommendation; 3.6 is reachable for plain `abi3`**; `abi3t` single-source is
reasonable only **down to 3.12**. Don't target `abi3t` unless free-threading is wanted
now — it's a hard pre-3.15 boundary.

## Code-generator projects (Cython, PyO3/maturin) — the short path

If the extension is **generated** by Cython or PyO3 rather than hand-written against
`Python.h`, the generator already emits heap types, module state, and multi-phase init
for you — **skip steps 3–7**, do the following, then rejoin at **step 8** (build) and
**step 9** (verify). Full config: `reference/build-systems.md`.

**Cython (3.1+):**

1. Set the floor — `limited_api: '3.12'` (meson) or `py_limited_api=True` +
   `define_macros=[("Py_LIMITED_API", "0x030C0000")]` (setuptools). Cython then emits
   limited-API-safe C and builds heap types from specs internally, so you don't
   hand-port types.
2. Fix the source patterns Cython **can't** support under the limited API: a `cdef
   class` can't inherit from a builtin; profiling / line tracing are unavailable;
   typed memoryviews need a **3.11+** floor; some `cimport cpython` fast paths (e.g.
   direct `array.array` access) don't work. Grep for these and rework them.
3. Accept the perf trade-off (~18–33 % vs ~38 % speed-up).
4. **abi3t** is on an experimental branch (mid-2026) — wait for a released Cython
   rather than editing generated C by hand.

**Rust / maturin (PyO3):**

1. Enable the feature: `pyo3 = { features = ["abi3-py312"] }` (add `"abi3t-py315"` for
   free-threaded 3.15+). PyO3 handles heap types, init, and refcounting for you.
2. Set the interpreter floor and build **once per ABI family** (`maturin build -i
   python3.12`, then `-i python3.15t`) — one build emits at most one family.
3. A few PyO3 APIs are unavailable under abi3 and fail to compile with the feature on,
   so follow the compiler errors. Reference: <https://www.maturin.rs/bindings.html>.

Both still finish at **step 8** (confirm the tag and `.so` suffix) and **step 9**
(`abi3audit` + import/test on every claimed version, incl. free-threaded for `abi3t`).
The rest of the workflow (steps 3–9) is the **hand-written C/C++** path.

## 3. Convert static types to heap types

The largest step: a static `PyTypeObject` uses struct internals the limited API hides,
so each type becomes a **heap type** built from a `PyType_Spec` + `PyType_Slot[]` and
created at runtime with `PyType_FromModuleAndSpec`. Walkthrough, field→slot table, and
code: `reference/heap-types.md`. The traps:

- **Heap types are GC types.** Each instance references its type, so set
  `Py_TPFLAGS_HAVE_GC`, have `tp_traverse` call **`Py_VISIT(Py_TYPE(self))`**, and in
  `tp_dealloc` `PyObject_GC_UnTrack` first then **`Py_DECREF(Py_TYPE(self))`** last.
- **Plain `abi3` stays simple:** the instance struct keeps `PyObject_HEAD`,
  `basicsize` stays positive, member offsets absolute — `PyObject` goes opaque only
  under **abi3t** (step 7). Use `PyType_GetSlot` for an inherited slot you can't name.
- **Store the type in module state** (step 4), never a `static PyObject *`.

## 4. Move globals into module state

Heap types + the limited API push per-module state instead of C globals (also needed
for multi-phase init and subinterpreters). Define a state struct, set `m_size =
sizeof(state)` (or `Py_mod_state_size` under PyModExport), reach it via
`PyModule_GetState(module)`, and inside heap-type methods via `PyType_GetModuleState`
(needs `PyType_FromModuleAndSpec`). Patterns: `reference/heap-types.md`.

## 5. Replace non-limited API usage

**Run `upgrade_pythoncapi.py` first** — it mechanically rewrites `->ob_type` →
`Py_TYPE`, `x == Py_None` → `Py_IsNone`, and similar, and adds `pythoncapi_compat.h`
so the result still compiles on old Pythons. Review the diff, then hand-finish: fast
macros (`PyList_GET_ITEM` → `PyList_GetItem`), remaining field access, `_Py*` private
calls. Full swap table and the "no equivalent" cases: `reference/api-substitutions.md`.
Expect the perf trade-off — the fast macros are gone by design.

## 6. Multi-phase module init

Convert single-phase `PyInit_<name>` (`PyModule_Create`) to **multi-phase**: a
`PyModuleDef` with a `PyModuleDef_Slot[]` (`Py_mod_exec` does the setup; `Py_mod_gil =
Py_MOD_GIL_NOT_USED` under `#ifdef Py_GIL_DISABLED`) and a `PyInit_` that just returns
`PyModuleDef_Init(&def)`. Prerequisite for `abi3t`, good practice regardless.
Before/after: `reference/module-init.md`. Note `Py_mod_gil` is only the *marker* —
making the extension genuinely thread-safe for the free-threaded build is the
separate [`port-to-free-threaded-python`](../port-to-free-threaded-python/) skill.

## 7. (abi3t only) Port to PyModExport for Python 3.15

**Skip unless step 2 chose `abi3t`.** Free-threaded 3.15 makes `PyObject` opaque,
breaking the static `PyModuleDef`. PEP 793 replaces `PyInit_` with
**`PyModExport_<name>`** returning a `PySlot[]` (required `Py_mod_abi` via
`PyABIInfo_VAR`, plus `Py_mod_name` / `_doc` / `_state_size` / `_methods` / `_slots`
and the state traverse/clear/free funcs); build with **`Py_TARGET_ABI3T`**
(`0x030f0000`). Consequences — opaque `PyObject` (separate data struct + **negative
`basicsize`**), no `PyModuleDef` (module **tokens**), no variable-size types — are in
`reference/module-init.md`. Keep the step-6 path under `#else` so one source still
builds `abi3` for ≤3.14.

## 8. Build system: flags and wheel tags

Set the define and emit the right tag / `.so` suffix. Per-backend recipes:
`reference/build-systems.md`. In brief:

- **meson-python** — `py.extension_module(..., limited_api: '3.12')`.
- **scikit-build-core** — `wheel.py-api = "cp312"` (or `"cp315.cp315t"` for abi3t).
- **maturin** (PyO3) — Cargo `abi3-py312` / `abi3t-py315`; one build per ABI family.
- **setuptools** — `Extension(..., py_limited_api=True, define_macros=[("Py_LIMITED_API",
  "0x030C0000")])` + `bdist_wheel py_limited_api="cp312"`.
- **Cython** — `limited_api: '3.12'` or the setuptools pair (Cython 3.1+).

Keep `requires-python` / the build-tool floor in sync with the chosen hex.

## 9. Verify

The limited API covers *definitions only*, so verification is empirical:

1. **abi3 symbol audit** — `uvx abi3audit dist/*.whl` (or on the `.so`); it flags any
   symbol outside the declared floor. Confirm the file is `*.abi3.so` / `*.abi3t.so`,
   not `*.cpython-3XY*.so`. Pass the **original wheel filename** — abi3audit reads the
   ABI tag out of the name, so a renamed wheel (`foo.whl`) makes it error. (`nm -D` +
   [`Quansight/torch-abi-audit`](https://github.com/Quansight/torch-abi-audit) is a
   manual fallback.)
2. **Wheel tag** — `uv build`, check the filename carries `-abi3-` (or `-abi3.abi3t-`),
   and `uvx twine check dist/*`.
3. **Import + tests on every claimed version** — build at the **lowest** floor, then
   import and run the suite on it *and* newer ones; for `abi3t`, include a
   **free-threaded** build. Watch for `NULL`-arg / struct-field pitfalls the define
   misses (`reference/background.md`).
4. **Reference-leak spot check** — several limited-API swaps flip borrowed↔strong
   references (`reference/api-substitutions.md`), so hunt leaks after the port with a
   throwaway check. On a **debug** build, watch `sys.gettotalrefcount()` hold steady
   across a loop (`python -X showrefcount ...`, or `python -m test -R 3:3 test_m`); on
   a **standard** build, diff a `gc` object census or `tracemalloc` snapshot. See
   `reference/refleak-detection.md` for both, a one-harness-fits-both snippet, and
   sanitizers. Run it on the lowest floor and, for `abi3t`, a free-threaded build.
