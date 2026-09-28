# AGENTS.md — ship-type-information

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both share the
same content and reference files.

## When to use

You are asked to **add type information to a Python package or make its types reach
users** — add annotations to untyped code, ship a `py.typed` marker, generate or fix
`.pyi` stubs for a compiled C/C++/Cython/Rust extension, raise a package's type
completeness, or fix downstream "module is untyped" / `Any` results. Covers pure-Python
annotation, stubs for extensions, PEP 561 declaration/packaging, and verification with
mypy / pyright / ty / pyrefly + `stubtest`.

## Status

**Experimental** — grounded in PEP 561, the typing spec, and current stub tooling; the
workflow is a new draft. Generated annotations and stubs are **drafts** — review them.

## How to run it

1. Read **`SKILL.md`** — the ordered 6-step workflow: assess (1), annotate untyped
   Python (2), stub compiled extensions (3), declare with `py.typed` (4), verify (5),
   package and inspect the wheel (6).
2. Open a bundled reference when a step cites it:
   - `reference/why-types.md` — the case for annotating, with expert sources (for
     convincing a maintainer).
   - `reference/annotating.md` — annotating untyped Python (static tools vs MonkeyType,
     strictness ramp).
   - `reference/stubs.md` — `.pyi` per binding (incl. Cython `stubgen-pyx`), hand-written
     C (`__text_signature__`), pattern files, placement, freshness gate.
   - `reference/verify-and-ship.md` — PEP 561 declaration, the four checkers +
     `--verifytypes` + `stubtest`, packaging, wheel verification.

## Related skills

- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — best-fidelity nanobind stubs
  (this skill defers nanobind detail there).
- [`port-to-python-limited-api`](../port-to-python-limited-api/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — one stub set per abi3 /
  stable-ABI wheel.
- [`port-to-free-threaded-python`](../port-to-free-threaded-python/) — typed
  free-threaded extensions.
- [`modernize-python-metadata`](../modernize-python-metadata/) — the `Typing :: Typed`
  classifier.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — checkers,
  `stubtest`, and the freshness gate in CI.

## Definition of done

The package ships `py.typed` (or a stub-only distribution); compiled extensions have
committed `.pyi` that `stubtest` validates against the runtime module; mypy, pyright,
ty, and pyrefly pass; `pyright --verifytypes` reports the intended completeness; the
built wheel actually contains the type files; and a CI gate keeps stubs fresh. Nothing
committed without the user's OK.

## Sources & acknowledgments

This skill is grounded in real projects and their maintainers — acknowledge them when
the output leans on their work, and preserve upstream license/attribution:

- **Checkers** — mypy / typeshed team; Eric Traut / Microsoft (pyright, `--verifytypes`);
  Astral (ty); Meta (Pyrefly).
- **Stub generation** — Wenzel Jakob (nanobind stubgen); Sergei Izmailov
  (`pybind11-stubgen`); the mypy team (`stubgen`, `stubtest`); the PyO3 project
  (`pyo3-stub-gen`).
- **Annotating untyped code** — Meta (MonkeyType, `pyrefly infer`); Jelle Zijlstra
  (`autotyping`); the `com2ann` / `infer-types` authors.
- **C signatures** — Larry Hastings and the CPython team (Argument Clinic,
  `__text_signature__`).
- **Standards** — the PEP 561 authors (Ethan Smith, Ivan Levkivskyi) and the
  typing-spec maintainers.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.
