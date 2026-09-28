---
name: ship-type-information
description: >-
  Ship complete, verified type information for a Python package. Add annotations to
  untyped code (autotyping, infer-types, pyrefly infer, MonkeyType), drop the
  py.typed marker (PEP 561), and generate .pyi stubs for compiled C/C++/Rust
  extensions (nanobind stubgen, pybind11-stubgen, mypy stubgen, pyo3-stub-gen;
  __text_signature__ for hand-written C). Verify with mypy, pyright
  (--verifytypes), ty, and pyrefly plus stubtest, then package the stubs so the built
  wheel actually carries them. Pairs with pybind11-to-nanobind,
  port-to-python-limited-api, and port-to-free-threaded-python. Use when asked to add
  type annotations, ship py.typed, generate or fix .pyi stubs for a C extension, make
  a package typed, or fix "module is untyped" / Any results downstream.
---

# Ship type information

**Status: Experimental** — grounded in PEP 561, the typing spec, and the current
stub-generation tooling (linked below); the workflow is a new draft. Have a human
review the generated annotations and stubs — every generator produces *drafts*.

Make a package's types **real, complete, verified, and shipped** so downstream users
and their checkers see actual signatures instead of `Any`. Three problems, often
combined: untyped Python source (add annotations), compiled extensions that are
opaque to type checkers (ship `.pyi` stubs), and types that exist but never reach
users (declare with `py.typed` and package them). This skill covers all three and the
verification that keeps them honest.

## Why bother

An extension module or an un-marked package types as `Any` for every consumer:
incorrect calls pass silently, editors give no completion, and the annotations you
*did* write reach no checker. `py.typed` + stubs turn that into real static checking
across mypy, pyright, ty, and pyrefly — a one-time cost that every downstream user
benefits from. Stubs are also **Python-version-agnostic**, so one set covers an abi3
/ stable-ABI wheel across all versions. For the fuller case (and expert sources to cite
when convincing a maintainer), see `reference/why-types.md`.

## Authoritative sources (if this skill disagrees, they win)

- [PEP 561](https://peps.python.org/pep-0561/) — distributing and packaging type information.
- Typing spec — [distributing type information](https://typing.readthedocs.io/en/latest/spec/distributing.html).
- [mypy stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) / [stubtest](https://mypy.readthedocs.io/en/stable/stubtest.html).
- [nanobind — typing & stubs](https://nanobind.readthedocs.io/en/latest/typing.html);
  [pybind11-stubgen](https://github.com/pybind/pybind11-stubgen);
  pyright [type completeness / `--verifytypes`](https://microsoft.github.io/pyright/#/typed-libraries?id=verifying-type-completeness).

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it: work in a
> project-local `.venv` with **uv** (`uvx` for one-off tools); never touch
> global/user site-packages; get existing code committed to VCS before editing (ask
> the user); don't commit/push without approval (never straight to `main`); keep
> comments terse. Auto-generated annotations and stubs are **drafts — review them.**

**Bundled references — open each at the step that cites it:**

- `reference/why-types.md` — a primer on why annotations are worth it, with expert
  sources (empirical, industrial, and PEP 484 rationale) — for convincing a maintainer.
- `reference/annotating.md` — adding annotations to untyped Python (autotyping,
  infer-types, `pyrefly infer`, MonkeyType, com2ann, ruff/pyupgrade); static-vs-runtime
  trade-off; strictness ramp.
- `reference/stubs.md` — `.pyi` stubs for compiled extensions per binding (nanobind,
  pybind11, PyO3, Cython `stubgen-pyx`, mypy `stubgen`), hand-written C
  (`__text_signature__`), pattern files, placement, the CI freshness gate.
- `reference/verify-and-ship.md` — checkers (mypy / pyright `--verifytypes` / ty /
  pyrefly), `stubtest`, PEP 561 packaging (inline vs stubs-beside vs stub-only dist),
  and verifying the built wheel carries the type files.

**Definition of done:** the package ships `py.typed` (or a stub-only distribution);
compiled extensions have committed `.pyi` that `stubtest` validates against the
runtime module; mypy, pyright, ty, and pyrefly pass; `pyright --verifytypes` reports
the intended completeness; the built wheel actually contains the type files; and a CI
gate keeps stubs fresh. Nothing committed without the user's OK.

## 1. Assess the current state

Establish what's there before changing anything:

- **Shape** — pure-Python, or compiled extensions (C/C++/Cython/Rust)? Which binding
  (nanobind / pybind11 / raw CPython API / Cython / PyO3)? That picks the stub tool.
- **Declared?** Is there a `py.typed` marker and a `Typing :: Typed` classifier? Are
  there existing `.pyi` files?
- **Baseline** — run a checker over the package and over a *consumer* import, and get
  the completeness score:
  ```bash
  uvx pyright --verifytypes <import_name> --ignoreexternal
  ```
  Note what resolves to `Any`/`Unknown` (untyped defs vs the opaque extension).

Decide scope: annotate untyped Python (step 2), stub the extensions (step 3), or both
— then declare (4), verify (5), ship (6).

## 2. Annotate untyped Python

Only if there's untyped Python source. **Deterministic first, review always** — every
tool emits drafts. From `reference/annotating.md`:

1. **Obvious cases** — `autotyping` (None/bool returns, trivial params) across the tree.
2. **Static inference** — **`pyrefly infer`** (formerly `autotype`) and/or `infer-types`
   add argument/return types without running code (deterministic).
3. **Dynamic gaps** — `MonkeyType` (via `pytest-monkeytype`) records types your test
   suite exercises that static analysis can't resolve; apply, then review.
4. **Modernize** — `com2ann` for legacy type comments; `ruff`/`pyupgrade` for modern
   syntax (PEP 604 `X | None`, PEP 585 `list[...]`, `collections.abc` over `typing`
   aliases), gated on the project's `requires-python` floor (**3.11 is a good default
   today**; 3.10 is the floor for bare `X | Y` at runtime — see `reference/annotating.md`).
5. **Ramp strictness** — get clean at the default level, then tighten per-module toward
   strict; fix, don't blanket-`ignore`.

**Untyped dependencies** leak `Any` into your code. At the import boundary, cheapest
first: install published stubs (`types-<pkg>` / `<pkg>-stubs`), else write local stubs
in a `stubs/` dir, else wrap the dep in a small **typed facade**, else suppress narrowly
(per-module `ignore_missing_imports`).

**Model structured data** (independent of the above) — prefer a real type over a bare
`dict`/`tuple` for JSON/config/records: a **`TypedDict`** to describe dict-shaped data,
or a **`@dataclass`** / attrs / pydantic when you own the model. See
`reference/annotating.md`.

## 3. Generate stubs for compiled extensions

Checkers don't import compiled modules, so ship `.pyi`. Pick the generator by binding
(details, commands, and pattern-file examples in `reference/stubs.md`):

| Binding | Generator |
| --- | --- |
| **nanobind** | `nanobind`'s stubgen / `nanobind_add_stub` (best fidelity via `__nb_signature__`) — defer to [`pybind11-to-nanobind`](../pybind11-to-nanobind/SKILL.md) |
| **pybind11** | `pybind11-stubgen` |
| **Rust / PyO3** | `pyo3-stub-gen` |
| **Cython** | `stubgen-pyx` (parses source, keeps your PEP 484 annotations; `bint`→`bool`) |
| **hand-written C / fallback** | `mypy stubgen` (runtime-introspects; most types default to `Any`) |

For **hand-written C**, expose `__text_signature__` (a signature line in the method's
docstring) so introspection tools recover the signature, and ship a hand-written `.pyi`
for the types. (CPython's Argument Clinic emits `__text_signature__` for the stdlib but
is a CPython-internal tool, not supported for third-party use — hand-write the docstring
signature instead.) **Patch** what generators can't express
(overloads, tuple-widening, `None`-returning getters, version strings) via nanobind
pattern files or manual edits.

## 4. Declare the types (PEP 561)

From `reference/verify-and-ship.md`:

- Add an **empty `py.typed`** marker file in the package root — required for checkers
  to read *either* inline annotations *or* adjacent `.pyi` beside the modules.
- **Inline** (pure Python) vs **stubs beside modules** (compiled: `.pyi` next to the
  `.so`, `py.typed` present) vs a **stub-only distribution** (`<pkg>-stubs`) when the
  stubs must live apart or you're typing a third-party package you don't own.
- The `partial\n` marker is **stub-only-package-specific**: a partial `<pkg>-stubs`
  distribution puts `partial\n` in its `py.typed` so checkers merge it with the runtime
  package. An **inline** package's `py.typed` is empty — there is no inline "partial"
  marker; unannotated code simply infers or falls back to `Any`.
- Add the `Typing :: Typed` classifier (see
  [`modernize-python-metadata`](../modernize-python-metadata/SKILL.md)).

## 5. Verify

Types are only real if a checker confirms them:

- **Run all four** — `uvx mypy <pkg>`, `uvx pyright <pkg>`, `uvx ty check`,
  `uvx pyrefly check` — from a consumer's perspective; libraries shipping stubs
  benefit from the cross-check (they disagree at the edges).
- **`pyright --verifytypes <pkg> --ignoreexternal`** — the type-completeness score;
  drive it up to the intended level.
- **`stubtest`** — `uvx --from mypy stubtest <import_name>` checks each `.pyi` matches
  the runtime module (missing/extra/mismatched symbols); the decisive stub QA.
- **CI freshness gate** — regenerate stubs and fail if the committed ones differ; pin
  the generator **and** Python version (output formatting changes between releases).

## 6. Package & ship, then verify the artifact

Types that aren't in the wheel don't exist:

- Include `py.typed` **and** every `.pyi` in the wheel — `package-data` / `MANIFEST.in`
  (setuptools), `force-include` / default (hatchling), `install_sources` (meson-python),
  maturin `include`. `reference/verify-and-ship.md` has the per-backend snippets.
- **Build and inspect the wheel** (`uv build`, then unzip / `check-wheel-contents`):
  confirm `py.typed` and the `.pyi` files are actually present at the right paths.
- Stubs are Python-version-agnostic — one set ships in an abi3 / stable-ABI wheel and
  covers every version.
