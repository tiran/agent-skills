# "Why not Poetry?" — a matter of fit (and some taste)

Backs the "Poetry is out of scope" note in the skill. The honest answer is **"it's
a fine tool that doesn't match how these skills are built"** — not that Poetry is
bad. It is capable, popular, and well-designed, and it deserves real credit for
popularizing the `pyproject.toml`-centric, lockfile-driven workflow the whole
ecosystem now takes for granted. This skill points elsewhere for a mix of concrete
reasons and, frankly, some **personal taste**. Sources:
[Poetry 2.0 announcement](https://python-poetry.org/blog/announcing-poetry-2.0.0/),
[PyPA tool recommendations](https://packaging.python.org/en/latest/guides/tool-recommendations/),
[Henry Schreiner — "Should you use upper-bound version constraints?"](https://iscinumpy.dev/post/bound-version-constraints/),
[uv](https://docs.astral.sh/uv/).

## What Poetry is (and which part is "the backend")

Poetry is an **all-in-one project manager**: dependency resolution, virtualenv
management, building, and publishing behind one command. Its PEP 517 build backend
is **`poetry-core`**. `poetry-core` is a perfectly valid backend — but in practice,
choosing it means adopting the whole Poetry workflow. That coupling, more than the
backend itself, is what this skill is weighing.

## The concrete reasons this skill prefers a composable stack

- **Standards, historically.** For years Poetry stored metadata in its own
  `[tool.poetry]` table instead of the standard PEP 621 `[project]` table, so your
  metadata wasn't portable and other tools couldn't read it. **Poetry 2.0
  (January 2025) added `[project]` support**, which closes most of this gap — credit
  where it's due. But a lot of existing projects and tutorials still use the old
  table, and the standards-first path is now first-class in the alternatives.
- **Upper-bound defaults.** `poetry add` writes caret (`^`) constraints by default,
  and Poetry has historically pushed an upper bound on the Python version too
  (`python = "^3.x"` → `<4.0`). Speculative caps like these are actively harmful in
  **reusable libraries**: they propagate to every consumer and cause unsolvable
  resolution conflicts downstream — the definitive write-up is Henry Schreiner's
  [*Should You Use Upper Bound Version Constraints?*](https://iscinumpy.dev/post/bound-version-constraints/).
  You *can* override the defaults, but you're working against the grain of the tool.
- **Compiled extensions.** `poetry-core` has no supported story for C/C++/Cython/Rust
  extensions — only an unofficial, undocumented `build.py` hook. If you ship native
  code, the purpose-built backends (meson-python, scikit-build-core, maturin) are the
  answer, and this skill routes there.
- **All-in-one coupling.** Bundling resolver + venv + build + publish behind one
  tool — with, until the PEP 751 lock standard, a Poetry-specific lockfile — is a
  genuine strength for some teams and a lock-in for others. These skills favor pieces
  you can swap independently.

## The taste part, said plainly

Reasonable people land differently here, and much of this is preference rather than
a defect. The house style behind these skills is a **composable, standards-first
stack**: **uv** for environments, locking, and resolution; a **purpose-built PEP 517
backend** (hatchling / meson-python / scikit-build-core / maturin) for building; and
**PEP 621 metadata** any tool can read. Poetry's integrated, batteries-included
philosophy is a legitimate alternative — we're not claiming it's wrong, only that
it's not the shape these skills are designed around.

## When Poetry still makes good sense — including for new products

- **Applications and services you deploy rather than publish.** You're the leaf node:
  a lockfile for reproducible deploys and a single integrated tool are exactly what
  you want, and caret caps hurt no one downstream. This is Poetry's sweet spot.
- **Pure-Python projects** where you value Poetry's UX and don't need compiled builds.
- **A team already fluent in Poetry** with working CI — the switching cost isn't
  worth paying just to match someone's house style. A backend/tool swap stays
  reversible later (that's the point of PEP 517).

If you do use it for a new product, two things keep you out of trouble: adopt
**Poetry 2.0's `[project]` table** so your metadata stays portable, and **loosen the
caret/Python caps** for anything you might publish as a library.

## The modern alternative

Much of Poetry's original value — a pyproject-centric, lockfile-driven, one-command
workflow — is now delivered by **uv**, which is fast, standards-native (PEP 621
metadata, PEP 751 locks), and delegates building to standard backends rather than
reimplementing one. That's why these skills default to **uv + hatchling** for pure
Python (or a compiled backend when there's native code) instead of Poetry. For
reusable libraries specifically, prefer hatchling / flit / PDM paired with uv.

## One-line guidance

- **New reusable library / package** → uv + hatchling (or meson-python /
  scikit-build-core / maturin if compiled); not Poetry.
- **New app or service you deploy** → Poetry is a reasonable choice; uv is the
  standards-first alternative worth comparing.
- **Existing Poetry project that works** → keep it; move to the `[project]` table
  (2.0) and drop speculative upper caps if you publish it.
