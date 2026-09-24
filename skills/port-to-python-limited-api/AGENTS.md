# AGENTS.md — port-to-python-limited-api

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both share
the same content and reference files, so there is nothing to keep in sync here.

## When to use

A project ships a **hand-written** C/C++ CPython extension (written directly against
`Python.h`) and you are asked to adopt the **limited API / stable ABI** — build one
`abi3` wheel that loads on every later Python instead of one per version — and/or to
target **Python 3.15 `abi3t`** (PEP 803 + PEP 793 `PyModExport`) for a single wheel
covering GIL-enabled and free-threaded builds. Also the right skill when the ask is
narrower: "convert these static types to heap types."

**Not** for pybind11/nanobind (use
[`pybind11-to-nanobind`](../pybind11-to-nanobind/SKILL.md)) or the PyTorch C++ ABI
(use [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/SKILL.md)). Cython and
PyO3 have their own limited-API support, so for those it's mostly a build flag.

## How to run it

1. Read **`SKILL.md`** in this directory — the ordered 9-step workflow. Follow it top
   to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/heap-types.md` — static `PyTypeObject` → heap type + module state.
   - `reference/module-init.md` — multi-phase init → `PyModExport` (abi3t).
   - `reference/api-substitutions.md` — non-limited → limited API swaps.
   - `reference/refleak-detection.md` — hunting reference leaks the swaps introduce
     (standard and debug builds).
   - `reference/build-systems.md` — flags + wheel tags for meson-python,
     scikit-build-core, maturin, setuptools (+ Cython).
   - `reference/background.md` — the ABI/wheel-tag model and the benefit/drawback
     call (the "why").

## Definition of done

Builds with `Py_LIMITED_API` / `Py_TARGET_ABI3T` at the chosen floor; the wheel
carries the `abi3` (or `abi3.abi3t`) tag and the `.so` is `*.abi3.so` / `*.abi3t.so`;
`abi3audit` finds no violations; and it imports and passes tests on every claimed
Python version — including a free-threaded build for `abi3t`.
