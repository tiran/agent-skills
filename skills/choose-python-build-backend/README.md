# Skill: choose a Python build backend

Recommend the right PEP 517 build backend for a new or existing Python package,
and give enough context to migrate. Chooses by three axes — **purelib** (pure
Python) vs **platlib** (compiled C/C++/Rust/Torch/…), **static vs dynamic/VCS
metadata**, and the **native language/build system** — then points at the skill
that does the migration.

Covers **uv-build**, **flit-core**, **hatchling** (including compiled builds via
`scikit-build-core[hatchling]` or a custom `hatch_build.py` hook),
**meson-python**, **scikit-build-core**, **maturin**, and **setuptools** (the
legacy path). Poetry is intentionally out of scope.

**Status: Experimental** — grounded in the PyPA tool recommendations and current
backend docs; the decision procedure is a new draft.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The decision procedure — 5 steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/backends.md` | Per-backend assessment + comparison table (purelib/platlib, metadata, build system, `[build-system]` block, migration notes). |
| `reference/why-not-setuptools.md` | The balanced case for/against setuptools. |

## Related

This skill **recommends**; these **execute**:

- [`modernize-python-metadata`](../modernize-python-metadata/) — move metadata
  into `[project]`.
- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — compiled backends.
- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — abi3 / Torch.

## Further reading

- [PyPA — tool recommendations](https://packaging.python.org/en/latest/guides/tool-recommendations/)
- [pyOpenSci — Python packaging build tools](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-build-tools.html)
- [Scientific Python — compiled packaging](https://learn.scientific-python.org/development/guides/packaging-compiled/)
- ["Why Hatch?"](https://hatch.pypa.io/latest/why/) · [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/) · [Quansight — PEP 517 backend popularity](https://labs.quansight.org/blog/pep-517-build-system-popularity)

See the repository [`README.md`](../../README.md) for per-agent setup.
