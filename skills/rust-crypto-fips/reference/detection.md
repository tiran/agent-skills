# Detecting Rust crypto backends: Cargo graph and binary signals

Companion to SKILL steps 2 and 4. Two layers must agree: the **source/dependency
graph** (what *could* be linked) and the **built binary** (what *was* linked). They
diverge — feature unification can pull a provider in, and `vendored` statically
compiles crypto that the graph alone won't tell you is static. The per-format binary
mechanics (ELF/Mach-O/PE symbol reading, the posture model) are the sibling's
[`binary-inspection.md`](../crypto-fips-audit/reference/binary-inspection.md); this file
is the **Rust-specific** signal table.

## Cargo graph signals

```bash
grep -REn 'rustls|aws-lc-rs|aws-lc-sys|aws-lc-fips-sys|\bring\b|native-tls|openssl|openssl-sys|openssl-src|webpki-roots|rustls-native-certs|rustls-platform-verifier|rustls-native-ossl|native-ossl|prefer-post-quantum|vendored' Cargo.toml Cargo.lock
```

| Signal (crate / feature) | Means | Verdict lens |
| --- | --- | --- |
| `ring` | bundled provider (Rust + C/asm), **no FIPS, no PQC** (maintained by the rustls team) | class 1 |
| `aws-lc-rs` + `aws-lc-sys` | bundled **non-FIPS** AWS-LC (stock) | class 1 |
| `aws-lc-rs` + `aws-lc-fips-sys`, or the `fips` feature | bundled **FIPS** AWS-LC — *still outside the distro boundary* (`fips-pqc-policy.md`) | class 1 |
| `aws-lc-rs` `non-fips` feature | forces `aws-lc-sys` (mutually exclusive with `fips`) | class 1 |
| rustls feature `aws_lc_rs` (default) / `ring` | which provider rustls compiles in | — |
| rustls feature `custom-provider` | built-in providers disabled; a provider is supplied in code | inspect code |
| rustls feature `prefer-post-quantum` / `fips` | PQC KX preference / bundled FIPS provider | step 7 / class 1 |
| `openssl`/`openssl-sys` **without** `vendored` | likely **system** OpenSSL (confirm in the binary) | target state |
| `openssl-sys`/`native-tls` `vendored`, or **`openssl-src`** in the tree | statically-linked **bundled** OpenSSL → escapes the system module & policies | class 1 |
| `native-tls` (no `vendored`) | OS-native TLS; on Linux = system OpenSSL | target state (path 2) |
| `webpki-roots` / `webpki-root-certs` / any crate shipping a `*.pem` / `cacert.pem` root set | bundled CA **trust store** — a policy / system-integration issue, not FIPS | class 2 |
| `rustls-native-certs` / `rustls-platform-verifier` | OS trust store (trust source only) | remediation present |
| `rustls-native-ossl` / `native-ossl` | system-OpenSSL-backed rustls provider (`0.3.x`) | remediation present (path 1) |

**Which crate pulls each in** — use `-e normal,build` and inverse (`-i`); a bare
`-e dev -i` can print nothing even when an edge exists, and dev-only edges are **not
shipped**:

```bash
cargo tree -e normal,build -i ring
cargo tree -e normal,build -i aws-lc-sys
cargo tree -e normal,build -i aws-lc-fips-sys
cargo tree -e normal,build -i openssl-sys
cargo tree -e normal,build -i rustls           # often reached via reqwest/sqlx/tonic/hyper-rustls
```

Only flag a crate that is a real `[dependencies]`/`[build-dependencies]` entry **and**
appears in the shipped build — confirm against the binary below. A `deny.toml`
(`cargo-deny`) banning `ring`/`aws-lc-sys` is a good anti-regression control for a FIPS
target (regardless of `ring`'s maintenance status). Note `cargo audit` no longer flags
current `ring` — **RUSTSEC-2025-0007 was withdrawn** once the rustls team took over
maintenance — but it still flags **`ring` < 0.17** (RUSTSEC-2025-0010).

**Vendoring override:** `OPENSSL_NO_VENDOR=1` (the target-prefixed
`<TARGET>_OPENSSL_NO_VENDOR` is checked first) forces system libcrypto; `OPENSSL_DIR` /
`OPENSSL_STATIC` also steer linkage. For a system AWS-LC instead of a bundled one:
`AWS_LC_SYS_SYSTEM_DIR` / `AWS_LC_FIPS_SYS_SYSTEM_DIR` — but that is still AWS-LC, not
system OpenSSL.

## RustCrypto & other pure-Rust primitive crates

Beyond the TLS stacks, a project may call **pure-Rust primitives directly** — the
[RustCrypto](https://github.com/RustCrypto) family (`sha2`, `hmac`, `aes-gcm`, …) and
friends (`*-dalek`, `rsa`). They compile **into the binary** and are **outside the system
validated module**, so on a FIPS target they are **class 1 even when the algorithm is
approved** — the same boundary rule as `ring`/bundled `aws-lc`. Per-algorithm verdicts
live in the sibling's
[`native-crypto.md`](../crypto-fips-audit/reference/native-crypto.md) → Rust and
[`fips-primer.md`](../crypto-fips-audit/reference/fips-primer.md); grep the manifest/SBOM:

```bash
grep -REn 'sha2|sha3|\bhmac\b|hkdf|pbkdf2|\baes\b|aes-gcm|chacha20poly1305|\bp256\b|\bp384\b|\bk256\b|ecdsa|ed25519|curve25519-dalek|x25519-dalek|\brsa\b|\bdsa\b|blake2|blake3|argon2|scrypt|bcrypt|sha1|md-?5|md4|ml-kem|ml-dsa|slh-dsa|fips20[345]|pqcrypto' Cargo.toml Cargo.lock
```

| Class | Example crates | Verdict on a FIPS target |
| --- | --- | --- |
| Approved alg, **unvalidated impl** (review by use) | `sha2` `sha3` `hmac` `hkdf` `pbkdf2` `aes` `aes-gcm` `p256`/`p384` `ecdsa` `ed25519-dalek` `rsa`\* | class 1 (outside the module) |
| **Non-approved** primitive | `chacha20poly1305`; `curve25519-dalek`/`x25519-dalek` (X25519 KEX); `k256` (secp256k1); `blake2`/`blake3`; `argon2`/`scrypt`/`bcrypt`; pure-Rust PQC `ml-kem`/`ml-dsa`/`slh-dsa`/`fips203..205`/`pqcrypto-*` | class 1 |
| **Weak / broken** | `sha1`/`sha1_smol` (restricted); `md5`/`md-5`; `md4` | class 1 **+** weak-crypto (class 3) |

\* `rsa` also carries the Marvin timing concern — see the sibling's weak-crypto lens.

**Binary signals.** Pure Rust leaves **no C symbols and no `libcrypto` NEEDED**, so the
`ring_`/`aws_lc_` greps above won't fire. Detect these via the **Cargo graph + the maturin
SBOM** (below), or, in an unstripped binary, demangled Rust symbol paths / panic-location
strings (`sha2::`, `aes_gcm::`, `curve25519_dalek::`).

**Remediation is *not* a TLS provider swap.** For direct primitive use, route the
operations through the **system OpenSSL EVP** — the `openssl` crate, or native-ossl's
`native-ossl` (safe EVP wrappers) / `ring-native-ossl` (a `ring`-compatible API backed by
`native-ossl`/OpenSSL) — so they run
inside the validated module (`tls-backends.md`).

## Embedded SBOM (maturin-built wheels)

If the Rust code ships as a **Python wheel built by maturin**, the wheel carries a
**CycloneDX SBOM** ([PEP 770](https://peps.python.org/pep-0770/)) under
`*.dist-info/sboms/` that lists the **Rust crates compiled in** — the fastest way to
enumerate `ring` / `aws-lc-rs` / `aws-lc-fips-sys` / `webpki-roots` and their versions
without symbol inspection, and it catches transitive crates a bare `Cargo.lock` scan
can miss. maturin keeps the **bindings crate's** BOM (full transitive graph); auditwheel
adds `auditwheel.cdx.json` recording which **OS packages** provided shared libraries
grafted into the wheel (useful to tell a system `libcrypto` from a vendored one).

```bash
unzip -l foo.whl | grep -i 'sboms/'                      # *.dist-info/sboms/*.cdx.json present?
unzip -p foo.whl '*/sboms/*.cdx.json' | jq -r '.components[]? | "\(.name) \(.version)"'
```

The SBOM reflects the *source* crate graph, so it still can't settle **which** AWS-LC
variant actually linked (both may appear) — confirm linkage in the binary below.

## Binary signals (the deciding layer)

The graph can list both `aws-lc-sys` and `aws-lc-fips-sys` while only one links, so the
**binary decides**. Host-native tools below; for a foreign arch/OS binary use the
portable `pyelftools`/`macholib`/`pefile` reader in the sibling's
`binary-inspection.md` (or its `scripts/scan_crypto.py`).

```bash
readelf -d <bin> | grep NEEDED          # libcrypto.so/libssl.so NEEDED ⇒ dynamic system link; absent ⇒ bundled/static
nm <bin> 2>/dev/null | grep -E 'ring_|GFp_|aws_lc_fips_|aws_lc_[0-9]|FIPS_mode'   # NOT nm -D (see note)
strings -a <bin> | grep -Ei 'aws_lc_fips_|aws_lc_[0-9]|AWS-LC( FIPS)? [0-9]|BORINGSSL_bcm_power_on_self_test|BORINGSSL_integrity_test|OpenSSL [0-9]|OPENSSLDIR'
```

> **Use `nm`, not `nm -D`, for bundled crypto.** A statically-linked provider (`ring`,
> `aws-lc`) compiled into a Rust executable or `cdylib` links as **local** symbols, which
> `nm -D` (dynamic symbols only) does **not** list — `nm -D` is right only for a *shared*
> `libcrypto.so`'s exports. `nm` (all symbols) needs an **unstripped** binary; many Rust
> release profiles strip (`strip = true`), so **`strings` is the strip-proof signal** —
> the AWS-LC/FIPS banner lives in `.text` and survives stripping.

| Binary marker | Backend | Note |
| --- | --- | --- |
| `aws_lc_fips_*` symbols, `AWS-LC FIPS <ver>` string, `BORINGSSL_bcm_power_on_self_test` / `FIPS_mode` | **FIPS** AWS-LC build | self-test symbols are a strong FIPS indicator; the FIPS version string lives in `.text` (survives stripping) — still bundled → class 1 here |
| `aws_lc_<maj>_<min>_<patch>_*` prefix, `AWS-LC <ver>` (no "FIPS") | **stock** AWS-LC | the version prefix changes every release |
| `ring_*` / `GFp_*` symbols | **`ring`** | — |
| `libcrypto.so` **NEEDED**, banner `OpenSSL <ver>` / `OPENSSLDIR`, no bundled markers | **system OpenSSL** (dynamic) | the target state — corroborate the banner with the NEEDED entry |
| distro-packaged AWS-LC: SONAME `libcrypto-awslc.so.*`, symbol version `AWS_LC_1.0` | system AWS-LC (`-DENABLE_DIST_PKG`) | still AWS-LC, not system OpenSSL |

- A **`libcrypto.so` NEEDED** with none of the bundled markers = dynamically linked to
  the system provider (what remediation should produce).
- A **stripped, statically-linked binary with no markers is opaque** — you can't prove
  absence of crypto; report for review, never "clean."
- Prefer the binary over the graph for the final verdict; use `BORINGSSL_PREFIX`-aware
  reasoning (AWS-LC can rename symbols — trust the `.text` banner string) per the
  sibling's `native-crypto.md` → Rust.
