# Annotating untyped Python

For adding type annotations to existing untyped **Python source** (step 2). Compiled
extensions are `reference/stubs.md`, not here. **Every tool below produces drafts —
review each change and gate with a checker.** Do it in a clean git tree so the diff is
reviewable (GUARDRAILS).

## Deterministic (static) tools — prefer these

They analyze code without running it, so output is reproducible and doesn't depend on
which paths your tests hit. Pin versions.

- **`autotyping`** — the cheap, high-confidence wins: `-> None` / `-> bool` returns,
  trivial parameter defaults, `__str__ -> str`, property setters. Fast across a whole
  tree. `uvx autotyping --safe src/`.
- **`pyrefly infer`** (formerly `autotype`) — static inference of argument/return types
  from local call sites, written back in place. Same ecosystem as the `pyrefly` checker
  (step 5). Review — maintainers explicitly recommend it.
- **`infer-types`** — CLI that infers and inserts return types.
- **`com2ann`** — translate legacy `# type:` comments into real annotations.
- **`ruff`** / **`pyupgrade`** — modernize typing syntax deterministically: `Optional[X]`
  → `X | None` (PEP 604), `typing.List` → `list` / `typing.Sequence` →
  `collections.abc.Sequence` (PEP 585), drop `from __future__ import annotations` where
  not needed. (ruff `UP`/`FA`/`TC` rules; `ANN` flags *missing* annotations.)

> **Prefer the modern style — but gate it on `requires-python`.** Default to PEP 604
> unions (`X | None`), PEP 585 built-in generics (`list[int]`, `dict[str, int]`), and
> `collections.abc` (`Iterable`, `Sequence`, `Mapping`) over the deprecated
> `typing.List`/`typing.Optional`/`typing.Union` aliases. These forms are evaluated at
> runtime, so bare `X | Y` needs **Python 3.10** (`list[int]` needs 3.9); a **3.11
> baseline is a good default today**. ruff/pyupgrade key their rewrites to the project's
> `requires-python` / `target-version`, so **set a sensible floor first** (via
> [`modernize-python-metadata`](../../modernize-python-metadata/SKILL.md)) or the
> rewrites won't apply. If the project must support **< 3.10** *and* anything evaluates
> annotations at runtime (pydantic, `@dataclass`, `typing.get_type_hints`, attrs,
> Typer), keep `from __future__ import annotations` (PEP 563) or quote the annotations —
> don't blindly drop the future-import. In `.pyi` **stubs** the modern syntax is always
> safe regardless of the runtime floor: stubs are never executed.

> **`typing_extensions` vs. raising the floor.** Newer *typing constructs* — `Self`
> (3.11), `override` (3.12), `TypeIs` (3.13), `Required`/`NotRequired` (3.11),
> `dataclass_transform` (3.11), `ReadOnly`/`deprecated`/TypeVar defaults (3.13) — are all
> **backported by [`typing_extensions`](https://typing-extensions.readthedocs.io/)** down
> to 3.9, and checkers treat `typing_extensions.X` identically to `typing.X`. So **don't
> raise `requires-python` just to use them** — keep the low runtime floor and
> `from typing_extensions import Self, override` instead. It cannot backport *syntax*,
> though: **PEP 695** type parameters (`class Box[T]:`, `def f[T]()`, `type Alias = …`)
> need a **3.12** interpreter, and PEP 604/585 evaluated at runtime need 3.10/3.9 (above)
> — those are the only reasons to bump the baseline for typing. Import from
> `typing` when the symbol exists on your floor, else from `typing_extensions`
> (a runtime dep; `TYPE_CHECKING`-only if used purely in annotations under the future
> import).

## Runtime-trace tools — fill dynamic gaps

Deterministic **given a fixed test run**, but only cover code your tests execute. Use
after the static pass, for dynamic patterns static analysis can't resolve.

- **`MonkeyType`** — traces the running suite (`sys.setprofile`) and records observed
  types, then writes them back with libcst. Hook it to tests via `pytest-monkeytype`:
  ```bash
  uv run pytest --monkeytype-output=./monkeytype.sqlite3
  uv run monkeytype apply <import_name>        # or: monkeytype stub <mod> for a .pyi
  ```
  It respects existing annotations. Caveat: it tends to emit concrete types (`list`)
  where an abstract one (`Sequence`/`Iterable`) is better — widen by hand.
- **`pyannotate`** — the older Dropbox equivalent; MonkeyType is preferred.

**Not deterministic — don't rely on for reproducible output:** ML-based inferers
(type4py, etc.). Fine as a hint source, not a build step.

## A practical order for a large untyped codebase

1. `autotyping --safe` for the obvious returns/params.
2. `pyrefly infer` and/or `infer-types` for broader static inference.
3. `MonkeyType` (via the test suite) for the dynamic gaps.
4. `com2ann` if there are legacy type comments; `ruff --fix` / `pyupgrade` to modernize.
5. **Review every diff**, widen over-narrow types, then run a checker (step 5) at the
   default level. Tighten module-by-module toward strict; fix rather than blanket-ignore.

## Untyped dependencies and imports

When a dependency has no types, everything you get from it is `Any`, which silently
spreads through your own code. Handle it **at the boundary**, cheapest first:

1. **Look for existing stubs.** Does the dep ship `py.typed` now (many do)? If not, is
   there a stub package — `types-<pkg>` (typeshed's third-party stubs) or `<pkg>-stubs`?
   Install it as a typing/dev dependency; `mypy --install-types` and pyright pick these
   up automatically. This alone fixes most cases.
2. **Write local stubs for what you use.** No published stubs → drop partial `.pyi` in a
   `stubs/` dir and point the checker at it (mypy `mypy_path = "stubs"` / `MYPYPATH`;
   pyright `stubPath`). You only need the handful of symbols you actually call; consider
   upstreaming them to `typeshed` if the library is popular.
3. **Wrap the untyped dep behind a typed facade.** Confine all use of the untyped
   library to one small adapter module whose functions carry real annotations, so `Any`
   stops at that boundary instead of leaking through the codebase. The highest-value
   structural fix.
4. **Suppress narrowly, last resort.** List the offending modules in a per-module mypy
   override instead of silencing globally:
   ```toml
   [[tool.mypy.overrides]]
   # third-party packages without type annotations or stubs
   module = ["untyped_dep", "another_dep.*"]
   ignore_missing_imports = true
   ```
   Keep the list **explicit** and prune it over time — when a dep ships types in a later
   release, drop it from the list so it starts being checked. Newer mypy also has
   per-module `follow_untyped_imports = true`, which type-*checks through* an untyped
   module (inferring what it can) rather than treating it as `Any`. The one-off form is
   `# type: ignore[import-untyped]` on the specific import. Other checkers: pyright
   `reportMissingTypeStubs`, and ty / pyrefly per-module rule suppression.

Type the loose data such a dep returns where it enters your code — see *Model
structured data* below.

## Model structured data — TypedDict or dataclass

Independent of any dependency: whenever code passes around **structured data** (JSON
payloads, config, records, `**kwargs`), prefer a real type over a bare `dict`/`tuple` —
whether the data comes from your own code or from an untyped library.

- **`TypedDict`** — to *describe* **dict-shaped data** without changing its runtime form:
  it stays a plain `dict` but gains per-key types; use `NotRequired` / `total=False` for
  optional keys. Ideal for JSON/config you receive; `cast()` or parse untyped input to it
  at the boundary:
  ```python
  from typing import TypedDict, NotRequired, cast


  class User(TypedDict):
      id: int
      name: str
      email: NotRequired[str]


  raw = get_user(uid)  # dict / Any
  user: User = cast(User, raw)  # typed from here on
  ```
- **`@dataclass`** — when you *own the model* and want a real object (attribute access,
  defaults, `frozen=True`, methods). Reach for **attrs** or **pydantic** when you need
  validation/serialization — pydantic *checks* the data at runtime, the safest boundary
  for input you don't control.

Rule of thumb: **`TypedDict` to describe dict-shaped data cheaply; `dataclass` / attrs /
pydantic to own it as a (optionally validated) object.** Either way you replace an opaque
`dict`/`Any` with a precise type.

## Strictness ramp

Don't switch on `strict` globally on day one — it buries you. Get clean at the default
level first, then raise per-module (mypy `[[tool.mypy.overrides]]` with
`disallow_untyped_defs = true`; pyright `strict` include list) as each area is
annotated. The goal is monotonic progress with a green checker at every step.
