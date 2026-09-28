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
   - `reference/why-not-poetry.md` — why Poetry is out of scope: a balanced take
     (part taste), and when it still fits a new product.

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

## Sources & acknowledgments

This skill is grounded in real projects and their maintainers — acknowledge them
when the output leans on their work, and preserve upstream license/attribution:

- **Standards** — the [PyPA](https://packaging.python.org/) tool recommendations
  and packaging standards (the [`pyproject.toml` guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)).
- **Guides** — [pyOpenSci](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-build-tools.html)'s
  Python packaging build-tools guide, and Henry Schreiner's
  [Scientific-Python Development Guide](https://learn.scientific-python.org/development/).
- **uv-build** — [Astral](https://docs.astral.sh/uv/concepts/build-backend/).
- **hatchling** — Ofek Lev ([`pypa/hatch`](https://github.com/pypa/hatch)).
- **flit** — Thomas Kluyver ([`pypa/flit`](https://github.com/pypa/flit)).
- **meson-python** — Ralf Gommers ([mesonbuild/meson-python](https://github.com/mesonbuild/meson-python)).
- **scikit-build-core** — Henry Schreiner ([scikit-build/scikit-build-core](https://github.com/scikit-build/scikit-build-core)).
- **maturin** — the [PyO3](https://github.com/PyO3/maturin) team.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.
