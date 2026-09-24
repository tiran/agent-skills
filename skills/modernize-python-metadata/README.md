# Skill: modernize Python packaging metadata

Improve a Python package's metadata and move it into a [PEP 621](https://peps.python.org/pep-0621/) `[project]` table
in `pyproject.toml`, filling in what's missing. Covers dropping the
`open("README.md").read()` hack for the `readme` field, **SPDX license
expressions** (an expression + `license-files`, never the full text), trove
classifiers (including `Private :: Do Not Upload`), **well-known project URLs**,
authors/keywords/`requires-python`, dependency version constraints (**floors, not
caps**), **[PEP 735](https://peps.python.org/pep-0735/) dependency groups vs extras**, and the `[build-system]` table.

**Keeps your build backend** — setuptools is a fine choice and reads `[project]`;
this skill moves *metadata*, it does not remove setuptools or change how the
package builds.

**Status: Experimental** — grounded in the current PyPA specifications; the step
order is a new draft. Metadata bugs are quiet, so verify with `validate-pyproject`
and `twine check` (SKILL step 11).

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 11 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/field-guide.md` | Full `[project]` field reference, setup.py→`[project]` map, tool-version floors. |
| `reference/dependencies.md` | Version constraints, extras vs dependency groups, build-system + Torch `--no-build-isolation`. |

## Related

- [`port-to-scikit-build-core`](../port-to-scikit-build-core/) /
  [`port-to-meson-python`](../port-to-meson-python/) — change the *build backend*
  (this skill does not).
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) —
  publishes the package whose metadata this skill cleans up.

## Further reading

Background from the packaging maintainers and community this skill draws on:

- [Scientific Python Development Guide — packaging](https://learn.scientific-python.org/development/guides/packaging-simple/)
  (Henry Schreiner et al.) — the modern `[project]` reference, plus the
  `sp-repo-review` checks (PP004 no `requires-python` cap, PP007 license field vs
  classifiers).
- [pyOpenSci — Python Package Guide](https://www.pyopensci.org/python-package-guide/).
- Henry Schreiner — [Should You Use Upper Bound Version Constraints?](https://iscinumpy.dev/post/bound-version-constraints/)
  (why to avoid caps).
- Hynek Schlawack — [Testing & Packaging](https://hynek.me/articles/testing-packaging/)
  (the `src/` layout) and his tools
  [`hatch-fancy-pypi-readme`](https://github.com/hynek/hatch-fancy-pypi-readme)
  and [`build-and-inspect-python-package`](https://github.com/hynek/build-and-inspect-python-package).
- James Bennett — [Python packaging: use the "src" layout](https://www.b-list.org/weblog/2023/dec/15/python-packaging-src-layout/).
- PyPA — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).

See the repository [`README.md`](../../README.md) for per-agent setup.
