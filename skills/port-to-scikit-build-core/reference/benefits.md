# Why scikit-build-core + CMake over bespoke setuptools

Rationale for the migration, for humans deciding whether it is worth it. The
executable steps are in `../SKILL.md`.

The anchor is PyTorch's own switch, announced on the PyTorch dev-discuss forum:
[*"PyTorch's build is switching from setuptools to scikit-build-core, and
setup.py goes away"*](https://dev-discuss.pytorch.org/t/heads-up-pytorchs-build-is-switching-from-setuptools-to-scikit-build-core-and-setup-py-goes-away/3414)
(setup.py removed **2026-07-20**). PyTorch is the archetypal case: a CMake-driven
native core plus a large pure-Python library, historically glued together by
`setup.py`.

## The problem with setup.py for native code

setuptools is a *Python* packaging tool; it was never a native build system.
`setup.py` cannot express a real C++/CUDA dependency graph, so every hybrid
project grows its own imperative `build_ext` orchestration. Meanwhile CMake — which
*is* a native build system — cannot on its own produce wheels, sdists, or package
metadata. And the classic `setup.py` command interface (`develop`, `install`,
`bdist_wheel`) has been deprecated for years in favor of PEP 517/518/621.

scikit-build-core closes the gap: it is a maintained, standards-based PEP 517
backend purpose-built for exactly this hybrid. It drives your existing CMake build
and produces standards-compliant wheels/sdists — *"puts the build on the
interfaces the rest of the ecosystem targets."*

## Concrete benefits (from the PyTorch migration)

- **Far less bespoke code.** PyTorch retired *"over 2,000 lines of bespoke build
  orchestration"* in favor of declarative `pyproject.toml`.
- **Standards throughout.** PEP 517/518 build, PEP 621 metadata; PEP 639 license
  inclusion *"comes for free."* Works uniformly with pip, `build`, uv,
  cibuildwheel.
- **Editable installs done right.** Python sources import from your checkout while
  compiled artifacts import from the build location, so the source tree stays
  clean. Opt-in auto-rebuild on import exists (off by default).
- **Caching / incremental rebuilds unchanged.** *"The CMake cache carries over
  between builds exactly as before"*; `ccache`/`sccache` keep working.
- **Cross-platform & cross-compilation carry over** — the backend *"drives the
  same CMake build you know."*
- **Performance is neutral** *"by construction and by measurement"*: matched CI
  jobs show identical durations and byte-comparable wheel sizes.
- **CMake options are first-class**, passed per build via config-settings
  (`-Ccmake.define.USE_CUDA=ON`) instead of `--global-option` hacks.

## What does *not* change

For packages that merely build **on top of** PyTorch via
`torch.utils.cpp_extension`, nothing changes — the setuptools helpers remain and
torch keeps its runtime setuptools dependency. What breaks is direct
`python setup.py …` invocation, and any tooling that assumed compiled artifacts
live *inside* the package directory (they now come from the CMake install step).

## When it is worth it

- You have (or can write) a CMake build for the native code.
- You maintain a custom `build_ext`/`setup.py` you would rather delete.
- You want abi3 / free-threaded wheels (pairs naturally with nanobind — see
  `../SKILL.md` step 9 and the `port-to-torch-stable-abi` skill).
- You want cross-platform wheels via cibuildwheel with a declarative config.

If your extension is a single small `.c` file with no dependencies, plain
setuptools may still be simpler; the payoff grows with build complexity.
