# Skill: port a package build to scikit-build-core + CMake

Migrate a Python package with a compiled (C/C++/CUDA) extension from a bespoke
`setup.py` / setuptools build to **scikit-build-core + CMake** ([PEP 517](https://peps.python.org/pep-0517/)/[518](https://peps.python.org/pep-0518/)/[621](https://peps.python.org/pep-0621/)):
a declarative `pyproject.toml`, CMake for the native code, standards-based
wheels/sdists, editable installs, and optional abi3 via nanobind.

**Status: Experimental** — built from two real but unmerged migrations
(coremltools, kvcached nanobind). Review the build on every target platform.

It handles two starting points in one workflow:

- **Track A** — a project with an existing CMake core and `setup.py` glue (just
  add install rules and delete the glue).
- **Track B** — a project built only with torch `CppExtension`/`CUDAExtension`
  and no CMake (author a `CMakeLists.txt`).

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 11 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/examples.md` | Two annotated real migrations + `[tool.scikit-build]` field guide. |
| `reference/benefits.md` | The case for scikit-build-core over setuptools (the "why"). |

## Related

Pairs with [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — the abi3 /
nanobind path (SKILL step 9) is where the two skills meet.

## Acknowledgments

This skill distills the work of many people and projects:

- **Henry Schreiner** — [`scikit-build-core`](https://github.com/scikit-build/scikit-build-core)
  and the [`pybind/scikit_build_example`](https://github.com/pybind/scikit_build_example).
- **Ralf Gommers** — the [`pypackaging-native`](https://pypackaging-native.github.io/)
  guide on native-packaging tradeoffs.
- The **pybind11** and **CMake/Ninja** communities (CMake-based builds).

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.

See the repository [`README.md`](../../README.md) for per-agent setup (Claude
Code, Codex, others).
