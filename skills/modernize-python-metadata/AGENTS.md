# AGENTS.md — modernize-python-metadata

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

You are asked to **improve a Python package's metadata** and move it into a PEP
621 `[project]` table — clean up a PyPI page, fill in missing author/license/URL
info, move metadata out of `setup.py`/`setup.cfg`, adopt SPDX license
expressions, well-known project URLs, or PEP 735 dependency groups, or fix
version constraints.

This is a **metadata** task, not a build-backend change: **setuptools stays a
fine choice** (it reads `[project]`), and build logic like `ext_modules` remains
where it is. If you actually need to change *how* the package builds, use
`port-to-scikit-build-core` / `port-to-meson-python` instead.

## Status

**Experimental** — grounded in the current PyPA specifications; the step order is
a new draft. Metadata bugs are quiet, so verify with `validate-pyproject` and
`twine check` (SKILL step 11).

## How to run it

1. Read **`SKILL.md`** — the ordered workflow (11 steps). Follow it top to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/field-guide.md` — full `[project]` field reference (readme,
     license, classifiers, well-known URLs), the setup.py→`[project]` field map,
     and tool-version floors for newer fields.
   - `reference/dependencies.md` — version constraints (avoid caps), extras vs
     dependency groups, `[build-system].requires`, and the Torch
     `--no-build-isolation` special case.

## Related skills

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — change the *build backend*
  (this skill deliberately does not).
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) —
  publishes the package whose metadata this skill cleans up.

## Definition of done

Metadata lives in a static `[project]` table (nothing duplicated in
`setup.py`/`setup.cfg`); `validate-pyproject` and `twine check` pass; README,
SPDX license, authors, keywords, classifiers, and well-known URLs are populated;
dependencies use floors without speculative caps; dev tooling is in
`[dependency-groups]`; the build backend is declared (keeping setuptools is fine).
