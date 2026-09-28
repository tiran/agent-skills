# Primer — why type annotations are useful

A short case for why annotating and shipping types is worth the effort, for when a
maintainer needs convincing before the work in `SKILL.md`.

## What annotations buy you

- **Bugs caught before runtime.** A checker flags wrong argument types, `None` where a
  value is required, typos in attributes, and mismatched returns — statically, without
  executing the path. These are exactly the errors that otherwise surface as production
  `AttributeError`/`TypeError`.
- **Machine-checked documentation.** A signature `def load(p: Path) -> Config` states
  the contract and can't drift from the code the way a docstring does — the checker
  fails if it lies.
- **Editor tooling.** Completion, go-to-definition, inline signatures, and safe
  rename/refactor all rely on types; they degrade to nothing on `Any`.
- **Refactoring at scale.** Types turn a large change into a checkable one: rename a
  field or change a return type and the checker enumerates every site to fix.
- **A contract for consumers.** For a *library*, shipping types (`py.typed` + stubs) is
  a force multiplier — every downstream user's checker and editor benefit from work you
  do once. An unmarked package is `Any` for all of them (the whole point of this skill).

## What the evidence and experts say

Three well-known sources, spanning empirical, industrial, and design rationale:

- **Empirical — Gao, Bird & Barr, *"To Type or Not to Type: Quantifying Detectable
  Bugs in JavaScript"* (ICSE 2017).** A controlled study that reintroduced fixed public
  bugs and found a static type system would have caught **~15%** of them — direct
  evidence that types prevent a measurable share of real defects. (JavaScript/TypeScript,
  but the mechanism — annotations + a static checker — is the same one Python's typing
  provides.) <https://earlbarr.com/publications/typestudy.pdf>
- **Industrial — Dropbox, *"Our journey to type checking 4 million lines of Python"*
  (2019, Jukka Lehtosalo et al.).** The landmark real-world case: gradually typing a
  multi-million-line codebase with mypy, and *why* they invested — catching bugs,
  improving refactoring confidence and developer velocity at scale.
  <https://dropbox.tech/application/our-journey-to-type-checking-4-million-lines-of-python>
- **Design rationale — [PEP 484](https://peps.python.org/pep-0484/) (Guido van Rossum,
  Jukka Lehtosalo, Łukasz Langa).** The rationale behind Python type hints: *gradual*
  typing — annotations are optional, incremental, and have no runtime effect — so a
  project adopts them where they pay off without an all-or-nothing rewrite.

## The honest caveats

- **Types rot unless a checker runs.** Annotations that aren't enforced by mypy/pyright/
  ty/pyrefly in CI drift out of sync and become misleading — worse than none. Step 5.
- **Gradual, not total.** You don't need 100% coverage; annotate the public surface and
  the error-prone core first, and raise strictness incrementally (`reference/annotating.md`).
- **Cost is real but front-loaded.** The annotation/stub pass is genuine work; the
  payoff accrues on every later change and to every downstream user.
