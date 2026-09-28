# Verify and ship type information

Covers step 4 (declare, PEP 561), step 5 (verify), and step 6 (package + inspect).

## Declaring types (PEP 561)

A checker only reads a package's types if the package **declares** them. Three shapes:

- **Inline** (pure Python) — annotations in the `.py` files + an **empty `py.typed`**
  marker in the package root.
- **Stubs beside modules** (compiled) — `.pyi` next to the `.so`, plus `py.typed`.
  Checkers read adjacent stubs *only* when `py.typed` is present.
- **Stub-only distribution** — a separate `<pkg>-stubs` package (PEP 561 naming) when
  the stubs must live apart, or when typing a third-party package you don't own
  (contribute to `typeshed` instead if it's stdlib/popular). A `-stubs` package uses a
  `<pkg>-stubs/` dir; a *complete* one needs no `py.typed`, while a **partial** one MUST
  include `py.typed` containing `partial\n` so checkers merge it with the runtime
  package.

The `partial\n` marker is **specific to stub-only packages** (above) — it is not an
inline mechanism. An **inline** package's `py.typed` is empty (its content is
irrelevant); unannotated parts simply infer or fall back to `Any`. Add the
`Typing :: Typed` classifier via [`modernize-python-metadata`](../../modernize-python-metadata/SKILL.md).

## Verify with the checkers

Run all four — they disagree at the edges, and library authors want the cross-check:

```bash
uvx mypy <import_name>
uvx pyright <import_name>
uvx ty check                       # Astral; fast, still 0.x — pin it
uvx pyrefly check                  # Meta; stable
```

**Type completeness** (for a library that advertises `py.typed`):

```bash
uvx pyright --verifytypes <import_name> --ignoreexternal
```

reports a percentage and lists every symbol that's `Unknown`/partially known. Drive it
to the intended level; `--ignoreexternal` excludes types re-exported from deps you don't
control.

**`stubtest`** — the decisive check that a `.pyi` matches the *runtime* module (catches
missing, extra, or mismatched symbols that a checker alone won't):

```bash
uvx --from mypy stubtest <import_name>
# allow known, intentional gaps:
uvx --from mypy stubtest <import_name> --allowlist stubtest-allowlist.txt
```

`stubtest` imports the module, so run it in the built/installed environment. It's fast
enough for CI.

## Package the type files into the wheel

Types that aren't in the wheel don't ship. Per backend:

- **hatchling** — `.pyi` and `py.typed` under `src/<pkg>/` are included by default;
  if pruned, add `[tool.hatch.build.targets.wheel] force-include` or `artifacts` for
  generated `.pyi`.
- **setuptools** — `package_data = {"<pkg>": ["py.typed", "*.pyi", "**/*.pyi"]}` (and
  `MANIFEST.in` for the sdist).
- **meson-python** — `py.install_sources('src/<pkg>/py.typed', 'src/<pkg>/my_ext.pyi', subdir: '<pkg>')`.
- **maturin** — include the `.pyi`/`py.typed` beside the module (Cargo `include` /
  project layout); maturin ships `<pkg>/*.pyi` when present.

Generated `.pyi` (from the build) must be added as build artifacts, not just source.

## Verify the built artifact

Confirm the files actually landed:

```bash
uv build
uvx check-wheel-contents dist/*.whl          # flags surprises
python -m zipfile -l dist/*.whl | grep -E 'py\.typed|\.pyi'
```

You should see `<pkg>/py.typed` and every `<pkg>/**/*.pyi`. Stubs are
Python-version-agnostic, so a single set ships in an abi3 / stable-ABI wheel and serves
every interpreter version (pairs with
[`port-to-python-limited-api`](../../port-to-python-limited-api/SKILL.md) and
[`port-to-torch-stable-abi`](../../port-to-torch-stable-abi/SKILL.md)).

## CI

Wire into the release/CI pipeline
([`secure-python-release-pipeline`](../../secure-python-release-pipeline/SKILL.md)): run
the four checkers + `stubtest` in the lint job, and the stub **freshness gate**
(`reference/stubs.md`) so committed `.pyi` can't drift from the code.
