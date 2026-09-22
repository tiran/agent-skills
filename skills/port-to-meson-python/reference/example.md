# Worked example: pycxxfilt (meson-python + VCS version + abi3)

A real, shipping meson-python project: a small C++ extension wrapping
`c++filt`/`abi::__cxa_demangle`. Source of the patterns below:
<https://github.com/tiran/pycxxfilt> (see `meson.build` and `pyproject.toml`).

It is a compact, complete reference for three things this skill cares about:
VCS versioning computed in `meson.build`, the limited-API/abi3 setup, and the
cibuildwheel matrix.

## `pyproject.toml` (the parts that matter)

```toml
[build-system]
requires = ["meson-python>=0.17", "meson>=1.6", "vcs-versioning>=2.3.2"]
build-backend = "mesonpy"

[project]
name = "pycxxfilt"
dynamic = ["version"]          # version is not static — computed in meson.build

[tool.meson-python]
limited-api = true             # emit an abi3 wheel
```

`vcs-versioning` is a build-time dependency, not a runtime one — it exists only
so `meson.build` can call it at configure time. `dynamic = ["version"]` is
mandatory: without it, PEP 621 requires a static `version` and the build fails.

## `meson.build`: version from VCS at configure time

This is the pattern the whole skill points at (step 5). meson-python reads the
version from `project(... version: ...)`, so VCS versioning means **producing the
string during `meson setup`**:

```meson
project(
    'pycxxfilt',
    'c', 'cpp',
    meson_version: '>=1.6.0',
    # Derive the version from the latest git tag via vcs-versioning. It falls
    # back to the sdist's PKG-INFO when building outside a git checkout.
    # find_program resolves meson-python's native-file 'python' (the build
    # interpreter with the versioning deps) ahead of a bare PATH 'python3'.
    version: run_command(
        find_program('python3', 'python', version: '>= 3.11'),
        '-m', 'vcs_versioning',
        check: true,
    ).stdout().strip(),
    default_options: [
        'cpp_std=c++20',
        'b_ndebug=true',
        # ...
    ],
)
```

Why each piece matters:

- **`find_program('python3', 'python', version: '>= 3.11')`** — meson-python
  injects a *native file* pointing at the build interpreter, the one that has the
  `vcs-versioning` dependency from `build-system.requires`. Listing `python3`
  then `python` lets Meson resolve that injected interpreter ahead of an
  unrelated bare `python3` on `PATH`. The `version:` constraint guards the
  minimum.
- **`-m vcs_versioning`** — runs the tool as a module; it prints the derived
  version (git tag + distance) to stdout.
- **`check: true`** — a failed version computation aborts the build loudly rather
  than silently producing a bogus version.
- **`.stdout().strip()`** — the trailing newline would otherwise become part of
  the version string.
- **PKG-INFO fallback** — the sdist carries `PKG-INFO` with the frozen version,
  so the same `meson.build` resolves a version when built from an sdist that has
  no `.git`. Always test `pip install dist/*.tar.gz` to exercise this path.

This replaces what `setuptools-scm` does declaratively in a setuptools/
scikit-build-core project; with meson-python the computation lives in the Meson
build. Any tool that prints a version to stdout slots into the same
`run_command`.

## abi3 / limited API

pycxxfilt ships a single stable-ABI wheel per platform:

- `[tool.meson-python] limited-api = true` sets the wheel's ABI tag to `abi3`.
- The extension is built with a `limited_api` version in `meson.build` (sets
  `Py_LIMITED_API`).
- cibuildwheel opts the floor interpreter into the stable ABI:

```toml
[[tool.cibuildwheel.overrides]]
select = "cp311-*"
config-settings = { setup-args = "-Dpython.allow_limited_api=true" }
```

Building the abi3 wheel on CPython 3.11 tags it `cp311-abi3`, loadable on 3.11+.
Keep limited-API off free-threaded interpreters (they don't support it).
