# AGENTS.md — port-to-meson-python

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

You are asked to build a Python package (usually with a compiled
C/C++/Cython/Fortran/Rust extension) with the **meson-python** PEP 517 backend —
scaffold a new project, or port one off a bespoke `setup.py` — move to
`pyproject.toml` (PEP 517/621), drop `setup.py`, add VCS versioning, or produce
standards-based / abi3 wheels.

## Status

**Experimental** — distilled from one real shipping project (pycxxfilt) plus the
upstream docs, but the workflow is a new draft. Have a human review the wheel on
every target platform.

## How to run it

1. Read **`SKILL.md`** in this directory — the ordered workflow (two tracks:
   new project / port from setuptools). Follow it top to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/example.md` — pycxxfilt as an annotated example, focused on
     VCS versioning computed in `meson.build` and the abi3 setup.
   - `reference/meson-cookbook.md` — `meson.build` patterns, `[tool.meson-python]`
     settings, config-settings, and the setuptools→Meson mapping.

## Related skills

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — the CMake-based
  sibling. Pick meson-python for a Meson build, scikit-build-core for a CMake one.
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — if the C++ bindings are
  also being modernized (nanobind supports Meson too).

## Definition of done

`uv build` yields an installable sdist + wheel with no `setup.py`; the
package imports and its tests pass from both wheel and sdist; editable install
rebuilds on import; and, if targeted, one abi3 wheel loads across Python versions.
