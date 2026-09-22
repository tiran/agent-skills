# Reference repositories

Real projects the skills here are grounded in — useful when extending a skill or
checking a recommendation against a working example. Practices drift, so **read
the current source before copying**; a repo listed under one topic often does the
others well too.

## My projects (tiran)

| Repo | Backend | Worth studying for |
| --- | --- | --- |
| [`tiran/pycxxfilt`](https://github.com/tiran/pycxxfilt) | meson-python | Compiled C++ extension via Meson, VCS versioning (`vcs-versioning`), full CI + `scorecard` + `codeql`. Template for `port-to-meson-python`. |
| [`tiran/zipwire`](https://github.com/tiran/zipwire) | hatchling + hatch-vcs | Pure-Python packaging, tag-triggered `release.yml` with Trusted Publisher. Template for `secure-python-release-pipeline`. |
| [`tiran/retread`](https://github.com/tiran/retread) | hatchling + hatch-vcs | Same secure-release shape as zipwire; a second worked example. |
| [`tiran/kvcached`](https://github.com/tiran/kvcached) (fork) | setuptools + C++/CUDA | My stable-ABI port work on kvcached, upstream at [`ovg-project/kvcached`](https://github.com/ovg-project/kvcached). Basis for `port-to-torch-stable-abi`. |

## Hynek Schlawack

The reference author for modern, no-nonsense Python packaging. His blog
([hynek.me](https://hynek.me/articles/)) and repos are the source for much of the
metadata and release guidance here.

| Repo | Worth studying for |
| --- | --- |
| [`python-attrs/attrs`](https://github.com/python-attrs/attrs) | Exemplary `pyproject.toml`, hatchling + hatch-vcs + hatch-fancy-pypi-readme, typing, docs, CI matrix. |
| [`hynek/structlog`](https://github.com/hynek/structlog) | Same house style; dependency groups, nox/tox sessions. |
| [`hynek/hatch-fancy-pypi-readme`](https://github.com/hynek/hatch-fancy-pypi-readme) | Hatchling metadata plugin — composing a PyPI readme from fragments. |
| [`hynek/argon2-cffi`](https://github.com/hynek/argon2-cffi) | cffi-based compiled binding done cleanly. |

Key posts: *Sharing Your Labor of Love* (PyPI), *Semantic Versioning Will Not
Save You*, *Python Application Dependency Management*.

## Scientific-Python packaging (Henry Schreiner, Ralf Gommers)

The authorities on native-code and CMake/Meson-based packaging. Their guides and
templates are the modern reference for anything beyond pure-Python.

| Resource | Worth studying for |
| --- | --- |
| [`scientific-python/cookie`](https://github.com/scientific-python/cookie) (Schreiner) | The modern packaging template + [Development Guide](https://learn.scientific-python.org/development/) — one project scaffold across ~13 backends (hatchling, flit, pdm, setuptools, maturin, meson-python, scikit-build-core). Was `scikit-hep/cookie`. |
| [`scientific-python/repo-review`](https://github.com/scientific-python/repo-review) (Schreiner) | `sp-repo-review` — lints a repo against that guide; a checklist made executable. |
| [`scikit-build/scikit-build-core`](https://github.com/scikit-build/scikit-build-core) (Schreiner) | The CMake build backend itself; see [`pybind/scikit_build_example`](https://github.com/pybind/scikit_build_example) for a minimal C++ project. |
| [`pypackaging-native`](https://pypackaging-native.github.io/) (Gommers) | The reference write-up on *why* native packaging is hard — ABI, GPUs/CUDA, BLAS, cross-compilation, wheel limits. Read before designing a native build. |
| [`mesonbuild/meson-python`](https://github.com/mesonbuild/meson-python) (Gommers) | The Meson backend behind the numpy/scipy migrations. |

## PyPA & packaging tooling (canonical)

| Repo | Worth studying for |
| --- | --- |
| [`pypa/sampleproject`](https://github.com/pypa/sampleproject) | The reference PEP 621 `[project]` table. |
| [`pypa/cibuildwheel`](https://github.com/pypa/cibuildwheel) | The way to build/test wheels across platforms in CI. |
| [`pypa/hatch`](https://github.com/pypa/hatch) / [`pypa/build`](https://github.com/pypa/build) | Backend + PEP 517 frontend internals and their own packaging. |
| [PyPI Trusted Publishers docs](https://docs.pypi.org/trusted-publishers/) | OIDC publishing — the target state of `secure-python-release-pipeline`. |
| [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish) (Sydorenko) | The blessed Trusted-Publisher action — tokenless PyPI upload. |

## Other maintainers & their reference repos

| Person | Repo | Worth studying for |
| --- | --- | --- |
| Ofek Lev | [`pypa/hatch`](https://github.com/pypa/hatch) | hatchling — the reference modern project-management backend. |
| Thomas Kluyver | [`pypa/flit`](https://github.com/pypa/flit) | The minimalist pure-Python backend — smallest correct `pyproject.toml`. |
| Pradyun Gedam | [`pypa/installer`](https://github.com/pypa/installer) | Clean low-level "how a wheel is installed" library; also leads pip. |
| Paul Ganssle | [`dateutil/dateutil`](https://github.com/dateutil/dateutil), CPython | Well-run mature package; former setuptools maintainer. Sharp write-ups on versioning and *why not to invoke `setup.py` directly*. |
| Bernát Gábor | [`tox-dev/pyproject-api`](https://github.com/tox-dev/pyproject-api), [`tox`](https://github.com/tox-dev/tox), [`pypa/virtualenv`](https://github.com/pypa/virtualenv) | PEP 517 hooks done right; the `tox-dev` house style for task automation and clean multi-env layout. |

Explainers/authorities (fewer template-style repos, essential background): **Brett
Cannon** — PEP 517/518 co-author, the [snarky.ca](https://snarky.ca/) packaging
posts, `python-launcher`.

## Compiled extensions & ABI

| Repo | Worth studying for |
| --- | --- |
| [`pytorch/pytorch`](https://github.com/pytorch/pytorch) | Stable-ABI headers, lintrunner (downloads a prebuilt actionlint, no Go build). |
| [`pytorch/extension-cpp`](https://github.com/pytorch/extension-cpp) | Canonical minimal Torch C++/CUDA extension. Its `extension_cpp_stable` variant is the reference for the **stable Torch ABI** ([official note](https://pytorch.org/docs/main/notes/libtorch_stable_abi.html)) — one build across Torch versions. |
| [`pytorch/vision`](https://github.com/pytorch/vision) / [`pytorch/audio`](https://github.com/pytorch/audio) | First-party real-world stable-Torch-ABI users (`STABLE_TORCH_LIBRARY`). |
| [`wjakob/nanobind_example`](https://github.com/wjakob/nanobind_example) | nanobind bindings + one **abi3** wheel across Python versions (`wheel.py-api = "cp312"`). |
| [`pyca/cryptography`](https://github.com/pyca/cryptography) | Rust extension via **maturin**, abi3, hardened multi-platform release CI. |
| [`numpy/numpy`](https://github.com/numpy/numpy) / [`scipy/scipy`](https://github.com/scipy/scipy) | Proof meson-python scales, and the reference distutils→meson-python migration. A *scale* reference, **not a starter template** — the signal is buried in BLAS/Fortran/Cython/cross-compile complexity. For a clean small example use `tiran/pycxxfilt` or the meson-python docs. |

*Two orthogonal axes:* the **stable Torch ABI** yields one wheel across *Torch*
versions; **abi3** yields one wheel across *Python* versions. The examples above
each show one axis; combining both is what `port-to-torch-stable-abi` assembles.

## Build backends (by example)

- **uv-build / hatchling / flit** — pure-Python: `pypa/flit`, hynek's repos.
- **meson-python** — `tiran/pycxxfilt` (small, clean); numpy/scipy for scale only.
- **scikit-build-core** — [`scikit-build/scikit-build-core`](https://github.com/scikit-build/scikit-build-core) sample projects (CMake-based C/C++/CUDA).
- **maturin** (Rust/PyO3, the modern default) — [`pyca/cryptography`](https://github.com/pyca/cryptography), [`astral-sh/ruff`](https://github.com/astral-sh/ruff), `astral-sh/uv`, `pydantic/pydantic-core`, `huggingface/tokenizers`.
- **setuptools-rust** (Rust inside a setuptools build — use when you need setuptools' flexibility) — [`pyca/bcrypt`](https://github.com/pyca/bcrypt), plus the [`PyO3/setuptools-rust`](https://github.com/PyO3/setuptools-rust) `examples/`. Even [`PyO3/maturin`](https://github.com/PyO3/maturin) bootstraps in two phases (`build-backend = "bootstrap"`): setuptools-rust builds a minimal maturin, which then builds the full-featured maturin.
