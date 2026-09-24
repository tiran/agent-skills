# Skill: port a C/C++ extension to the limited API / stable ABI

Port a **hand-written** CPython C/C++ extension (written directly against `Python.h`)
from the full, version-specific C API to the **Limited API**, so it builds one
**`abi3`** wheel per platform that loads on that Python **and every later one** —
instead of a fresh `cpXY` wheel every release. Optionally then target **Python 3.15
`abi3t`** (PEP 803 + PEP 793 `PyModExport`) for a single wheel that *also* covers the
free-threaded build. The usual first and largest step is converting static
`PyTypeObject` types to **heap types**; the skill also covers module state, multi-phase
init, API substitutions, and the build flags / wheel tags. The content is
framework-neutral Markdown; the same files drive multiple coding agents.

## Why do this (and why not)

**Payoff.** One wheel per platform, forward-compatible: an `abi3` wheel built at the
3.12 floor imports on 3.12 and every later CPython with **no rebuild**, so the
build/CI/PyPI matrix shrinks and users get a working wheel on a brand-new Python on
day one (`cryptography` ships a single `cp311-abi3` wheel, not one per version).
`abi3t` extends that to free-threaded CPython from 3.15.

**Performance.** The limited API is a **subset**: fast layout-dependent macros
(`PyList_GET_ITEM`, `PyTuple_GET_ITEM`, direct struct-field access) are unavailable, so
you call functions that add a bounds check and a real call the macro skipped. The hit
depends entirely on the workload — Cython measured roughly an **18–33 % speed-up under
the limited API vs. ~38 % with the full API** on object-heavy code, while C-heavy code
that rarely touches Python objects barely notices. In hot loops the usual mitigation
is to hoist a length or fetch once instead of per-iteration. Measure your own hot
paths before assuming the cost is acceptable (or negligible).

**Other costs.** The port is a genuine refactor (heap types, module state, multi-phase
init), not a flag flip. `abi3t` is a **hard 3.15 boundary**: source- and
binary-incompatible with ≤3.14 and unable to wrap variable-size types.
`Py_LIMITED_API` guards *definitions only*, so you must **test on every version you
claim**. Full analysis, the ABI/wheel-tag model, and a transition plan are in
[`reference/background.md`](reference/background.md).

**When _not_ to reach for this skill.** For **pybind11**, migrate to nanobind instead
(pybind11 isn't limited-API-compatible) via
[`pybind11-to-nanobind`](../pybind11-to-nanobind/); for the **PyTorch C++ ABI** (a
different "stable ABI") use [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/).
**Cython and Rust/PyO3** projects don't need the hand port — their generators emit
limited-API-safe code, so it's a build-flag change (the skill covers that path too).
Making an extension genuinely **thread-safe** for free-threading is a separate
concern; this skill covers only the `Py_mod_gil` declaration and the `abi3t` tag.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 9 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/background.md` | API vs ABI, the three ABIs + wheel tags, benefits/drawbacks — the "why". |
| `reference/heap-types.md` | Static `PyTypeObject` → heap type (`PyType_FromSpec`/`PyType_Slot`), GC rules, module state. |
| `reference/module-init.md` | Single-phase → multi-phase init → `PyModExport` (abi3t). |
| `reference/api-substitutions.md` | Non-limited → limited API swap tables + the "not in the limited API" cases. |
| `reference/build-systems.md` | `Py_LIMITED_API` / `Py_TARGET_ABI3T` flags + `abi3` / `abi3.abi3t` tags for meson-python, scikit-build-core, maturin, setuptools (+ Cython). |

`SKILL.md` and `AGENTS.md` point at the same `reference/` files; only `SKILL.md`
carries the full step list, so there is no duplicated workflow to maintain.

## Related

- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — the abi3 route for a **pybind11**
  extension (migrate to nanobind rather than hand-porting).
- [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — the **PyTorch** C++
  stable ABI, plus its own abi3 assessment.
- [`choose-python-build-backend`](../choose-python-build-backend/) — picks the backend
  whose flags this skill sets.

## Further reading

- CPython [C API Stability](https://docs.python.org/3/c-api/stable.html) ·
  [Isolating Extension Modules](https://docs.python.org/3/howto/isolating-extensions.html)
  ([PEP 630](https://peps.python.org/pep-0630/)) ·
  [abi3t migration how-to](https://docs.python.org/3.15/howto/abi3t-migration.html)
  ([PEP 793](https://peps.python.org/pep-0793/) / [PEP 803](https://peps.python.org/pep-0803/)).
- [Quansight, *What Every Python Developer Should Know About the CPython ABI*](https://labs.quansight.org/blog/python-abi-abi3t) — the overview this skill's background draws on.
- Deterministic tooling: [`pythoncapi-compat`](https://github.com/python/pythoncapi-compat)
  (back-fills modern C API + `upgrade_pythoncapi.py`) and
  [`abi3audit`](https://github.com/pypa/abi3audit) (verifies a `.so`/wheel is abi3-clean).

See the repository [`README.md`](../../README.md) for per-agent setup (Claude Code,
Codex, and others).
