# Dependencies, version constraints, and dependency groups

Backs steps 7–9. Authoritative:
[dependency specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/),
[dependency groups (PEP 735)](https://packaging.python.org/en/latest/specifications/dependency-groups/),
[against version caps](https://iscinumpy.dev/post/bound-version-constraints/).

## Version constraints: floors, not caps

```toml
dependencies = [
  "requests>=2.28",            # floor = oldest version you actually support/test
  "packaging>=23",
  "click>=8.1,!=8.1.4",        # exclude a specific KNOWN-broken release
]
```

**Set a lower bound, avoid an upper bound.** The reasoning (from
iscinumpy.dev and Brett Cannon):

- An **over-tight cap is unfixable downstream.** If you publish `numpy<2` and a
  user needs numpy 2, they cannot override your constraint — they must wait for
  *you* to release a fix. A missing cap, by contrast, anyone can pin around.
- **Caps silently backsolve.** A resolver meeting `foo<3` (when foo 3 is current)
  doesn't error — it quietly installs an ancient `foo` that satisfies the cap,
  giving users old, possibly insecure code instead of a clear failure.
- **Caps don't compose** in flat dependency systems: two packages with
  overlapping-but-different caps on a shared dependency can make the set
  unsolvable.
- Only cap a version you have **evidence** breaks you (a known incompatibility),
  and treat it as a temporary TODO with a comment — remove it once you've adapted.
  Prefer excluding the exact bad release (`!=1.2.3`) over guessing a range.

### `requires-python`

```toml
requires-python = ">=3.11"     # floor only
```

**Never put an upper bound on `requires-python`** (`>=3.11,<3.15` is a trap). Python
version caps "only cause hard failures": a cap makes your package flatly
uninstallable on a newer interpreter even when it would have worked, and the whole
ecosystem breaks in ways users can't override. Set the floor to the oldest Python
you test; drop end-of-life versions when you stop testing them.

**Prefer a floor of `>=3.11` for new or newly-modernized projects.** Python 3.10
reaches end-of-life (end of security support) in **October 2026**, so a fresh
`>=3.10` floor is already near the end of its life; 3.11 has security support
through October 2027. Only support an EOL version if you have a concrete reason
(a large install base you can measure). Check current support windows at
<https://devguide.python.org/versions/>.

Applications that need a fully reproducible environment should use a **lock file**
(uv, pip-tools, Poetry) — that's the right place for exact pins, not library
metadata.

## Extras vs dependency groups — decide by audience

| | `[project.optional-dependencies]` (extras) | `[dependency-groups]` (PEP 735) |
| --- | --- | --- |
| For whom | **Users** enabling an optional feature | **Developers** of this project |
| Install | `pip install mypkg[postgres]` | `pip install --group test` (or uv) |
| In published metadata? | **Yes** (`Provides-Extra`) | **No** — never shipped to PyPI |
| Installable as an extra by others? | Yes | No |
| Typical contents | `postgres`, `redis`, `cli` feature deps | `test`, `lint`, `docs`, `dev` toolchains |

Rule of thumb: if it's a knob your **users** turn on, it's an **extra**; if it's
your **team's** tooling, it's a **dependency group**. Historically people abused a
`dev` extra for this — dependency groups are the purpose-built replacement (they
don't leak into your package's public metadata).

```toml
[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.1"]
redis    = ["redis>=5"]

[dependency-groups]
test = ["pytest>=7", "coverage[toml]>=7"]
lint = ["ruff>=0.4", "mypy>=1.8"]
docs = ["sphinx>=7", "furo"]
# compose groups with include-group:
dev  = [
  { include-group = "test" },
  { include-group = "lint" },
  { include-group = "docs" },
]
```

`include-group` lets `dev` pull in the others so `--group dev` installs
everything, with each tool set still usable on its own.

### Caveat: the consumer must support PEP 735

`[dependency-groups]` only helps if whatever installs the set understands it
(pip ≥ 25.1 `--group`, or uv). Some tools consume **extras** and cannot read a
group, so relocating a dev set there breaks their wiring:

- **Hatch environments** are the common trap. An env's `features` key reads
  `[project.optional-dependencies]` (extras) **only** —
  `[tool.hatch.envs.test].features = ["test"]` pulls the `test` *extra*, and there
  is no way to point `features` at a `[dependency-groups]` group. Moving that set
  from `optional-dependencies` to `dependency-groups` silently leaves the env with
  nothing installed. Hatch added a *separate* env key for this in **1.16.0**
  (2025-11-24); **1.16.3** fixes it for envs not marked as builders, so
  **require Hatch ≥ 1.16.3**:

  ```toml
  [dependency-groups]
  test = ["pytest>=7", "pytest-cov>=4"]

  [tool.hatch.envs.test]
  dependency-groups = ["test"]     # NOT features = ["test"]; needs Hatch >= 1.16.3
  ```

  So the move is possible, but it's a two-part change (relocate the set **and**
  rewire every env from `features` to `dependency-groups`) plus pinning the
  **Hatch ≥ 1.16.3** floor wherever Hatch is constrained (a CI install, a `hatch`
  entry in a dev group, contributor docs) — not a free relocation. This is a
  **Hatch** (project/env manager) version, not **hatchling** (the build backend):
  groups aren't build metadata, so the backend's version is irrelevant — only the
  env-runner's is.

  **Enforce the floor in-tree with `tool.hatch.requires-hatch`.** Hatch checks
  this specifier at runtime and refuses to run when the installed version is too
  old — better than relying on every contributor and CI step to pin the version
  by hand:

  ```toml
  [tool.hatch]
  requires-hatch = ">=1.18.0"
  ```

  **Gotcha: the `requires-hatch` field itself was only added in Hatch 1.18.0**
  (2026-08-11), and older versions **silently ignore it**. So a `requires-hatch = ">=1.16.3"`
  is unenforceable on exactly the 1.16.x/1.17.x versions it would target — they
  skip the check and then fail later with an empty env (nothing installed from
  the group), which is harder to diagnose than a clean version error. Pin
  `requires-hatch = ">=1.18.0"` (the lowest version where the mechanism actually
  bites), which also supersedes the 1.16.3 functional floor. Keep the CI install
  pins and contributor docs on the **same** `>=1.18.0` bound so there's one
  coherent floor. (`requires-hatch` value is any PEP 440 specifier set; docs:
  <https://hatch.pypa.io/latest/how-to/config/constrain-hatch/>.)
- **tox / nox / CI steps** that install `.[test]` (an extra) rather than
  `--group test` have the same problem.

Before moving a dev set out of `optional-dependencies`, grep for how it's
consumed (`features`, `.[...]`, `extras`) and migrate the consumer in the same
change — or leave it as an extra.

## `[build-system].requires` — build-time deps

```toml
[build-system]
requires = ["setuptools>=61", "Cython>=3", "numpy>=2"]   # compile-time only
build-backend = "setuptools.build_meta"
```

- List **only what's needed to build** (backend, Cython, header-providing
  packages, a VCS-version tool) — not runtime deps.
- By default builds are **isolated** (PEP 517): the backend and everything in
  `requires` are installed into a fresh throwaway environment. This is why
  `open("README.md").read()` and reading the version by importing the package at
  build time are fragile — the build doesn't run in your dev environment.

### Special case: building against a pre-installed dependency (e.g. Torch)

Some compiled extensions must be built against the **exact** version of a heavy
dependency that's already installed (ABI compatibility) — PyTorch extensions are
the classic example. Two things follow, and they're a deliberate exception to the
"isolate and pin everything" defaults:

1. **Don't list that dependency in `[build-system].requires`.** If you did,
   isolated builds would fetch a *possibly different* version into the build
   environment and compile against the wrong ABI.
2. **Build with isolation off:** users run
   `pip install . --no-build-isolation` (or `--no-build-isolation-package torch`)
   so the compile sees the already-installed dependency. The build environment
   must therefore have the backend **and** that dependency present beforehand.

Document this in the README ("install torch first, then
`pip install --no-build-isolation .`"). It's the one place where relying on a
pre-installed, un-pinned build dependency is correct rather than a smell.
