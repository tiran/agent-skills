# Inspecting compiled binaries for problematic / vendored crypto

Companion to SKILL step 5. Can a compiled binary (C/C++/Rust/Go) be checked for
problematic or vendored crypto? Yes: read dependencies, symbols, strings, and
embedded build metadata. Grounded in the reference scanner
[`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan) (Emilien
Macchi, Red Hat, Apache-2.0), whose `linkage.py` + `binfmt/` codify this exact
question, plus the sources linked inline.

## The core question and the posture model

For each crypto library, resolve a **posture** (wheel-crypto-scan's model):

| Posture | Meaning | Typical evidence |
|---|---|---|
| **system** | links the host's validated provider | `NEEDED libcrypto.so.3` (plain soname / absolute path), not shipped in the wheel |
| **bundled** | ships a copy of the library file | copy in `*.libs/`/`.dylibs/`, or a **hash-mangled** `NEEDED libcrypto-a1b2c3.so.3` |
| **static** | crypto **compiled into** the extension | **defined** `EVP_*` symbols + a real copy marker (see below) |
| **unknown** | uses crypto, copy unresolved | *imported* crypto symbols with no provider; `openssl-sys`; ambiguous Go |
| **opaque** | couldn't tell at all | stripped static object, no symbols/deps/strings — **report, never "clean"** |

Three ways a package carries its own crypto, all of which must be caught: a copy in
a vendor dir, a dependency on a **hash-renamed** library, or crypto **compiled
straight in** (no file, no dependency — `cryptography` 42+ does this). A check that
only looks for vendor directories is wrong in the worst direction.

**The load-bearing lesson:** a defined OpenSSL-API symbol *or* an `OpenSSL x.y.z`
version banner **does not prove a static OpenSSL copy** — AWS-LC and BoringSSL
implement the same API under the same names and emit the same banner. Require
**corroboration** before calling something static OpenSSL (below).

## Two ways to read a binary

**CLI tools** (quick, interactive) and **Python libraries** (scriptable, no
shelling out). The CLI is fine for a spot check on the host's own platform; reach
for the Python libs for anything else.

**Why the Python libs matter: they cross the arch/OS boundary.** `readelf`, `nm`,
`otool`, and `dumpbin` are host-native — from a Linux CI box you can't `otool` a
macOS `.dylib` or `dumpbin` a Windows `.pyd`, and a foreign-arch ELF may defeat the
host toolchain. `pyelftools`/`macholib`/`pefile` are pure-Python parsers: they read
**any** format for **any** arch/OS from one host, dispatched by file magic. That's
what lets a single Linux runner audit a whole multi-platform wheel set (the reason
wheel-crypto-scan and `torch-abi-audit` both parse in-process rather than shell
out).

- **`pyelftools`** — ELF: `ELFFile`, iterate sections by `sh_type`
  (`SHT_DYNAMIC`/`SHT_DYNSYM`/`SHT_SYMTAB`), read `DT_NEEDED`, `.dynsym`/`.symtab`
  entries and `st_info` binding (defined vs `SHN_UNDEF`). (wheel-crypto-scan's only
  binary dep.)
- **`macholib`** — Mach-O: load commands, dylib dependencies, symbols; handles
  fat/universal binaries (union the per-arch headers).
- **`pefile`** — PE/`.pyd`: import/export directories, delay-load, forwarders.

Match the same **symbol prefixes and version-banner strings** listed below,
regardless of which reader you use.

### A self-contained cross-format reader (`uv run`)

This skill ships [`scripts/scan_crypto.py`](../scripts/scan_crypto.py) — a
[PEP 723](https://peps.python.org/pep-0723/) inline-metadata script. `uv run`
installs the parsers into a throwaway env (no project or venv setup) and it reads
ELF / Mach-O / PE alike, from any host:

```bash
uv run scripts/scan_crypto.py path/to/_ext.so path/to/_ext.pyd   # any format, any host
uv run scripts/scan_crypto.py -v path/to/_ext.dylib              # -v: every symbol
```

For each file it reports the three posture signals: **linked** crypto libraries
(`DT_NEEDED` / PE imports / Mach-O load commands), **defined** vs **imported**
crypto symbols, and version-banner **strings** (an in-process `strings`-style pass
that also catches a bundled copy with no dynamic dependency). Read **defined**
crypto symbols as compiled-in (static), **imported** as calls to an external copy
(posture table below) — the same defined-vs-imported split the CLI `nm` gives, but
portable. Its symbol/string patterns cover OpenSSL & forks, **NSS, GnuTLS,
libgcrypt, nettle**, libsodium, `ring`, and AWS-LC (see the provider table below).
[`torch-abi-audit`](https://github.com/Quansight/torch-abi-audit)'s `objectfile.py`
is the fuller, tested parser this is modelled on (adds `PyInit_*` detection and
more per-format edge cases). A banner alone is not proof of a static copy — see the
`OPENSSLDIR` corroboration rule below.

> **Do not use `ldd` on untrusted input** — it loads/executes the target. Use
> `readelf -d` / `patchelf --print-needed` (or `pyelftools`) instead.

## ELF (.so)

```bash
readelf -d libfoo.so | grep -E 'NEEDED|SONAME|RPATH|RUNPATH'   # dependencies
nm -D libfoo.so | grep -E 'EVP_|SSL_|RAND_|BN_|OSSL_|PK11_|NSS_|gnutls_|gcry_|nettle_'  # exported syms
nm  libfoo.so 2>/dev/null | grep -Ei 'ring_|GFp_|aws_lc|goboring|nettle_'  # local .symtab too
strings -a libfoo.so | grep -Ei 'OpenSSL [0-9]|OPENSSLDIR|BoringSSL|AWS-LC|libsodium|GnuTLS|Libgcrypt|nettle|NSS '
readelf -d libfoo.so | grep -Ei 'libcurl|libpq|libmysqlclient|libmariadb|libzmq|libsodium|libkrb5|gssapi|librdkafka|libsybdb'  # client libs that pull crypto one hop away
```

- **Dependency posture:** plain soname not shipped → **system**; **absolute**
  `NEEDED /usr/lib64/libcrypto.so.3` → always **system** (no RPATH resolution);
  **hash-mangled** basename → **bundled**; a plain soname that **resolves to a file
  the wheel ships** (delocate copies without renaming) → **bundled**.
- **Defined vs imported:** a **defined** (`nm`: `T`/`t`/`D`) crypto symbol means a
  copy compiled in; **imported** (`U`) means it calls an external copy it doesn't
  ship → **unknown**. Read `.symtab` for definitions even when `.dynsym` is present
  (a version script can hide a static copy from `.dynsym` — e.g. `cryptography`
  50.0.1 has 776 local `EVP_*` defs).
- **Banner needs a copy marker:** treat an `OpenSSL x.y.z` banner as a real
  compiled-in copy **only** when the **`OPENSSLDIR: `** string is also present
  (`OpenSSL_version()` emits both together; a header macro emits only the banner).
  Banner alone → **unknown**.

OpenSSL markers to grep: prefixes `EVP_`, `SSL_CTX_`, `OSSL_PROVIDER_`,
`X509_STORE_`, `PKCS5_PBKDF2_`, `RSA_`, `EC_KEY_`, `BN_`; exact `OPENSSL_init_ssl`,
`RAND_bytes`, `HMAC_Init_ex`. Fork tells: BoringSSL `OPENSSL_is_boringssl`,
`BORINGSSL_*`; AWS-LC `OPENSSL_IS_AWSLC`, `AWSLC_VERSION_NUMBER_STRING`. FIPS
BoringCrypto: **`BORINGSSL_integrity_test`** (defined) is the power-on self-test —
match it only as a *defined* symbol.

### Provider markers — all validated system providers

The same symbol/string/soname reasoning applies to the other RHEL/Fedora
providers, not just OpenSSL (see `native-crypto.md` for their validation status).
The scanner matches all of these; grep by hand with the same patterns:

| Provider | Symbol prefixes | Sonames (`NEEDED`) | Banner / string tell |
|---|---|---|---|
| **OpenSSL** & forks | `EVP_`, `SSL_`, `OSSL_`, `RSA_`, `EC_KEY_`, `BN_` | `libcrypto.so`, `libssl.so` | `OpenSSL x.y.z` + `OPENSSLDIR:` |
| **NSS** | `PK11_`, `NSS_`, `SECMOD_`, `SECKEY_`, `SECOID_` | `libnss3`, `libssl3`, `libsmime3`, `libnssutil3`, and the modules `libsoftokn3` / `libfreebl3` (+ NSPR `libnspr4`) | `NSS <ver>`; look for `NSS_GetSystemFIPSEnabled` |
| **GnuTLS** | `gnutls_` | `libgnutls.so` (pulls in nettle/hogweed) | `GnuTLS` |
| **libgcrypt** | `gcry_` | `libgcrypt.so` (+ `libgpg-error`) | `Libgcrypt` |
| **nettle** (GnuTLS's low-level lib) | `nettle_`, `_nettle_`; PK in **hogweed** | `libnettle.so`, `libhogweed.so` | `nettle` |

Notes that flip a verdict:
- **NSS's validated module is `libsoftokn3` / `libfreebl3`** (the "NSS Cryptographic
  Module"), not `libnss3` as a whole — a bundled `libfreebl3` is the boundary
  escape to flag. NSS also honours its own policy file, not `/etc/crypto-policies`
  directly (`native-crypto.md`).
- **libgcrypt is validated on RHEL 8/9 but deprecated / no longer validated on
  RHEL 10** — a system `gcry_*` is an approved provider on RHEL 9; flag *new* use
  only when the target is RHEL 10.
- **nettle/hogweed ship the actual primitives GnuTLS calls** — a GnuTLS extension
  that bundles its own nettle is outside the validated boundary just like a bundled
  OpenSSL. Bare `nettle_`/`_nettle_` symbols with no `libnettle.so` dependency =
  statically compiled in.

## Go binaries

```bash
go version -m ./bin      # module list + build settings (GOFIPS140, -tags, CGO_ENABLED, DefaultGODEBUG)
go tool nm ./bin | grep -E '_Cfunc__goboringcrypto_|crypto/internal/boring'   # legacy BoringCrypto
```

- `GOFIPS140=v1.0.0` build setting → **native Go FIPS module**;
  `GOEXPERIMENT=boringcrypto` / `crypto/internal/boring` → **legacy BoringCrypto**
  (cgo→BoringSSL). The two are mutually exclusive.
- **Ambiguity to respect:** `crypto/internal/fips140` package paths appear in
  **both** stock and FIPS builds — presence proves the *capability is compiled in*,
  not that FIPS was *selected*. Only the `GOFIPS140=` build setting (or runtime
  `fips140=on`) proves selection. `GOFIPS140=off` records nothing.
- wheel-crypto-scan parses `.go.buildinfo` for the Go 1.18+ inline-string layout
  only and refuses to guess the older pointer layout (a guessed load address prints
  a plausible-but-wrong version); older binaries fall back to marker strings.
- For a full Go/OpenShift FIPS verdict (native module vs. OpenSSL bridge, CGO,
  static/dynamic, tags), run **`check-payload`** (Related tooling below) — it walks
  the same `go version -m` settings this skill reads; `native-crypto.md` → "Go"
  documents the exact tree.

## Rust binaries

Rust crypto (`ring`, `aws-lc-sys`, `openssl-sys`) is almost always **statically
compiled in**, so `readelf -d` won't show it. Use symbols + strings + cargo paths:

```bash
nm ./bin 2>/dev/null | grep -Ei 'ring_|GFp_|aws_lc|awslc'
strings -a ./bin | grep -Ei 'OPENSSL_IS_AWSLC|AWSLC_VERSION|BoringSSL|/ring-[0-9]|/openssl-sys-[0-9]'
```

| Backend | Tell |
|---|---|
| `ring` | `ring_*` / `GFp_*` symbols; no OpenSSL/AWSLC banner |
| `aws-lc-rs` (`aws-lc-sys`) | `OPENSSL_IS_AWSLC`, `AWSLC_VERSION_NUMBER_STRING` (strings beat symbols under `BORINGSSL_PREFIX`) |
| `openssl-sys` | OpenSSL banner + symbols; **`vendored` feature → static bundle**, else system → **unknown** without more evidence |

wheel-crypto-scan infers crate name+version from **cargo source paths** embedded in
panic locations (`.../<crate>-<version>/src/…`, `cargo vendor`, git checkouts) —
medium-confidence but unambiguous when present. Remember the **test-only false
positive**: a crate only in `[dev-dependencies]`/`Cargo.lock` isn't shipped —
confirm it's in the built artifact (see native-crypto.md / SBOM below).

## Mach-O and PE (briefly)

- **Mach-O:** `otool -L` (deps), `otool -l` (all load commands), `nm -gU`
  (exports), `strings`. Beyond `LC_LOAD_DYLIB`, the weak/lazy/upward/**re-export**
  dylib commands also carry dependencies — a re-exported libcrypto is a crypto
  surface. delocate copies into `.dylibs/` (rewrites the load command, keeps the
  name). Stripped extensions → partial/unknown, not clean.
- **PE (`.pyd`/`.dll`):** `dumpbin /DEPENDENTS|/IMPORTS|/EXPORTS` or `objdump -p`;
  imports = PE's `DT_NEEDED` (`libcrypto-3-x64.dll`, legacy `libeay32.dll`).
  Forwarders resolve like imports. Blind spots: **ordinal-only imports** (no name)
  and the **delay-load** directory.

## Embedded SBOM — high-confidence inventory

**maturin embeds a PEP 770 SBOM** in the wheel's `.dist-info` listing the Rust
crates (and versions) it built in — the highest-confidence bundled-component
evidence, and it survives stripping. Read it before (or alongside) symbol scraping:

```bash
unzip -l pkg-*.whl | grep -iE 'sbom|\.cdx\.|bom'      # e.g. *.dist-info/sboms/*.cdx.json
```

wheel-crypto-scan folds a shipped SBOM into its linkage decision (purl-aware:
`pkg:cargo/…` reads as the crate). Caveat: the SBOM says a crate is *present*, not
which physical copy of a C library it binds — still often **unknown** for
`openssl-sys` until symbols/strings corroborate.

## Limitations — be explicit in the report

1. **Static linking hides the dependency graph** — inspect symbols/strings, not
   just `NEEDED`.
2. **Stripping removes symbols** — a stripped static object can be **opaque**;
   report for review, never "no crypto."
3. **Symbol prefixing / version scripts / hash-renaming** deliberately hide names —
   fall back to version-banner strings.
4. **The banner is shared** across OpenSSL/BoringSSL/AWS-LC/LibreSSL — require the
   `OPENSSLDIR:` copy marker + fork tells.
5. **`openssl-sys` and Go `crypto/internal/fips140` are ambiguous by
   construction** — the artifact doesn't record which copy / whether FIPS was
   selected. Resolve to **unknown**, not a verdict.

## Related tooling

- **wheel-crypto-scan** — the reference deterministic wheel scanner (recommend it;
  SKILL step 5).
- **[`check-payload`](https://github.com/openshift/check-payload)** (Red Hat /
  OpenShift, Apache-2.0) — the counterpart for **Go binaries and container images/
  payloads**: scans a container payload, a running node, or a local binary and
  validates the FIPS build regime (native Go FIPS module vs. the golang-fips OpenSSL
  bridge; dynamic link to system OpenSSL). Built for RHSB-2023-001; its
  `validateGo*` chain is the authority for the Go decision tree in
  `native-crypto.md`. Recommend it where wheel-crypto-scan doesn't reach — Go
  services and whole container images (SKILL step 5 / step 7).
- **blint** (OWASP) — binary SBOM + security properties for ELF/PE/Mach-O.
- **CBOMkit** / **CycloneDX CBOM** (1.6 / ECMA-424) — Cryptography Bill of
  Materials; PQC-migration driven crypto-asset inventory.
- **syft** — general SBOM (not crypto-specialized out of the box).
