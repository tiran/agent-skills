# Skill: bootstrap a new Python project

Scaffold a new Python project ready to install, type-check, test, and release on day
one — not a bare `uv init`. A modern `src/` layout with
[PEP 621](https://peps.python.org/pep-0621/) metadata, dynamic VCS versioning, a
`py.typed` marker, quality tooling, and hardened CI — the shape the
[`tiran/*`](https://github.com/tiran) reference repos ship.

Covers **hatchling + hatch-vcs** (pure Python, the default) and **meson-python +
vcs-versioning** / **scikit-build-core** / **maturin** (compiled), **ruff** (lint +
format), a type checker (**Pyrefly** by default; **ty** or **mypy** on request),
**pytest + coverage**, **tox** (or **nox**) driven by **uv**, and GitHub Actions CI
hardened per [`secure-python-release-pipeline`](../secure-python-release-pipeline/)
(SHA-pinned, least-privilege, `build-and-inspect-python-package`, CodeQL, Scorecard,
Dependabot, PyPI Trusted Publisher + attestations). Always writes a README, a LICENSE
file, and a `.gitignore`. Type checker, task runner, license, and docs generator are
decided with the user (see `reference/tooling-choices.md`).

**Status: Experimental** — encodes one house style plus current PyPA / Astral / Hynek
Schlawack practice; review the generated tree and first CI run.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The 10-step workflow + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/scaffold.md` | Concrete file contents: `pyproject.toml` (pure + compiled), `tox.ini` / `noxfile.py`, ruff/pytest/coverage config, CI workflows, `.gitignore`, `SECURITY.md`. |
| `reference/tooling-choices.md` | The open decisions: type checker (Pyrefly/ty/mypy), license (permissive vs copyleft), tox vs nox, and template tools (recommended `scientific-python/cookie`; copier, cookiecutter/cruft, `uv init`/`hatch new`). |
| `reference/task-runners.md` | The full task-runner rationale: nox vs tox benefits, and why not make / shell scripts (portability, env isolation, footguns). |
| `reference/containers.md` | Container house rule (if used): OCI-standard, Podman+Docker tool-agnostic, `ARG` over hard-coded values, avoid dockerisms, Dev Container standard. |

## Related

This skill **orchestrates** these:

- [`choose-python-build-backend`](../choose-python-build-backend/) — pick the backend.
- [`modernize-python-metadata`](../modernize-python-metadata/) — write `[project]`.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — the CI/release path.
- [`port-to-meson-python`](../port-to-meson-python/) / [`port-to-scikit-build-core`](../port-to-scikit-build-core/) — native build details for compiled projects.

## Further reading

- [PyPA — writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Scientific Python Development Guide](https://learn.scientific-python.org/development/) · [`scientific-python/cookie`](https://github.com/scientific-python/cookie)
- [copier](https://copier.readthedocs.io/) · [hynek/build-and-inspect-python-package](https://github.com/hynek/build-and-inspect-python-package)
- Reference repos: [`tiran/zipwire`](https://github.com/tiran/zipwire), [`tiran/retread`](https://github.com/tiran/retread), [`tiran/pycxxfilt`](https://github.com/tiran/pycxxfilt)

## Acknowledgments

This skill distills the work of many people and projects:

- **Hynek Schlawack** — modern packaging and release practice,
  [`build-and-inspect-python-package`](https://github.com/hynek/build-and-inspect-python-package),
  and the [`structlog`](https://github.com/hynek/structlog) /
  [`attrs`](https://github.com/python-attrs/attrs) exemplars.
- **Henry Schreiner** — [`scientific-python/cookie`](https://github.com/scientific-python/cookie),
  `sp-repo-review`, and the [Scientific-Python Development Guide](https://learn.scientific-python.org/development/);
  **Ralf Gommers** — [meson-python](https://github.com/mesonbuild/meson-python) and
  native-packaging guidance.
- **Astral** — [`uv`](https://docs.astral.sh/uv/), [`ruff`](https://docs.astral.sh/ruff/),
  and `ty`; **Meta's Pyrefly team** — the default type checker; **Bernát Gábor** —
  [`tox`](https://github.com/tox-dev/tox); the [**nox**](https://github.com/wntrblm/nox)
  maintainers; **Marius Gedminas** —
  [`check-python-versions`](https://github.com/mgedmin/check-python-versions).
- Worked CI/practice examples from **pydantic**, **fastapi**, **pyca/cryptography**,
  `structlog`, and `attrs`; standards from the **PyPA**; container conventions from
  **Red Hat** (UBI, the OpenShift `1001:0` arbitrary-UID model).
- **Christian Heimes** ([`tiran`](https://github.com/tiran)) — the `pycxxfilt` /
  `zipwire` / `retread` house style this skill encodes.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.

See the repository [`README.md`](../../README.md) for per-agent setup.
