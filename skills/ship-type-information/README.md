# Skill: ship type information

Make a Python package's types **real, complete, verified, and shipped** — so
downstream users and their type checkers see actual signatures instead of `Any`. Three
problems, often combined: untyped Python source, compiled extensions that are opaque to
checkers, and types that exist but never reach users.

Covers **annotating untyped code** (`autotyping`, `infer-types`, `pyrefly infer`,
`MonkeyType`, `com2ann`), the **`py.typed`** marker and [PEP 561](https://peps.python.org/pep-0561/)
packaging, **`.pyi` stubs for C/C++/Rust extensions** (nanobind stubgen,
`pybind11-stubgen`, `mypy stubgen`, `pyo3-stub-gen`; `__text_signature__` for
hand-written C), **verification** with **mypy / pyright (`--verifytypes`) /
ty / pyrefly** plus **`stubtest`**, and confirming the built **wheel** actually carries
the type files.

**Status: Experimental** — grounded in PEP 561, the typing spec, and current stub
tooling; the workflow is a new draft. Review generated annotations and stubs (they're
drafts).

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The 6-step workflow + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/why-types.md` | Primer on why annotations are worth it, with expert sources (Gao–Bird–Barr ICSE 2017, Dropbox, PEP 484). |
| `reference/annotating.md` | Adding annotations to untyped Python — static tools (autotyping, `pyrefly infer`, infer-types, com2ann, ruff) vs runtime trace (MonkeyType), and the strictness ramp. |
| `reference/stubs.md` | `.pyi` stubs for compiled extensions per binding (incl. Cython `stubgen-pyx`), hand-written C (`__text_signature__`), pattern files, placement, the CI freshness gate. |
| `reference/verify-and-ship.md` | Declaring types (PEP 561), the four checkers + `--verifytypes` + `stubtest`, packaging the type files, and verifying the built wheel. |

## Related

- [`pybind11-to-nanobind`](../pybind11-to-nanobind/) — nanobind's stubgen is the
  best-fidelity stub source; this skill defers nanobind detail there.
- [`port-to-python-limited-api`](../port-to-python-limited-api/) /
  [`port-to-torch-stable-abi`](../port-to-torch-stable-abi/) — one stub set serves an
  abi3 / stable-ABI wheel across all Python versions.
- [`port-to-free-threaded-python`](../port-to-free-threaded-python/) — pairs when
  shipping a typed free-threaded extension.
- [`modernize-python-metadata`](../modernize-python-metadata/) — the `Typing :: Typed`
  classifier.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — run the
  checkers, `stubtest`, and the stub-freshness gate in CI.

## Acknowledgments

This skill distills the work of many people and projects:

- The **mypy / typeshed** team — [`stubgen`](https://mypy.readthedocs.io/en/stable/stubgen.html),
  [`stubtest`](https://mypy.readthedocs.io/en/stable/stubtest.html), and the PEP 561
  reference implementation.
- **Eric Traut** / **Microsoft** — [pyright](https://github.com/microsoft/pyright) and
  `--verifytypes` type-completeness scoring.
- **Astral** — [`ty`](https://github.com/astral-sh/ty); **Meta** — [Pyrefly](https://github.com/facebook/pyrefly)
  (checker **and** `pyrefly infer`) and [MonkeyType](https://github.com/Instagram/MonkeyType).
- **Wenzel Jakob** — [nanobind](https://github.com/wjakob/nanobind) stubgen (`__nb_signature__`);
  **Sergei Izmailov** — [`pybind11-stubgen`](https://github.com/pybind/pybind11-stubgen);
  the **PyO3** project — `pyo3-stub-gen`.
- **Jelle Zijlstra** — [`autotyping`](https://github.com/JelleZijlstra/autotyping);
  the **`com2ann`** / **`infer-types`** authors.
- **Larry Hastings** and the **CPython** team — Argument Clinic and `__text_signature__`.
- The **PEP 561** authors (Ethan Smith, Ivan Levkivskyi) and the typing-spec maintainers.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list.

See the repository [`README.md`](../../README.md) for per-agent setup.
