# AGENTS.md — agent-skills

Entry point for AI coding agents **using the skills** in this repository. **To edit
this repo** (add or change a skill), read [`CONTRIBUTING.md`](CONTRIBUTING.md); humans
should read [`README.md`](README.md). This file is read by Codex (and any
`AGENTS.md`-aware agent) from the working directory upward; Claude Code reads it via
the `CLAUDE.md` symlink.

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
| [`ship-type-information`](skills/ship-type-information/SKILL.md) | Experimental | Add type information to a package or make its types reach users — annotate untyped code (autotyping, `pyrefly infer`, MonkeyType), add the `py.typed` marker (PEP 561), generate/fix `.pyi` stubs for a compiled C/C++/Cython/Rust extension (nanobind stubgen, `pybind11-stubgen`, `mypy stubgen`, `pyo3-stub-gen`; `__text_signature__` for hand-written C), verify with mypy/pyright (`--verifytypes`)/ty/pyrefly + `stubtest`, and package the stubs so the built wheel carries them. Use to add types, ship `py.typed`, raise type completeness, or fix downstream "module is untyped" / `Any` results. |
| [`secure-python-release-pipeline`](skills/secure-python-release-pipeline/SKILL.md) | Experimental | Set up or review a GitHub Actions build/release pipeline for a Python package: split sdist/wheel builds (wheels built from the sdist), cibuildwheel for C/C++/Rust, publish to PyPI via a Trusted Publisher (OIDC, no token) in a locked-down job, minimal permissions, SHA-pinned actions, no cache on release, zizmor audit, attestations. |
| [`crypto-fips-audit`](skills/crypto-fips-audit/SKILL.md) | Experimental | Audit a Python package — and any C/C++/Go/Rust it ships — for its use of cryptography: inventory what crypto it uses at all, find insecure/weak crypto (AES-ECB, RSA PKCS#1 v1.5, static IV/nonce, `random` for secrets, disabled TLS verification, weak keys), and assess FIPS 140-3 compliance (refused/restricted hashes MD5/SHA-1, non-approved primitives BLAKE/ChaCha20-Poly1305/scrypt/Argon2/bcrypt/X25519, vendored/statically linked crypto that escapes the system validated module, hardcoded TLS/ciphers that bypass crypto-policies, bundled CA stores, problematic PyPI deps). Source-first, confirmed against the built wheel/binaries. Gathers evidence; does not certify. |

Status: **Stable** (broadly applied, verified), **Beta** (real cases, some rough
edges — check its output), **Experimental** (early draft). Beta/experimental
skills need a closer human review of their results.

## Contributing to this repo

**Editing this repo (adding or changing a skill)? Read
[`CONTRIBUTING.md`](CONTRIBUTING.md)** — it has the full git/PR workflow and the
skill-authoring conventions. In brief:

- **Branch off freshly-fetched `main`**, one branch = one PR = one logical change;
  never commit to `main`.
- **Sign off commits** (`git commit -s`, DCO); imperative ≤50-char subject, body
  wrapped at 72.
- **Run `pre-commit run --all-files`** and fix failures before pushing.
- **Register a new skill in both `## Skills` tables** (here and `README.md`) and add
  its `## Acknowledgments` / `## Sources & acknowledgments` sections.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for commit-message style, skill layout,
reference-file rules, PEP linking, and the acknowledgment rule in full.

## Pointing another project at a skill

To have an agent in a *different* project use a skill here, add a line to that
project's `AGENTS.md`, for example:

```markdown
For PyTorch stable-ABI ports, follow
<path-to>/agent-skills/skills/port-to-torch-stable-abi/SKILL.md.
```
