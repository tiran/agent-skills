# Skill: port a package to free-threaded Python

Take a package to **correct behavior on the free-threaded (no-GIL) CPython build**
(PEP 703; the `cp313t`/`cp314t` "t" ABI) and to **declaring support**, so importing it
doesn't silently switch the GIL back on. For pure Python that's a thread-safety review;
for a C/C++/Cython/pybind11/nanobind/Rust-PyO3 extension it also means fixing data
races and shipping a `cp3Xt` wheel. The content is framework-neutral Markdown; the same
files drive multiple coding agents.

## Why do this (and why not)

**Payoff.** Real multi-core parallelism for threaded Python plus native code, without
the pickling/IPC overhead of multiprocessing. Free-threading is already mainstream: a
Sept 2026 scan of the top 360 PyPI packages found **57 of the 81 that ship compiled
wheels already ship a free-threaded one** (~70%). If you ship an extension without
declaring support, every user on a free-threaded interpreter silently loses the GIL
being disabled — a warning fires and the whole process falls back to serial execution.

**Two separate jobs.** *Declaring support* (`Py_mod_gil` / `PyUnstable_Module_SetGIL`
/ a one-line binding flag) is what stops the GIL re-enabling — cheap, high-impact, and
a no-op on the normal build. *Being race-free* is the real engineering: without the GIL,
code that was "accidentally thread-safe" (shared caches, module globals, borrowed
references) now races. The skill keeps these distinct so you don't ship a declaration
that isn't backed by safe code.

**Scope — detect broadly, fix conservatively.** The skill **detects all unprotected
shared state** and **fixes only the simple, local cases**: borrowed→strong reference
swaps (`PyList_GetItemRef`), a single atomic counter, a self-contained critical section
or small `PyMutex` region, and the support declaration. **Complex shared-state redesign,
structural global→thread-local conversion, and non-reentrant-library locking are out of
scope to fix** — those carry deadlock and performance risk and are the maintainer's
call, so the skill reports them (file:line, why it races, a candidate fix) and stops.

**Costs.** The free-threaded build has ~1–8% single-threaded overhead (the normal GIL
build is unaffected); the thread-safety audit is genuine work; and until Python 3.15's
`abi3t` you ship a **second** wheel per version (`cp3Xt` alongside `cpXY`). Full
rationale, PEP 703 internals, and the detection heuristics are in
[`reference/background.md`](reference/background.md) and
[`reference/thread-safety.md`](reference/thread-safety.md).

**When _not_ to reach for this skill.** The single-wheel **`abi3t`** ABI mechanics
(PEP 803 + PEP 793 `PyModExport`, opaque `PyObject`) belong to
[`port-to-python-limited-api`](../port-to-python-limited-api/) — thread-safety and ABI
stability are orthogonal; run this for the former, that for the latter.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 8 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/background.md` | What free-threading is, PEP 703 internals, detection, the GIL-re-enable trap, cost/benefit, abi3 vs abi3t — the "why". |
| `reference/declaring-support.md` | `Py_mod_gil` / `PyUnstable_Module_SetGIL`, the per-binding declarations (Cython/pybind11/nanobind/PyO3), the trove classifier. |
| `reference/thread-safety.md` | Detection heuristics, the detect-vs-fix scope boundary, borrowed-reference hazards, critical sections / `PyMutex` / atomics, global state and caches. |
| `reference/build-and-test.md` | `cp3Xt` wheels per backend + cibuildwheel; TSan, `pytest-run-parallel`, running the GIL-disabled interpreter. |

`SKILL.md` and `AGENTS.md` point at the same `reference/` files; only `SKILL.md`
carries the full step list, so there is no duplicated workflow to maintain.

## Related

- [`port-to-python-limited-api`](../port-to-python-limited-api/) — the `abi3`/`abi3t`
  ABI work; pair with this skill to ship **one** `abi3.abi3t` wheel instead of a
  `cp3Xt` per version.
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — nanobind has first-class
  free-threading support (`FREE_THREADED`).
- [`choose-python-build-backend`](../choose-python-build-backend/) — picks the backend
  whose free-threaded wheels this skill builds.

## Further reading

- CPython [Free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html)
  · [Free-threading C-API guide](https://docs.python.org/3/howto/free-threading-extensions.html).
- The community porting guides:
  [py-free-threading.github.io](https://py-free-threading.github.io/) —
  [porting Python](https://py-free-threading.github.io/porting/),
  [porting extensions](https://py-free-threading.github.io/porting-extensions/),
  [tracking](https://py-free-threading.github.io/tracking/).
- [PEP 703](https://peps.python.org/pep-0703/) (making the GIL optional) ·
  [PEP 803](https://peps.python.org/pep-0803/) (`abi3t`).
- Adoption trackers: [hugovk.dev/free-threaded-wheels](https://hugovk.dev/free-threaded-wheels/).

See the repository [`README.md`](../../README.md) for per-agent setup (Claude Code,
Codex, and others).
