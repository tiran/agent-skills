# Skill: port a C++ extension from pybind11 to nanobind

Migrate a Python C++ extension's bindings from **pybind11** to **nanobind** — the
mechanical API renames, the removed pybind11 features to design around, opt-in
STL casters, custom constructors and type casters, the CMake
`nanobind_add_module` build, and an optional single abi3 wheel.

**Status: Experimental** — built from one real but unmerged migration (the
kvcached nanobind branch) plus the upstream porting guide. Review the build and
tests on every target platform.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 12 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/api-map.md` | Full rename table, STL caster headers, semantic diffs, removed features. |
| `reference/example.md` | The kvcached nanobind branch as an annotated worked example. |

## Related

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — nanobind builds
  through CMake; migrate the build there first if the project still uses
  `setup.py`.
- [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — for PyTorch
  extensions, the abi3 paths meet.

See the repository [`README.md`](../../README.md) for per-agent setup (Claude
Code, Codex, others).
