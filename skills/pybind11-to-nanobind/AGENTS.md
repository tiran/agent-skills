# AGENTS.md — pybind11-to-nanobind

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

A Python C++ extension binds its native code with **pybind11** and you are asked
to migrate to **nanobind** — to cut binding compile time and binary size, get
better free-threading, or produce a single **abi3** wheel across Python
versions.

## Status

**Experimental** — distilled from one real but unmerged migration (the kvcached
nanobind branch) plus the upstream porting guide. The API map is authoritative;
the workflow is new. Have a human review the build and tests on every target
platform.

## How to run it

1. Read **`SKILL.md`** in this directory — the ordered workflow. Follow it top to
   bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/api-map.md` — the full rename table, opt-in STL caster headers,
     semantic differences, and the removed-feature list.
   - `reference/example.md` — the kvcached nanobind branch as an annotated,
     end-to-end worked example.

## Related skills

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — nanobind is
  CMake-native (`nanobind_add_module`); if the project still uses `setup.py` /
  torch `cpp_extension`, do the build migration there first (SKILL step 2).
- [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — for a PyTorch
  extension, the abi3 path (SKILL step 11) lines up with that skill's step 17.

## Definition of done

The extension builds and imports through nanobind, the test suite passes, no
pybind11 headers remain (except a deliberate gradual-port bridge), and — if
targeted — one abi3 wheel loads across Python versions.
