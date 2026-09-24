# agent-skills

Portable, agent-neutral skills and playbooks for coding tasks (Python, PyTorch,
and systems work). Each skill is a small folder of Markdown with a defined
workflow, on the open Agent Skills standard — so the same files work across
Claude Code, Codex, and other coding agents.

## How these were written

The skills and their reference material are **AI-generated, but grounded** — not
invented. They are distilled from real project migrations, upstream
contributions, the current PyPA and tool documentation, and writing by other
packaging practitioners, then cross-checked against those sources and reviewed by
hand — informed by two decades of Python experience, including work as a CPython
core developer. The recommendations reflect established practice, not just model
output. Treat them as a well-sourced starting point, follow the linked authoritative docs
when in doubt, and see each skill's **Status** for how battle-tested it is. The
projects they draw on are listed in
[`skills/reference-repos.md`](skills/reference-repos.md).

## Skills

| Skill | Status | What it does |
| --- | --- | --- |
| [`choose-python-build-backend`](skills/choose-python-build-backend/) | Exp | Recommend the right **build backend** (uv-build, flit, hatchling, meson-python, scikit-build-core, maturin, setuptools) by purelib/platlib, static/dynamic metadata, and language — with migration context. |
| [`port-to-scikit-build-core`](skills/port-to-scikit-build-core/) | Exp | Migrate a package's build from bespoke `setup.py` to **scikit-build-core + CMake** ([PEP 517](https://peps.python.org/pep-0517/)/[621](https://peps.python.org/pep-0621/), standards-based wheels, editable installs). |
| [`port-to-meson-python`](skills/port-to-meson-python/) | Exp | Build a package with the **meson-python + Meson** backend, or port one off `setup.py` ([PEP 517](https://peps.python.org/pep-0517/)/[621](https://peps.python.org/pep-0621/), VCS versioning, abi3 wheels). |
| [`modernize-python-metadata`](skills/modernize-python-metadata/) | Exp | Improve packaging **metadata** and move it into a PEP 621 `[project]` table — readme, **SPDX license**, classifiers, well-known URLs, dependency groups, no version caps. |
| [`port-to-python-limited-api`](skills/port-to-python-limited-api/) | Exp | Port a hand-written C/C++ extension to the **Limited API / stable ABI** — one **abi3** wheel across Python versions instead of one per version; optionally target 3.15 **abi3t** for free-threaded builds. |
| [`port-to-free-threaded-python`](skills/port-to-free-threaded-python/) | Exp | Make a package work on the **free-threaded (no-GIL)** CPython build ([PEP 703](https://peps.python.org/pep-0703/)) and **declare support** so import doesn't re-enable the GIL — thread-safety pass, `Py_mod_gil`, `cp3Xt` wheels, TSan. Fixes simple races, reports the rest. |
| [`pybind11-to-nanobind`](skills/pybind11-to-nanobind/) | Exp | Port a C++ extension's bindings from **pybind11 to nanobind** — smaller/faster bindings and one **abi3** wheel across Python versions. |
| [`port-to-torch-stable-abi`](skills/port-to-torch-stable-abi/) | Beta | Port a compiled PyTorch C++/CUDA/ROCm extension to the **stable ABI** (one wheel across Torch versions), then assess Python **abi3**. |
| [`secure-python-release-pipeline`](skills/secure-python-release-pipeline/) | Exp | A secure **GitHub Actions** build/release pipeline — sdist + wheels (cibuildwheel), **Trusted Publisher** to PyPI, minimal permissions, zizmor. |
| [`crypto-fips-audit`](skills/crypto-fips-audit/) | Exp | Audit a Python package — and any **C/C++/Go/Rust** it ships — for its cryptography: inventory usage, find **insecure/weak crypto**, and assess **FIPS 140-3** compliance. Source-first, confirmed against the built artifact. Gathers evidence; does not certify. |

**Status** reflects how battle-tested a skill is:

- **Stable** — applied across many projects; workflow and references verified.
- **Beta** — built from real, source-verified cases and used on a few; solid but
  expect rough edges, and check its output.
- **Experimental** (`Exp` in the table) — early draft, not yet run end-to-end.

All skills share a common [`skills/GUARDRAILS.md`](skills/GUARDRAILS.md) —
operating rules the agent follows unless you say otherwise: use uv + a project
`.venv` (never global installs), don't delete content or commit/push without
approval, ask before heavy installs/compiles, and match the project's style.

## Install

### Claude Code

This repo is a Claude Code plugin marketplace:

```text
/plugin marketplace add tiran/agent-skills
/plugin install tiran-skills@tiran
```

#### Updating

New skills and fixes land as commits. To pull them into an existing install:

```text
/plugin marketplace update tiran     # git-pulls this repo
/reload-plugins                      # apply in the current session
```

This plugin carries **no `version` field**, so Claude Code tracks it by commit
SHA — every `marketplace update` that pulls a new commit refreshes the install,
with no version bump to remember. If a refresh seems stuck,
`rm -rf ~/.claude/plugins/cache` and re-run the update.

### Codex

Either install it as a plugin from the plugin browser (`/plugins` inside Codex —
the repo ships a portable `plugin.json`), or use a skill locally by linking it
into a path Codex scans (`.agents/skills/` up to the repo root, or
`~/.agents/skills/` for all projects):

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/skills/port-to-torch-stable-abi" ~/.agents/skills/
```

### Any other agent

Point the agent at a skill's `SKILL.md` and have it follow the steps. Nothing
here depends on a specific agent framework.

## Using a skill

Once installed, just describe the task — the agent matches it to a skill via the
descriptions in the table above and follows that `SKILL.md`. For example:

```text
Which build backend should I use for my Cython + CUDA project?
```

triggers [`choose-python-build-backend`](skills/choose-python-build-backend/). Or
point an agent straight at a skill file:

```text
Follow skills/port-to-scikit-build-core/SKILL.md to migrate this package's build.
```

## Layout

```text
agent-skills/
├── AGENTS.md                 # instructions for agents (CLAUDE.md symlinks to it)
├── plugin.json               # portable Codex plugin manifest
├── .claude-plugin/           # Claude Code marketplace + plugin metadata
└── skills/
    ├── GUARDRAILS.md         # shared operating rules every skill links to
    └── <skill-name>/
        ├── SKILL.md          # the workflow — the skill's source of truth
        └── reference/        # tables and background, referenced on demand
```

## Improving a skill

Improvements to the existing skills — corrections, clearer steps, better
references — are welcome. Conventions live in [`AGENTS.md`](AGENTS.md); each skill
is one directory under `skills/<name>/` with a single `SKILL.md` (the workflow)
and supporting material under `reference/`.

Draft with AI if it helps, but **read it and cut it down before you commit** —
unedited AI text is long, unchecked, and expensive to review.

## License

[Apache-2.0](LICENSE).
