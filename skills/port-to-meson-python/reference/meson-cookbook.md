# Meson cookbook for meson-python

Common `meson.build` patterns, the `[tool.meson-python]` settings, config-
settings, and the setuptools→Meson mapping. Cited from `SKILL.md`; keep the
workflow lean and look here for the "how".

References: [Meson Python module](https://mesonbuild.com/Python-module.html),
[`[tool.meson-python]`](https://mesonbuild.com/meson-python/reference/pyproject-settings.html),
[config-settings](https://mesonbuild.com/meson-python/reference/config-settings.html).

## Getting the Python installation

```meson
py = import('python').find_installation(pure: false)   # pure:false => platlib (has compiled code)
# pure: true for a pure-Python package (rare with meson-python)
```

## Installing what goes in the wheel

Only **installed** targets/files land in the wheel.

```meson
# compiled extension → package dir
py.extension_module('_core', ['src/_core.c', 'src/util.c'],
    install: true,
    subdir: 'mypkg',
    include_directories: include_directories('src/include'),
    dependencies: [dep_foo],
    c_args: ['-DUSE_FOO=1'],
)

# individual pure-Python files
py.install_sources('mypkg/__init__.py', 'mypkg/api.py', subdir: 'mypkg')

# a whole subtree (e.g. a package with data files), minus junk
install_subdir('mypkg', install_dir: py.get_install_dir(), exclude_files: ['*.pyc'])

# arbitrary data files
install_data('mypkg/data/table.bin', install_dir: py.get_install_dir() / 'mypkg/data')
```

## Dependencies (prefer discovery over hard-coded paths)

```meson
dep_foo = dependency('foo')                      # pkg-config or CMake
dep_thr = dependency('threads')
zlib    = dependency('zlib', required: false)    # optional
cc      = meson.get_compiler('c')
m_dep   = cc.find_library('m', required: false)  # bare library, no .pc file
np_inc  = run_command(py, '-c', 'import numpy; print(numpy.get_include())',
                      check: true).stdout().strip()
```

## Generated sources (Cython, protobuf, custom)

```meson
# Cython: enable the language, then just list .pyx as sources
project('mypkg', 'c', 'cython')
py.extension_module('_fast', 'mypkg/_fast.pyx', install: true, subdir: 'mypkg')

# arbitrary codegen
gen = custom_target('version_py',
    output: 'version.py',
    command: [py, files('tools/gen_version.py'), '@OUTPUT@'],
    install: true,
    install_dir: py.get_install_dir() / 'mypkg',
)
```

## Options (user-configurable build knobs)

```meson
# meson.options (or meson_options.txt)
option('use_cuda', type: 'boolean', value: false)
```

```meson
if get_option('use_cuda')
    add_languages('cuda')
    # ...
endif
```

Set per build with `-Csetup-args=-Duse_cuda=true` (step 7).

## `[tool.meson-python]` settings

| Key | Meaning |
| --- | --- |
| `limited-api` | `true` → build an abi3 wheel (ABI tag `abi3`). Reverts to false if `-Dpython.allow_limited_api=false`. |
| `editable-verbose` | Verbose output during rebuild-on-import. |
| `meson` | Path to the `meson` executable/script (or `MESON` env var). |
| `args.setup` | Extra args to `meson setup`. |
| `args.compile` | Extra args to `ninja`. |
| `args.install` | Extra args to `meson install`. |
| `args.dist` | Extra args to `meson dist`. |
| `wheel.exclude` / `wheel.include` | fnmatch globs to drop/keep installed files (last resort, e.g. subprojects). |
| `allow-windows-internal-shared-libs` | Relocate internal DLLs on Windows (no RPATH there). |

## config-settings (`pip -C…` / `build -C…`)

One `-C` per argument; repeat the key for multiple values:

| Key | Forwarded to |
| --- | --- |
| `setup-args` | `meson setup` (e.g. `-Csetup-args=-Dfoo=bar`) |
| `compile-args` | `ninja` (e.g. `-Ccompile-args=-j8`) |
| `install-args` | `meson install` |
| `dist-args` | `meson dist` |
| `build-dir` | keep/select the Meson build directory (`builddir` also accepted) |
| `editable-verbose` | verbose editable rebuilds (`true`/`false`) |

```bash
pip install . -Csetup-args=-Dfoo=bar -Csetup-args=-Dbaz=qux -Ccompile-args=-j8
```

## setuptools → Meson mapping

| setuptools (`setup.py`) | Meson |
| --- | --- |
| `Extension('_x', ['a.c'])` | `py.extension_module('_x', ['a.c'], install: true, subdir: 'pkg')` |
| `include_dirs=[...]` | `include_directories: include_directories(...)` |
| `libraries` / `library_dirs` | `dependencies: [dependency(...)]` / `cc.find_library(...)` |
| `define_macros=[('F','1')]` | `c_args: ['-DF=1']` |
| `extra_compile_args` / `extra_link_args` | `c_args:`/`cpp_args:` / `link_args:` |
| `packages` / `py_modules` | `py.install_sources(...)` / `install_subdir(...)` |
| `package_data` / `MANIFEST.in` (data) | `install_data(...)` / `install_subdir(...)` |
| Cython in `cmdclass` | add `'cython'` language, list `.pyx` sources |
| `setuptools_scm` version | `version: run_command(py, '-m', <vcs tool>, ...)` (SKILL step 5) |
| `python setup.py build_ext --inplace` | `pip install --no-build-isolation -e .` |
| `python setup.py bdist_wheel` | `uv build` (or `python -m build`) |

## sdist contents

meson-python builds the sdist from the Meson project via `meson dist`, which
uses the VCS file list — commit everything the build needs (all sources,
`meson.build`, `meson.options`). Tune with `tool.meson-python.args.dist` and
Meson's own dist mechanisms. The sdist embeds `PKG-INFO` with the frozen
version, which the VCS-version fallback (SKILL step 5) reads when there is no
`.git`.
