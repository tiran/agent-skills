# AGENTS.md — agent-skills

Instructions for AI coding agents working in **or with** this repository. Humans
should read [`README.md`](README.md) instead. This file is read by Codex (and any
`AGENTS.md`-aware agent) from the working directory upward; Claude Code reads it
via the `CLAUDE.md` symlink.

The skills here are plain Markdown on the open Agent Skills standard, so they are
not tied to any one agent.

## Using a skill

1. Pick the skill whose scope matches the task from the index below.
2. Read that skill's `SKILL.md` — the ordered workflow. Follow it top to bottom.
3. Open the skill's `reference/*.md` files only when a step cites them.

Agents with native skill support should prefer it: Claude Code discovers skills
through its plugin; Codex auto-discovers `SKILL.md` under `.agents/skills/` (or
via this repo's `plugin.json`) and invokes them with `$<skill>` / `/skills`. This
router is the fallback for agents without a skill system.

## Skills

| Skill | Status | Use when |
| --- | --- | --- |
| [`port-to-torch-stable-abi`](skills/port-to-torch-stable-abi/SKILL.md) | Beta | A project ships a compiled PyTorch C++/CUDA/ROCm extension version-locked to one Torch release, or you are asked to adopt the PyTorch stable ABI (`torch::stable` / `TORCH_TARGET_VERSION`) / stop rebuilding a wheel per Torch version. Also assesses Python abi3. |
| [`port-to-scikit-build-core`](skills/port-to-scikit-build-core/SKILL.md) | Experimental | A package builds a compiled extension with a bespoke `setup.py` (setuptools `Extension`/`CUDAExtension`, custom `build_ext`), and you are asked to adopt scikit-build-core + CMake, move to `pyproject.toml`, drop `setup.py`, or produce standards-based/abi3/CI wheels. |
| [`pybind11-to-nanobind`](skills/pybind11-to-nanobind/SKILL.md) | Experimental | A C++ extension binds its native code with pybind11, and you are asked to migrate to nanobind — cut binding compile time / binary size, improve free-threading, or produce a single abi3 wheel. Pairs with `port-to-scikit-build-core` (nanobind is CMake-native). |
| [`port-to-meson-python`](skills/port-to-meson-python/SKILL.md) | Experimental | Build a package (usually a compiled C/C++/Cython/Fortran/Rust extension) with the meson-python PEP 517 backend, or port one off a bespoke `setup.py`: `pyproject.toml` + `meson.build`, VCS versioning computed in `meson.build`, editable installs, abi3 wheels. Meson-based sibling of `port-to-scikit-build-core`. |
| [`secure-python-release-pipeline`](skills/secure-python-release-pipeline/SKILL.md) | Experimental | Set up or review a GitHub Actions build/release pipeline for a Python package: split sdist/wheel builds (wheels built from the sdist), cibuildwheel for C/C++/Rust, publish to PyPI via a Trusted Publisher (OIDC, no token) in a locked-down job, minimal permissions, SHA-pinned actions, no cache on release, zizmor audit, attestations. |
| [`modernize-python-metadata`](skills/modernize-python-metadata/SKILL.md) | Experimental | Improve a package's metadata and move it into a PEP 621 `[project]` table: readme field (drop the `open().read()` hack), SPDX license expression + license-files, trove classifiers (incl. `Private :: Do Not Upload`), well-known project URLs, authors/keywords/requires-python, dependency floors (no upper caps), PEP 735 dependency groups vs extras, the `[build-system]` table. Keeps the existing backend (setuptools stays fine) — a metadata task, not a build-system change. |
| [`choose-python-build-backend`](skills/choose-python-build-backend/SKILL.md) | Experimental | Decide which PEP 517 build backend a new or existing project should use, and how to migrate. Chooses by purelib vs platlib (compiled), static vs dynamic/VCS metadata, and native language/build system. Covers uv-build, flit-core, hatchling (incl. compiled via scikit-build-core[hatchling] / a custom hook), meson-python, scikit-build-core, maturin, and setuptools (legacy) — with a balanced "should you leave setuptools?" assessment. |

Status: **Stable** (broadly applied, verified), **Beta** (real cases, some rough
edges — check its output), **Experimental** (early draft). Beta/experimental
skills need a closer human review of their results.

## Working in this repo

- **Always work on a branch** — never commit to `main`. Branch first, commit
  there, open a PR.
- **Follow standard commit-message conventions:** an imperative subject line of
  **≤50 characters** (capitalized, no trailing period), a blank line, then a body
  wrapped at **72 columns** explaining the *why* / user impact — not a file-by-file
  changelog. Keep it terse; omit the body for trivial changes.
- **Always sign off commits** (`git commit -s`) — add the `Signed-off-by` line
  (DCO).

## Authoring or editing a skill (conventions)

- One skill per directory under `skills/<name>/`, with a single `SKILL.md` as the
  source of truth (frontmatter `name` + `description`, then an ordered workflow).
- Keep the `description` tight and specific — agents trigger the skill from it.
- Put tables, snippets, and long rationale under `reference/` and cite them from
  the numbered steps; do not inline them into the workflow.
- Do not duplicate the workflow into the per-skill `AGENTS.md`/`README.md`; those
  are thin adapters that point back at `SKILL.md`.
- Keep prose lean. Draft with AI if you like, but read and cut it down before
  committing — unedited AI text is long, unchecked, and expensive to review.

## Pointing another project at a skill

To have an agent in a *different* project use a skill here, add a line to that
project's `AGENTS.md`, for example:

```markdown
For PyTorch stable-ABI ports, follow
<path-to>/agent-skills/skills/port-to-torch-stable-abi/SKILL.md.
```
