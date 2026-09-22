# "Why not setuptools?" — the balanced version

Backs SKILL step 4. The honest answer is **"you still can, but…"**: setuptools is
not deprecated and is a fine PEP 517 backend, yet modern backends have better
defaults for most projects, and compiled projects have specialized options that
beat it. Two further strikes weigh against it: a **backwards-compatibility record**
of frequent breaking changes and yanked releases (it's a build-time dependency, so
a bad release breaks everyone building), and **license trouble** — vendored code,
including a fork of CPython's PSF-licensed `distutils` relicensed as MIT, with
compliance reports left unaddressed for years. Sources:
[PyPA tool recommendations](https://packaging.python.org/en/latest/guides/tool-recommendations/),
[Why Hatch?](https://hatch.pypa.io/latest/why/),
[pip 24.2 editable deprecation](https://github.com/pypa/pip/issues/11457),
[setuptools parallel-build issue #3119](https://github.com/pypa/setuptools/issues/3119),
[Cython compilation guide](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html),
[Quansight PEP 517 popularity](https://labs.quansight.org/blog/pep-517-build-system-popularity),
[setuptools PyPI release history](https://pypi.org/project/setuptools/#history),
[LWN: disruptive setuptools changes](https://lwn.net/Articles/1020576/).

## What is actually deprecated (not setuptools itself)

- **Direct `setup.py` invocations** — `python setup.py sdist` / `bdist_wheel` /
  `install` / `develop` are all deprecated. Use `uv build` (or `python -m build`), `pip install`.
- **`easy_install`** and **`distutils`** (removed from the stdlib in 3.12;
  setuptools vendors a copy).
- **The legacy editable path.** `pip install -e` historically wrapped
  `setup.py develop`; PEP 660 standardized editable installs so *any* backend
  supports them. pip has been removing the setuptools-specific fallback — a
  project that doesn't support the PEP 660 mechanism risks `pip install -e`
  breaking. Fix: `requires = ["setuptools>=64"]` + `build-backend =
  "setuptools.build_meta"` in `pyproject.toml`.

`setup.py` as a *config file* for setuptools is **not** deprecated — only calling
it directly is.

## Why modern backends win for pure-Python projects

- **Safer file-inclusion defaults.** setuptools auto-discovers "anything that
  looks like a package" for wheels and needs a separate `MANIFEST.in` (custom
  syntax) for sdists — easy to ship test/tooling dirs or omit needed files.
  Hatchling takes sdist contents from `.gitignore` and is strict/explicit about
  wheel contents, erroring instead of guessing.
- **Reproducible builds** by default (setuptools guarantees this for neither
  sdists nor wheels).
- **Editable installs that support IDE static analysis** out of the box;
  setuptools needs extra config and marks some of it legacy.
- **Simpler config** — one `pyproject.toml`, no `setup.py`/`setup.cfg`/
  `MANIFEST.in` — and a proper plugin system (setuptools' extension API is
  low-level).
- **Standards + momentum.** Hatchling is the backend in PyPA's *Writing your
  pyproject.toml* worked example and, with setuptools, one of only two
  PyPA-maintained backends; it's a first-class option in the Scientific Python
  `cookie` template.

Much setuptools usage is **inertia** — configs copied from older projects — rather
than a deliberate fit.

## The parallel-build caveat (matters for compiled projects)

setuptools has **no isolation or locking against concurrent builds that share a
working directory**. Building wheels for several Python versions / extensions in
parallel from one tree can make them "trample over each other, non-deterministically
fail or have incorrect contents." Mitigation is manual (separate build dirs per
interpreter). CMake (scikit-build-core) and Meson (meson-python) handle
parallelism natively via Ninja — a concrete reason to move compiled projects.

## Release instability: breaking changes and yanks

setuptools ships **~5 major versions a year** and has a track record of
**breaking changes and broken releases** that ripple across the ecosystem —
because it's a build-time dependency, a bad release breaks *everyone building*,
not just new adopters. Concretely:

- **Repeated yanks.** The [PyPI release history](https://pypi.org/project/setuptools/#history)
  lists **seven setuptools releases yanked since early 2024** after shipping
  regressions — each leaving the "latest" version broken until a fix lands, and
  forcing downstreams to refresh pins or eat warnings
  ([example downstream fallout](https://github.com/seleniumbase/SeleniumBase/issues/1073)).
- **Breaking removals.** v72 removed `setup.py test`, which
  [Fedora estimated would break 142–196 packages](https://fedoraproject.org/wiki/Changes/Setuptools_74%2B);
  the [March 2025 incident](https://staturdays.com/2025/03/25/how-one-setuptools-release-broke-everything-and-what-we-can-learn-from-it/)
  (v78) broke builds worldwide for hours before the fix.
- **Ongoing complaints.** The tracker carries many "breaking change in X.Y"
  reports (e.g. [#3455](https://github.com/pypa/setuptools/issues/3455)), and the
  broader concern is documented at length
  ([LWN: "Recent disruptive changes from Setuptools"](https://lwn.net/Articles/1020576/)).

Purpose-built backends (hatchling, flit, uv-build) and the compiled ones
(scikit-build-core, meson-python, maturin) change far less often and are narrower
in scope, so a routine build-backend bump is much less likely to break you. If you
do stay on setuptools, keep a **lower bound** in `build-system.requires` (the
floor you need for the features you use) and **catch breakage in CI** — build on a
schedule / via Dependabot so a bad backend release shows up as a red build, not a
broken release. Add an **upper cap only for a known, documented breakage** (a
specific version that demonstrably breaks your build), and remove it once fixed
upstream — never a speculative "`<next-major`" cap, which silently freezes you on
old, unpatched build tooling. Pin CI *actions* by SHA (that's provenance, not a
version cap).

## License hygiene: long-standing, unresolved

setuptools' `distutils` is a **fork of CPython's stdlib `distutils`** —
maintained at [pypa/distutils](https://github.com/pypa/distutils) as the
foundation setuptools builds on — and it is **relicensed as MIT**
([`pyproject.toml`](https://github.com/pypa/distutils/blob/3ed42426ce6f41e9d07dc63f3315d85f19e25618/pyproject.toml#L24)).
The upstream code is CPython's, under the **PSF License**, which for a derivative
work made available to others **requires a summary of the changes made to Python**
(PSFL §3) and **terminates automatically on a material breach** (PSFL §6, see
CPython [`LICENSE`](https://github.com/python/cpython/blob/main/LICENSE)).
Dropping the PSFL and its notice for an MIT declaration is a serious
license-compliance problem at the very base of the setuptools stack.

The same pattern recurs across setuptools itself, with reports unaddressed for
years — some for nearly a decade, several still open:

- [#132](https://github.com/pypa/setuptools/issues/132) (2014) missing license
  file and [#612](https://github.com/pypa/setuptools/issues/612) (2016) license
  clarification — both long-standing.
- [#2670](https://github.com/pypa/setuptools/issues/2670) (2021) the vendored
  `distutils` ships without its PSFL notice, and
  [pypa/distutils#312](https://github.com/pypa/distutils/issues/312) (open) asks
  for the proper Python license and credits.
- [#5049](https://github.com/pypa/setuptools/issues/5049) (open) itemizes code
  under **LGPLv3, BSD, Apache, and PSFL** bundled without adequate notices.

The irony: v78's new `license-file` *validation* broke downstream builds
([#4892](https://github.com/pypa/setuptools/issues/4892)) — setuptools enforcing
license-metadata strictness on its users while its own license accounting stays
incomplete. If you have compliance obligations (redistribution, vendoring,
corporate audit), this is a real cost of depending on setuptools; purpose-built
backends carry far less third-party baggage.

## When setuptools is still the right call

- An **existing, working C/C++ extension build** using `Extension` that you don't
  want to re-express in CMake/Meson — migrating the *build* is the costly part.
- **Rust bindings** in a setuptools project via **setuptools-rust** (though new
  Rust projects should prefer maturin).
- Reliance on setuptools-only features or its large plugin ecosystem.
- You simply need it to work and it does — a backend swap is reversible later
  (PEP 517), so there's no urgency to churn a healthy build.

## One-line guidance

- **New pure-Python** → hatchling (or uv-build/flit for simple + static).
- **New compiled** → maturin (Rust) / scikit-build-core (CMake, CUDA, nanobind,
  Cython, Torch) / meson-python (Meson, C/C++/Fortran, Cython) — **not**
  setuptools.
- **Existing setuptools pure-Python** → worth modernizing (better defaults).
- **Existing setuptools C-extension that builds fine** → migrate only for a
  reason (parallel builds, abi3, CMake/Meson features), not on principle.
