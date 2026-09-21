# AGENTS.md — choose-python-build-backend

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

You are asked **which PEP 517 build backend to use** — for a new Python project,
or whether an existing one should move (often off setuptools). The skill decides
by three axes (purelib vs platlib, static vs dynamic/VCS metadata, native
language/build system) and gives enough context to migrate.

## Status

**Experimental** — grounded in the PyPA tool recommendations and current backend
docs; the decision procedure is a new draft.

## How to run it

1. Read **`SKILL.md`** — classify the project (step 1), pick for pure-Python
   (step 2) or compiled (step 3), decide the setuptools question (step 4), and
   follow the migration mechanics (step 5).
2. Open a bundled reference when a step cites it:
   - `reference/backends.md` — per-backend assessment (purelib/platlib, metadata,
     build system, exact `[build-system]` block, migration notes) + a comparison
     table. Covers uv-build, flit-core, hatchling (incl. compiled),
     meson-python, scikit-build-core, maturin, setuptools.
   - `reference/why-not-setuptools.md` — the balanced case for/against setuptools
     (deprecations, editable installs, parallel-build races, defaults).

## Related skills

This skill **recommends**; these **execute** the migration:

- [`modernize-python-metadata`](../modernize-python-metadata/) — move metadata to
  `[project]` (needed for any backend swap).
- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — compiled backends.
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — abi3 / Torch.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — ship
  the wheels once the backend is chosen.

## Definition of done

A recommendation naming the backend, the reasoning (the three axes), the exact
`[build-system]` block, static-vs-dynamic metadata, and — if migrating — the
specific migration skill plus the mechanical steps. For compiled projects it names
the native build system (CMake/Meson/Cargo), not just the backend.
