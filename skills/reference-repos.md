# Reference repositories

Real projects the skills here are grounded in — useful when extending a skill or
checking a recommendation against a working example. Practices drift, so **read
the current source before copying**; a repo listed under one topic often does the
others well too.

## My projects (tiran)

| Repo | Backend | Worth studying for |
| --- | --- | --- |
| [`tiran/pycxxfilt`](https://github.com/tiran/pycxxfilt) | meson-python | Compiled C++ extension via Meson, VCS versioning (`vcs-versioning`), full CI + `scorecard` + `codeql`. Template for `port-to-meson-python`. Also a cross-ABI C++ symbol de-mangler (Itanium + MSVC + Rust) — used in the `port-to-torch-stable-abi` symbol audit. |
| [`tiran/zipwire`](https://github.com/tiran/zipwire) | hatchling + hatch-vcs | Pure-Python packaging, tag-triggered `release.yml` with Trusted Publisher. Template for `secure-python-release-pipeline`. |
| [`tiran/retread`](https://github.com/tiran/retread) | hatchling + hatch-vcs | Same secure-release shape as zipwire; a second worked example. |
| [`tiran/kvcached`](https://github.com/tiran/kvcached) (fork) | setuptools + C++/CUDA | My stable-ABI port work on kvcached, upstream at [`ovg-project/kvcached`](https://github.com/ovg-project/kvcached). Basis for `port-to-torch-stable-abi`. |
| [`Quansight/torch-abi-audit`](https://github.com/Quansight/torch-abi-audit) | — | Cross-format, pure-Python object-file symbol reader (`objectfile.py`): defined vs undefined symbols from ELF / Mach-O / PE via pyelftools/macholib/pefile, dispatched by file magic — reads any arch/OS from one host, no native toolchain. Reference for `crypto-fips-audit`'s binary-inspection reader and the `port-to-torch-stable-abi` symbol audit. |

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

## Limited API / stable ABI (abi3)

The deterministic tooling behind
[`port-to-python-limited-api`](port-to-python-limited-api/SKILL.md). There is **no**
automatic static→heap-type rewriter — that step stays a guided manual edit — but the
mechanical parts (API modernization, verification) are well-covered.

| Repo | Author | Worth studying for |
| --- | --- | --- |
| [`python/pythoncapi-compat`](https://github.com/python/pythoncapi-compat) | Victor Stinner (PyPA) | A single `pythoncapi_compat.h` header that back-fills modern C API (`Py_NewRef`, `Py_SET_TYPE`, `PyModule_AddObjectRef`, …) onto old Pythons, plus `upgrade_pythoncapi.py`, a regex-based rewrite script. What lets one code base compile from a very low floor upward (step 5). Back-fills API; does **not** prove abi3-safety — that's abi3audit. |
| [`pypa/abi3audit`](https://github.com/pypa/abi3audit) | Trail of Bits / PyPA | Scans a `.so`, wheel, or whole PyPI history for symbols outside the declared abi3 floor. Nothing in pip/CPython enforces that an `abi3`-tagged wheel is actually clean, so this is the authoritative verification (step 9); ToB's survey found ~1 in 6 abi3 wheels mistagged. |
| [`Quansight/torch-abi-audit`](https://github.com/Quansight/torch-abi-audit) | Quansight | Cross-format object-file symbol reader (`nm -D` fallback for the audit); also listed under *My projects*. Pairs with the Quansight *[CPython ABI](https://labs.quansight.org/blog/python-abi-abi3t)* write-up that grounds `reference/background.md`. |

**Real-world adopters** (worked examples for `reference/background.md`; a Sept 2026
scan found 17 abi3 users in the top 360 PyPI packages):

| Repo | Floor | Worth studying for |
| --- | --- | --- |
| [`giampaolo/psutil`](https://github.com/giampaolo/psutil) | `cp36` | Hand-written C at the lowest floor in the survey — one wheel back to 3.6. The C-extension case this skill targets. |
| [`protocolbuffers/protobuf`](https://github.com/protocolbuffers/protobuf) | `cp310` | C++ (`upb`) abi3 wheel **plus** a `py3-none-any` pure fallback — install succeeds where no binary matches. |
| [`jquast/wcwidth`](https://github.com/jquast/wcwidth) | `cp310` | A formerly pure-Python library's [pure→C-extension transition](https://github.com/jquast/wcwidth/commit/b7a3098bd087c6d04776c44c00fe4298299cd793) (optional `build_ext`, pure fallback). The "verify the artifact, not the tag" example. |
| [`pyca/cryptography`](https://github.com/pyca/cryptography) | `cp311` | Rust/PyO3 (maturin): `cp311-abi3` for GIL builds + version-specific `cp3XXt` free-threaded wheels — the transition table in the wild. Also under *Compiled extensions & ABI*. |

## Free-threading (no-GIL)

Grounding for [`port-to-free-threaded-python`](port-to-free-threaded-python/SKILL.md).
The **authorities are the CPython docs and the community porting guide**, not a tool;
the trackers give real adoption data.

| Resource | Author | Worth studying for |
| --- | --- | --- |
| [py-free-threading.github.io](https://py-free-threading.github.io/) | Quansight & the FT community | The definitive porting guides — [Python](https://py-free-threading.github.io/porting/) and [extensions](https://py-free-threading.github.io/porting-extensions/) (`Py_mod_gil`, critical sections, `PyMutex`, borrowed-ref hazards, TSan, `pytest-run-parallel`) — plus the per-package [tracking](https://py-free-threading.github.io/tracking/) table. The primary source for this skill. |
| [CPython free-threading HOWTOs](https://docs.python.org/3/howto/free-threading-python.html) | CPython | The [runtime](https://docs.python.org/3/howto/free-threading-python.html) and [C-API](https://docs.python.org/3/howto/free-threading-extensions.html) guides — detection (`sys._is_gil_enabled()`, `Py_GIL_DISABLED`), the GIL-re-enable behavior, and the authoritative extension API. |
| [PEP 703](https://peps.python.org/pep-0703/) / [PEP 803](https://peps.python.org/pep-0803/) | Sam Gross / Petr Viktorin | PEP 703 (making the GIL optional): the refcount/layout internals that explain *why* borrowed refs and globals race. PEP 803 (`abi3t`): the free-threaded stable ABI, handed to `port-to-python-limited-api`. |
| [hugovk.dev/free-threaded-wheels](https://hugovk.dev/free-threaded-wheels/) | Hugo van Kemenade | Daily-updated adoption tracker over the top 360 extension packages (detects the `cp3Xt` tag). Grounds the "~70% already ship a FT wheel" figure in `reference/background.md`. |
| [`Quansight-Labs/pytest-run-parallel`](https://github.com/Quansight-Labs/pytest-run-parallel) | Quansight | Runs an existing pytest suite from many threads (`--parallel-threads=auto`) — the cheapest race-finder (SKILL step 7). Pairs with ThreadSanitizer for the authoritative check. |

**Real-world ports** (source-verified Sept 2026 against the local checkouts noted;
they double as **stable-ABI** references — see the abi3 section above):

| Repo | Studied at | Free-threading lessons | Stable-ABI axis |
| --- | --- | --- | --- |
| [`numpy/numpy`](https://github.com/numpy/numpy) | 2.6.0.dev | Version-guarded `Py_mod_gil` slot; portable `PyMutex`/`PyThread_type_lock` lock macro (`npy_argparse.c`); critical-section + double-checked cache fill (`convert_datatype.c`); `NPY_TLS` scratch buffers (`dragon4.c`); C11 atomics; a **borrowed-ref CI linter** (`tools/ci/check_c_api_usage.py`) with `// noqa: borrowed-ref OK`; import-must-not-re-enable-GIL release gate; TSan CI (instruments OpenBLAS) + suppressions; **deliberately does not lock `ndarray`** and says so. | `meson.build` sets `Py_LIMITED_API='3.13'` on GIL builds, **blanks it on FT** (no abi3 before abi3t) — the abi3-vs-abi3t interaction in the wild. |
| [`scipy/scipy`](https://github.com/scipy/scipy) | main | Project-wide Cython `-Xfreethreading_compatible=True` in `scipy/meson.build`; the **non-reentrant-library playbook** — rewrite SAVE/COMMON state to reentrant (`ARNAUD_state_s`, VODE→C), serialize with a per-handle lock (Qhull), or **detect-and-refuse** (`IntegratorConcurrencyError`); `scipy.sparse` **documented as not thread-safe**; `SCIPY_TLS` + `threading.local()` caches; `pytest-run-parallel` + `thread_unsafe`/`parallel_threads_limit` markers + barrier helper. | Ships version-specific `cp3Xt`; same abi3/FT mutual-exclusion pre-3.15. |
| [`PyO3/pyo3`](https://github.com/PyO3/pyo3) | 0.29 | Free-threaded **by default since 0.28** (`gil_used = true` opts out); `pyo3::sync` toolbox (`PyMutex`, `PyOnceLock`, `MutexExt::lock_py_attached`) after `GILProtected` was removed; `with_critical_section` = the C macros; `#[cfg(Py_GIL_DISABLED)]`; runtime "Already borrowed" panics; the 0.26 `with_gil`→`attach` renames. | `abi3`/`abi3-pyXX` features for one wheel across GIL Python versions; **0.29 adds `abi3t`** (PEP 803) for the free-threaded stable ABI on 3.15+ — abi3 is silently downgraded to a version-specific FT build before then. |

Also worth reading: **CPython** itself (`Include/critical_section.h`, `pylock.h`,
ported stdlib modules like `Objects/listobject.c`, `Modules/_collectionsmodule.c`),
**Cython** (the `freethreading_compatible` directive + `docs/src/userguide/freethreading.rst`),
and **nanobind** (`docs/free_threaded.rst`, `nb::ft_mutex`/`ft_object_guard`, split-mode
`abi3t`). See each skill's `reference/` files for the `file:line` citations.

## Crypto / FIPS auditing

Grounding for [`crypto-fips-audit`](crypto-fips-audit/SKILL.md). The **authorities
on FIPS itself are NIST and Red Hat** (linked from that skill's `SKILL.md`), not
any tool — the repo below is a reference for evidence-gathering *mechanics*, not
for FIPS policy interpretation.

| Repo | Author | Worth studying for |
| --- | --- | --- |
| [`EmilienM/wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan) (Apache-2.0) | Emilien Macchi (Red Hat) | Deterministic scanner that gathers crypto evidence from built wheels — Python AST + ELF/Mach-O/PE symbols & strings (`pyelftools`), Go build info, Rust crate paths, embedded SBOM — behind a data-driven ruleset with a FIPS lens. The reference implementation for the skill's binary-inspection step (linkage posture model, "banner needs corroboration"). Docs: <https://my1.fr/wheel-crypto-scan/>. **Credit it when using its output**; treat its docs/ruleset as authoritative on mechanism, not on FIPS. |
| [`openshift/check-payload`](https://github.com/openshift/check-payload) (Apache-2.0) | Red Hat / OpenShift | The Go-and-container counterpart: scans a container payload, node, or local binary and validates the FIPS build regime. Its `internal/validations/validations.go` `validateGo*` chain is the skill's reference for the Go decision tree (native Go FIPS module #5247 vs. golang-fips OpenSSL bridge; **CGO required for the bridge, skipped for the native module**; dynamic link, `strictfipsruntime`, `no_openssl`). Built for RHSB-2023-001. Authoritative on the Go/OpenShift build mechanics, not on FIPS policy. |
| [`sethmlarson/truststore`](https://github.com/sethmlarson/truststore) | Seth Michael Larson | Verifies against the OS trust store through an `ssl.SSLContext` drop-in (`truststore.SSLContext`; `inject_into_ssl()` for apps) — the default in pip 24.2+, Python 3.10+. The remedy the skill recommends for a bundled-CA (system-integration) finding. |

## Build backends (by example)

- **uv-build / hatchling / flit** — pure-Python: `pypa/flit`, hynek's repos.
- **meson-python** — `tiran/pycxxfilt` (small, clean); numpy/scipy for scale only.
- **scikit-build-core** — [`scikit-build/scikit-build-core`](https://github.com/scikit-build/scikit-build-core) sample projects (CMake-based C/C++/CUDA).
- **maturin** (Rust/PyO3, the modern default) — [`pyca/cryptography`](https://github.com/pyca/cryptography), [`astral-sh/ruff`](https://github.com/astral-sh/ruff), `astral-sh/uv`, `pydantic/pydantic-core`, `huggingface/tokenizers`.
- **setuptools-rust** (Rust inside a setuptools build — use when you need setuptools' flexibility) — [`pyca/bcrypt`](https://github.com/pyca/bcrypt), plus the [`PyO3/setuptools-rust`](https://github.com/PyO3/setuptools-rust) `examples/`. Even [`PyO3/maturin`](https://github.com/PyO3/maturin) bootstraps in two phases (`build-backend = "bootstrap"`): setuptools-rust builds a minimal maturin, which then builds the full-featured maturin.
