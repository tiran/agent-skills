# AGENTS.md — secure-python-release-pipeline

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

You are asked to set up or review a **GitHub Actions** build/release pipeline for
a Python package — publish to PyPI, add wheels, adopt Trusted Publishing (OIDC),
add cibuildwheel for a C/C++/Rust extension, or harden an existing CI/CD workflow
(permissions, action pinning, zizmor, cache poisoning).

## Status

**Experimental** — assembled from two real shipping projects (pycxxfilt,
zipwire) plus upstream PyPI/zizmor/cibuildwheel docs; the consolidated workflow
is a new draft. Have a human review permissions and the PyPI publisher config.

## How to run it

1. Read **`SKILL.md`** — the ordered workflow (8 steps). Follow it top to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/templates.md` — copy-paste workflows (pure-Python, compiled +
     cibuildwheel, zizmor job, PyPI trusted-publisher checklist).
   - `reference/hardening.md` — the security rationale and the per-job
     permission map.

## Related skills

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — the build side; their
  VCS/dynamic versioning is what this pipeline freezes into the sdist (SKILL
  step 8).
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — produce the abi3
  wheels this pipeline builds and audits.

## Definition of done

A tag-triggered workflow builds an sdist, builds all wheels from that sdist,
verifies them, and publishes via a Trusted Publisher from a dedicated
`id-token: write` job; `permissions: {}` at top level with minimal per-job
grants; all actions SHA-pinned; no cache on release; zizmor clean.
