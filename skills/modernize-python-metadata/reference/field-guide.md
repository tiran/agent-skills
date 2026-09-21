# `[project]` field guide

Full reference for the metadata fields touched by the workflow. Authoritative:
[writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/),
[core metadata](https://packaging.python.org/en/latest/specifications/section-distribution-metadata/),
[license expression](https://packaging.python.org/en/latest/specifications/license-expression/),
[well-known URLs](https://packaging.python.org/en/latest/specifications/well-known-project-urls/).

## Tool-version floors for newer fields

Newer metadata is gated on tool support — an old backend drops it, an old
uploader rejects it. Approximate floors (check each tool's changelog for exact
versions):

| Feature | Needs |
| --- | --- |
| `[project]` table (PEP 621) | setuptools ≥ 61; hatchling any recent |
| SPDX `license` + `license-files` (PEP 639, core-metadata 2.4) | setuptools ≥ 77 / hatchling ≥ 1.27; **twine ≥ 6.1** to upload |
| `readme` field | setuptools ≥ 61 |
| `[dependency-groups]` (PEP 735) | pip ≥ 25.1 or uv (resolver-side, not the backend) |
| Well-known URL rendering | PyPI-side; any backend that writes `Project-URL` |

If you can't upgrade twine/pip in the target environment, defer the PEP 639/735
pieces and do the rest (readme, URLs, classifiers, authors, dependency floors)
now — those work on much older tooling.

## Field map: setup.py / setup.cfg → `[project]`

| Old (`setup()` kwarg / `setup.cfg`) | `[project]` key | Notes |
| --- | --- | --- |
| `name` | `name` | Normalized (PEP 503); `_`/`.`/`-` runs are equivalent. |
| `version` | `version` or `dynamic=["version"]` | Prefer VCS-derived; see versioning skills. |
| `description` | `description` | One line → core-metadata `Summary`. |
| `long_description` + `_content_type` | `readme` | Drop `open(...).read()`; give a filename. |
| `python_requires` | `requires-python` | Floor only (prefer `>=3.11`; 3.10 EOL Oct 2026); no upper cap. |
| `author` / `author_email` | `authors = [{name, email}]` | List of tables. |
| `maintainer` / `maintainer_email` | `maintainers = [...]` | Only if different from authors. |
| `license` / `license_file(s)` | `license` (SPDX) + `license-files` | PEP 639; not a classifier. |
| `keywords` | `keywords = [...]` | List, not a comma string. |
| `classifiers` | `classifiers = [...]` | Drop `License ::` rows. |
| `url` / `project_urls` | `[project.urls]` | Use well-known labels (below). |
| `install_requires` | `dependencies = [...]` | Floors, no caps. |
| `extras_require` | `[project.optional-dependencies]` | User-facing extras only. |
| `entry_points` / `console_scripts` | `[project.scripts]` / `[project.gui-scripts]` / `[project.entry-points.*]` | |
| `package_data` / `include_package_data` | build-backend config | Backend-specific (e.g. `[tool.hatch.build]`). |

## readme

```toml
readme = "README.md"                                    # type inferred (.md→markdown, .rst→x-rst)
readme = { file = "README.md", content-type = "text/markdown" }
readme = { text = "Inline summary.", content-type = "text/markdown" }   # rarely needed
```

The content type becomes core-metadata `Description-Content-Type`; a wrong type
makes PyPI show raw markup. Prefer the file form so the README has a single source.

## license (PEP 639)

```toml
license = "MIT"
license = "Apache-2.0"
license = "BSD-3-Clause OR GPL-2.0-only"     # SPDX boolean expression
license = "LicenseRef-Proprietary"           # for non-SPDX / private terms
license-files = ["LICENSE*", "vendor/**/LICENSE"]
```

- `license` is an **SPDX expression string** → core-metadata `License-Expression`.
- `license-files` is a list of **globs** (relative to project root) → the files
  are packaged and listed as `License-File`.
- Do **not** also use the legacy table form (`license = {text=...}` /
  `{file=...}`) or `License ::` classifiers — both are superseded, and the
  Scientific Python guide's PP007 flags mixing `License ::` classifiers with the
  `license` field. Pick the SPDX field.
- If you omit `license-files`, most backends **auto-discover** common names
  (`LICENSE*`, `COPYING*`); set it explicitly when the files live elsewhere or you
  ship several.

## authors, maintainers

```toml
authors = [
  { name = "Ada Lovelace", email = "ada@example.com" },
  { name = "Grace Hopper" },                 # name only is fine
  { email = "team@example.com" },            # email only is fine
]
```

## classifiers

Pick from the canonical list — browse <https://pypi.org/classifiers/> or
`uvx trove-classifiers` (the `trove-classifiers` package is the machine-
readable source PyPI validates against). Commonly worth setting:

| Classifier family | Example |
| --- | --- |
| Development status | `Development Status :: 4 - Beta` |
| Intended audience | `Intended Audience :: Developers` |
| Topic | `Topic :: Software Development :: Libraries` |
| Language | `Programming Language :: Python :: 3`, `Programming Language :: Python :: 3 :: Only` |
| Tested versions | `Programming Language :: Python :: 3.12` / `3.13` / `3.14` — one row per minor you test |
| Free threading | `Programming Language :: Python :: Free Threading :: 3 - Stable` (also `2 - Beta`, `1 - Unstable`, `4 - Resilient`) |
| Typing | `Typing :: Typed` (ship a `py.typed` marker) |
| Upload guard | `Private :: Do Not Upload` (PyPI rejects → blocks accidental publish) |

Do **not** encode license here (use the `license` field). **Do** list a
`Programming Language :: Python :: 3.X` row for each minor you test: unlike
`requires-python` (a floor only), the per-version rows advertise your actual
*tested* range on the PyPI page and in metadata — a good indicator for consumers.
Keep them in lockstep with your CI matrix (add on adoption, remove on drop).
Advertise free-threaded support with the `Free Threading` classifier only once you
test the free-threaded (`Py_GIL_DISABLED`) build.

## Well-known project URLs

Labels normalize by lowercasing and stripping punctuation/whitespace, then match
a known name. Use these so PyPI renders proper icons/links:

| Well-known name | Accepted label aliases (after normalization) |
| --- | --- |
| `homepage` | homepage |
| `source` | source, repository, sourcecode, github |
| `download` | download |
| `changelog` | changelog, changes, whatsnew, history |
| `releasenotes` | releasenotes |
| `documentation` | documentation, docs |
| `issues` | issues, bugs, issue, tracker, issuetracker, bugtracker |
| `funding` | funding, sponsor, donate, donation |
| `security` | security, securitypolicy |

```toml
[project.urls]
Homepage = "https://example.com/mypkg"
Documentation = "https://mypkg.readthedocs.io"
Source = "https://github.com/you/mypkg"
Changelog = "https://github.com/you/mypkg/releases"   # GitHub Releases doubles as a changelog
Issues = "https://github.com/you/mypkg/issues"
Funding = "https://github.com/sponsors/you"
```

Label keys are limited to 32 characters in core metadata. Pointing `Changelog`
at the repo's GitHub Releases page is a low-maintenance option when there's no
hand-written changelog file. Note the well-known `homepage` label **replaces the
old top-level `url=`** from `setup.py` — there is no separate `url` key in
`[project]`; put it in `[project.urls]` as `Homepage`.

## Scripts / entry points

```toml
[project.scripts]
mycli = "mypkg.__main__:main"

[project.gui-scripts]
mygui = "mypkg.gui:main"

[project.entry-points."some.plugin.group"]
myplugin = "mypkg.plugin:factory"
```
