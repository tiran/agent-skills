# AGENTS.md — bootstrap-python-project

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both share
the same content and reference files.

## When to use

You are asked to **start a new Python project** — scaffold/bootstrap a package,
set up a repo from zero, or turn a loose script into a proper installable, typed,
tested, releasable package — **or to bring an existing project up to this standard**
(adopt the layout, metadata, tooling, or CI it lacks). Produces the full opinionated
shape (not a bare `uv init`): `src/` layout, PEP 621 metadata, dynamic VCS versioning,
`py.typed`, ruff, a type checker, pytest + coverage, tox/nox via uv, and hardened
GitHub CI — always with a README, a LICENSE file, and a `.gitignore`. In the
improve-existing mode, run the workflow as a gap analysis and respect the project's
existing choices.

## Status

**Experimental** — encodes the `tiran/*` house style plus current PyPA / Astral /
Hynek Schlawack practice. Review the generated tree and the first CI run.

## How to run it

1. Read **`SKILL.md`** and follow the 10 steps: gather requirements (1), choose
   the backend (2), lay out `src/` (3), write `[project]` (4), configure ruff /
   type checker / pytest+coverage (5), set up tox or nox (6), add the required
   repo files (7), generate hardened CI (8), initialize + verify (9), and
   optionally make it a reusable template (10).
2. Open a bundled reference when a step cites it:
   - `reference/scaffold.md` — concrete file contents for both the pure-Python and
     compiled cases.
   - `reference/tooling-choices.md` — type checker (Pyrefly/ty/mypy), license,
     tox vs nox, and project-template tools (`scientific-python/cookie`, copier).
   - `reference/task-runners.md` — nox vs tox benefits, and why not make / shell.
   - `reference/containers.md` — container house rule (if used): OCI-standard,
     Podman+Docker, `ARG` over hard-coded values, Dev Container standard.

## Related skills

This skill **orchestrates** rather than duplicates:

- [`choose-python-build-backend`](../choose-python-build-backend/) — pick the backend (step 2).
- [`modernize-python-metadata`](../modernize-python-metadata/) — write the `[project]` table (step 4).
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — harden CI + release (step 8).
- [`port-to-meson-python`](../port-to-meson-python/) / [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — native build details for compiled projects.

## Definition of done

A repo that installs (`uv sync`), lints clean (ruff), type-checks clean, tests pass
(`pytest` / `tox`), builds a valid inspected sdist+wheel (`uv build`), and has
hardened CI plus a Trusted-Publisher release workflow — with a README, a LICENSE
file, and a `.gitignore`. Nothing committed without the user's OK.

## Sources & acknowledgments

This skill is grounded in real projects and their maintainers — acknowledge them when
the output leans on their work, and preserve upstream license/attribution:

- **Packaging & release:** Hynek Schlawack (`build-and-inspect-python-package`,
  `structlog`, `attrs`).
- **Templates, linting & guide:** Henry Schreiner (`scientific-python/cookie`,
  `sp-repo-review`, the Scientific-Python Development Guide); Ralf Gommers (meson-python).
- **Tooling:** Astral (`uv`, `ruff`, `ty`); Meta (Pyrefly); Bernát Gábor (`tox`); the
  nox maintainers; Marius Gedminas (`check-python-versions`).
- **Worked CI/practice examples:** pydantic, fastapi, pyca/cryptography.
- **Standards & conventions:** the PyPA; Red Hat (UBI, the OpenShift `1001:0`
  arbitrary-UID container model).
- **House style:** Christian Heimes' `tiran/{pycxxfilt,zipwire,retread}`.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.
