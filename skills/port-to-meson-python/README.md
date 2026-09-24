# Skill: build (or port) a package with meson-python + Meson

Build a Python package with the **meson-python** [PEP 517](https://peps.python.org/pep-0517/) backend — scaffold a new
project or port one off a bespoke `setup.py`. Covers the `pyproject.toml`
backend, the `meson.build` (`project` / `extension_module` / `install_sources`),
VCS/dynamic versioning computed in `meson.build`, editable installs,
config-settings, and abi3 / limited-API wheels.

**Status: Experimental** — built from one real shipping project (pycxxfilt) plus
the upstream docs, but the workflow is a new draft. Review the wheel on every
target platform.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 11 ordered steps, two tracks (new / port) + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/example.md` | pycxxfilt annotated — VCS version in `meson.build`, abi3, cibuildwheel. |
| `reference/meson-cookbook.md` | `meson.build` patterns, `[tool.meson-python]`, config-settings, setuptools→Meson map. |

## Related

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — the CMake-based
  sibling; pick by which native build system you want (Meson vs CMake).
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — nanobind bindings also
  build under Meson.

See the repository [`README.md`](../../README.md) for per-agent setup (Claude
Code, Codex, others).
