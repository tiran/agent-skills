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
| [`choose-python-build-backend`](skills/choose-python-build-backend/SKILL.md) | Experimental | Decide which PEP 517 build backend a new or existing project should use, and how to migrate. Chooses by purelib vs platlib (compiled), static vs dynamic/VCS metadata, and native language/build system. Covers uv-build, flit-core, hatchling (incl. compiled via scikit-build-core[hatchling] / a custom hook), meson-python, scikit-build-core, maturin, and setuptools (legacy) — with a balanced "should you leave setuptools?" assessment. |
| [`port-to-scikit-build-core`](skills/port-to-scikit-build-core/SKILL.md) | Experimental | A package builds a compiled extension with a bespoke `setup.py` (setuptools `Extension`/`CUDAExtension`, custom `build_ext`), and you are asked to adopt scikit-build-core + CMake, move to `pyproject.toml`, drop `setup.py`, or produce standards-based/abi3/CI wheels. |
| [`port-to-meson-python`](skills/port-to-meson-python/SKILL.md) | Experimental | Build a package (usually a compiled C/C++/Cython/Fortran/Rust extension) with the meson-python PEP 517 backend, or port one off a bespoke `setup.py`: `pyproject.toml` + `meson.build`, VCS versioning computed in `meson.build`, editable installs, abi3 wheels. Meson-based sibling of `port-to-scikit-build-core`. |
| [`modernize-python-metadata`](skills/modernize-python-metadata/SKILL.md) | Experimental | Improve a package's metadata and move it into a PEP 621 `[project]` table: readme field (drop the `open().read()` hack), SPDX license expression + license-files, trove classifiers (incl. `Private :: Do Not Upload`), well-known project URLs, authors/keywords/requires-python, dependency floors (no upper caps), PEP 735 dependency groups vs extras, the `[build-system]` table. Keeps the existing backend (setuptools stays fine) — a metadata task, not a build-system change. |
| [`port-to-python-limited-api`](skills/port-to-python-limited-api/SKILL.md) | Experimental | A project ships a hand-written C/C++ CPython extension (written against `Python.h`) and you are asked to adopt the Limited API / stable ABI (`Py_LIMITED_API`, abi3) so one wheel loads on every later Python instead of one per version, and/or to target Python 3.15 `abi3t` (PEP 803 + PEP 793 `PyModExport`) for a single wheel across GIL-enabled and free-threaded builds. Covers the usual first step — converting static `PyTypeObject` types to heap types (`PyType_FromSpec`) — module state, multi-phase init, API substitutions, and build flags/wheel tags for meson-python, scikit-build-core, maturin, setuptools (Cython/PyO3 at the build-flag level). Not for pybind11/nanobind or the PyTorch C++ ABI. |
| [`port-to-free-threaded-python`](skills/port-to-free-threaded-python/SKILL.md) | Experimental | A package should run on the free-threaded (no-GIL) CPython build (PEP 703; the `cp313t`/`cp314t` "t" ABI) and declare support so importing it doesn't silently re-enable the GIL. Covers the pure-Python thread-safety pass and, for C/C++/Cython/pybind11/nanobind/Rust-PyO3 extensions, declaring support (`Py_mod_gil` / `PyUnstable_Module_SetGIL` / the per-binding flag), the borrowed-reference hazards and strong-ref replacements (`PyList_GetItemRef`), building `cp3Xt` wheels, and testing with ThreadSanitizer / `pytest-run-parallel`. Detects all unprotected shared state but fixes only simple cases (borrowed→strong swaps, one atomic, a self-contained critical section / `PyMutex`); reports complex C/C++ shared-state redesign to the user. For a single `abi3t` wheel, pair with `port-to-python-limited-api`. |
| [`pybind11-to-nanobind`](skills/pybind11-to-nanobind/SKILL.md) | Experimental | A C++ extension binds its native code with pybind11, and you are asked to migrate to nanobind — cut binding compile time / binary size, improve free-threading, or produce a single abi3 wheel. Pairs with `port-to-scikit-build-core` (nanobind is CMake-native). |
| [`port-to-torch-stable-abi`](skills/port-to-torch-stable-abi/SKILL.md) | Beta | A project ships a compiled PyTorch C++/CUDA/ROCm extension version-locked to one Torch release, or you are asked to adopt the PyTorch stable ABI (`torch::stable` / `TORCH_TARGET_VERSION`) / stop rebuilding a wheel per Torch version. Also assesses Python abi3. |
| [`secure-python-release-pipeline`](skills/secure-python-release-pipeline/SKILL.md) | Experimental | Set up or review a GitHub Actions build/release pipeline for a Python package: split sdist/wheel builds (wheels built from the sdist), cibuildwheel for C/C++/Rust, publish to PyPI via a Trusted Publisher (OIDC, no token) in a locked-down job, minimal permissions, SHA-pinned actions, no cache on release, zizmor audit, attestations. |
| [`crypto-fips-audit`](skills/crypto-fips-audit/SKILL.md) | Experimental | Audit a Python package — and any C/C++/Go/Rust it ships — for its use of cryptography: inventory what crypto it uses at all, find insecure/weak crypto (AES-ECB, RSA PKCS#1 v1.5, static IV/nonce, `random` for secrets, disabled TLS verification, weak keys), and assess FIPS 140-3 compliance (refused/restricted hashes MD5/SHA-1, non-approved primitives BLAKE/ChaCha20-Poly1305/scrypt/Argon2/bcrypt/X25519, vendored/statically linked crypto that escapes the system validated module, hardcoded TLS/ciphers that bypass crypto-policies, bundled CA stores, problematic PyPI deps). Source-first, confirmed against the built wheel/binaries. Gathers evidence; does not certify. |

Status: **Stable** (broadly applied, verified), **Beta** (real cases, some rough
edges — check its output), **Experimental** (early draft). Beta/experimental
skills need a closer human review of their results.

## Working in this repo

- **Always work on a _new_ branch, one per change** — never commit to `main`, and
  never reuse, reset, or add commits to a branch left over from earlier work. Start
  each task by branching off freshly-fetched `main`
  (`git fetch origin && git switch -c <name> origin/main`), commit there, open a PR.
  When the user says "create a new branch," run `git switch -c` for a brand-new
  branch — do **not** reinterpret it as committing onto the current branch. One
  branch = one PR = one logical change; don't mix unrelated changes on a branch.
- **Follow standard commit-message conventions:** an imperative subject line of
  **≤50 characters** (capitalized, no trailing period), a blank line, then a body
  wrapped at **72 columns** explaining the *why* / user impact — not a file-by-file
  changelog. Keep it terse; omit the body for trivial changes.
  **Optimize for human readability:** write the body for a reviewer skimming
  `git log` — lead with the user impact and the important change, cut restated
  detail and boilerplate, and prefer a short message over an exhaustive one. Bullet
  points are fine, and preferred over a run-on paragraph, when the change has
  several distinct parts.
- **Verify `pre-commit` before pushing** — run `pre-commit run --all-files` (or let
  the git hook run) and fix any failures locally; don't push a branch whose hooks
  fail.
- **PR title and description mirror the commit** — reuse the commit subject as the
  PR title and the commit body as the description. Don't pad the PR with boilerplate
  the commit doesn't have (no invented "Testing" / "Changes" sections).
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
- **Register the skill in both index tables, in the same change.** Adding, renaming,
  or removing a skill must update the `## Skills` table here in `AGENTS.md` *and* the
  `## Skills` table in the root [`README.md`](README.md) (the human-facing index) —
  they must list the same skills. Add a row to `skills/reference-repos.md` too when
  the skill introduces a grounding repo. The `AGENTS.md` cell describes *when to use*
  the skill (trigger conditions); the `README.md` cell describes *what it does*.
- Keep prose lean. Draft with AI if you like, but read and cut it down before
  committing — unedited AI text is long, unchecked, and expensive to review.
- **Link PEP references in human-facing docs.** In `README.md` files (the root index
  and each skill's), write a PEP mention as a link to `https://peps.python.org/pep-XXXX/`
  — zero-padded, e.g. `[PEP 517](https://peps.python.org/pep-0517/)` — on first mention
  per file. `SKILL.md`/`AGENTS.md` are agent-facing and need no such linking.

## Pointing another project at a skill

To have an agent in a *different* project use a skill here, add a line to that
project's `AGENTS.md`, for example:

```markdown
For PyTorch stable-ABI ports, follow
<path-to>/agent-skills/skills/port-to-torch-stable-abi/SKILL.md.
```
