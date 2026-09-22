# Reference migrations and config field guide

Two real (experimental) migrations to copy from — one classic hybrid project, one
abi3/nanobind extension. Both remove `setup.py` entirely.

## A. coremltools — CMake core + setup.py glue → scikit-build-core

Branch: <https://github.com/tiran/coremltools/tree/scikit-build-core>
(**experimental**). The migration deleted `setup.py` (~115 lines) and
`MANIFEST.in`, net-simplified `CMakeLists.txt` (−135/+46), and added a
`pyproject.toml`. Commits: *switch build backend*, *update build scripts and
docs*, *derive version from git tags with setuptools-scm*.

`pyproject.toml` essentials:

```toml
[build-system]
requires = ["scikit-build-core>=1.0", "setuptools-scm>=8.1", "numpy"]
build-backend = "scikit_build_core.build"

[project]
name = "coremltools"
dynamic = ["version"]
requires-python = ">=3.7"
license = "BSD-3-Clause"
license-files = ["LICENSE.txt"]
# ... dependencies, classifiers, urls ...

[tool.scikit-build]
cmake.version = ">=3.10.2"
cmake.build-type = "Release"
build-dir = "build/skbuild/{wheel_tag}"
wheel.packages = ["coremltools"]
# version.py is generated + gitignored, so force it into the wheel:
wheel.force-include = { "coremltools/version.py" = "coremltools/version.py" }

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.setuptools_scm"   # version-specific: no `field` key

[tool.setuptools_scm]
version_file = "coremltools/version.py"
version_scheme = "only-version"      # use the git tag verbatim (handles .devN / b1 tags)
local_scheme = "no-local-version"
```

`CMakeLists.txt` — the parts scikit-build-core depends on:

```cmake
# modern FindPython; scikit-build-core supplies the hints
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

# each extension target is installed INTO the package so it ships in the wheel
install(TARGETS milstoragepython modelpackage LIBRARY DESTINATION coremltools)
install(TARGETS coremlpython           LIBRARY DESTINATION coremltools)
install(TARGETS kmeans1d_core          LIBRARY DESTINATION coremltools/_deps/kmeans1d)
```

Takeaways: `install(... DESTINATION <pkg[/subdir]>)` is the whole packaging
contract; pure-Python (including checked-in `*_pb2.py`) comes from
`wheel.packages`; generated/gitignored files need `wheel.force-include`.

## B. kvcached (nanobind branch) — setuptools ext → CMake + nanobind + abi3

Branch: <https://github.com/tiran/kvcached/tree/nanobind-abi3> (**experimental**).
Shows the abi3 path and the tie-in with `port-to-torch-stable-abi`.

```toml
[build-system]
requires = ["scikit-build-core>=1.0", "nanobind>=2.2.0", "torch>=2.10"]
build-backend = "scikit_build_core.build"

[project]
requires-python = ">=3.9"

[tool.scikit-build]
minimum-version = "1.0"
build-dir = "build/{wheel_tag}"
wheel.packages = ["kvcached"]
cmake.version = ">=3.18"
# Auto-detected abi3: cp312-abi3 on 3.12+ (serves 3.13/3.14/...), per-version below.
wheel.py-api = "cp312"

[tool.cibuildwheel]
test-requires = ["abi3audit"]        # fail if the abi3 wheel leaks a non-stable CPython symbol
# build 3.9-3.12; skip 3.13/3.14 (covered by cp312-abi3) and free-threaded
```

```cmake
cmake_minimum_required(VERSION 3.18)
find_package(Python 3.9 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
find_package(Torch REQUIRED)         # headers + ABI flag only; never linked

# STABLE_ABI => .abi3.so on Python >=3.12, ordinary extension below
nanobind_add_module(_C STABLE_ABI NB_STATIC ${KVCACHED_SOURCES})
# CUDA: find_package(CUDAToolkit REQUIRED) and target_link_libraries as needed
install(TARGETS _C LIBRARY DESTINATION kvcached)
```

Takeaways: `nanobind_add_module(... STABLE_ABI ...)` + `wheel.py-api = "cp312"`
gives one abi3 wheel for 3.12+; `find_package(Torch)` for headers only pairs with
the stable-ABI port so torch is never linked; `abi3audit` in CI is the guardrail.

## `[tool.scikit-build]` field guide (verified from the branches above)

Full option list and defaults: the scikit-build-core [config
reference](https://scikit-build-core.readthedocs.io/en/stable/reference/configs.html).

| Field | Purpose |
| --- | --- |
| `minimum-version` | Pin scikit-build-core behavior/features. |
| `build-dir` | Build tree; use `{wheel_tag}` for per-tag incremental caches. |
| `cmake.version` | Required CMake version constraint. |
| `cmake.build-type` | `Release` / `Debug` / etc. |
| `wheel.packages` | Pure-Python packages collected from the source tree. |
| `wheel.py-api` | Limited-API/abi3 tag, e.g. `cp312` (one wheel for ≥3.12). |
| `wheel.force-include` | Ship generated/gitignored files (`.gitignore` is honored otherwise). |
| `sdist.include` / `sdist.exclude` | Curate sdist contents. |
| `editable.rebuild` | Auto-rebuild the extension on import in editable installs. |
| `[[tool.dynamic-metadata]]` | Plug a provider (e.g. setuptools-scm) for `dynamic` fields. |

Build-time overrides (no file edits): `-Ccmake.define.X=Y`, `-Ccmake.args=-DX=Y`,
`-Cbuild-dir=…`, `-Cwheel.py-api=…`.
