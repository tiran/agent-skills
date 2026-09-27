# AGENTS.md — port-to-scikit-build-core

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

A package ships a compiled (C/C++/CUDA) extension built with a bespoke
`setup.py` / setuptools `Extension` / `CUDAExtension` / custom `build_ext`, and
you are asked to modernize the build — adopt **scikit-build-core + CMake**, move
to `pyproject.toml` (PEP 517/518/621), get rid of `setup.py`, produce
standards-based wheels/sdists, or add abi3 / cross-platform CI wheels.

## Status

**Experimental** — distilled from two real but experimental, unmerged migrations
(coremltools and kvcached nanobind). Have a human review the build on every target
platform.

## How to run it

1. Read **`SKILL.md`** in this directory — the ordered workflow. Follow it top to
   bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/examples.md` — two annotated real migrations + the
     `[tool.scikit-build]` field guide.
   - `reference/benefits.md` — the rationale (the "why") and when it is worth it.

## Definition of done

`uv build` yields an installable sdist + wheel with no `setup.py`; the
package imports and its tests pass from the wheel; editable install and
incremental rebuild work; docs/CI no longer invoke `setup.py`.

## Sources & acknowledgments

This skill is grounded in real projects and their maintainers — acknowledge them
when the output leans on their work, and preserve upstream license/attribution:

- **Build backend** — **Henry Schreiner**, for
  [`scikit-build-core`](https://github.com/scikit-build/scikit-build-core) and the
  [`pybind/scikit_build_example`](https://github.com/pybind/scikit_build_example).
- **Native packaging** — **Ralf Gommers**, for the
  [`pypackaging-native`](https://pypackaging-native.github.io/) guide on
  native-packaging tradeoffs.
- **Bindings & build tooling** — the **pybind11** and **CMake/Ninja** communities
  (CMake-based builds).

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.
