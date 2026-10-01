# Rust TLS backends: the CryptoProvider model and the remediation paths

Companion to SKILL steps 3 and 8. The FIPS/PQC/policy *verdicts* are in
`fips-pqc-policy.md`; *how to detect* each backend is in `detection.md`. Sources are
linked inline; they win over this file.

## rustls decouples protocol from crypto

Since **rustls 0.22** the TLS protocol engine is separate from a pluggable
**`crypto::CryptoProvider`** that supplies the actual primitives: `SecureRandom`, the
cipher suites, the key-exchange groups, the signature-verification algorithms, and a
`KeyProvider` (private-key load/sign). Two providers ship with rustls, **both
statically bundled** into your binary:

| Provider | Cargo feature | FIPS | Notes |
| --- | --- | --- | --- |
| `crypto::aws_lc_rs::default_provider()` | `aws_lc_rs` (**default on**) | only via `fips` feature → `aws-lc-fips-sys` | BoringSSL-derived; rustls's default; supplies ML-KEM for PQC |
| `crypto::ring::default_provider()` | `ring` | **none** | older; **no PQC/hybrid KX**. Maintained again by the rustls team (RUSTSEC-2025-0007 withdrawn) — maintenance isn't the driver, FIPS/PQC is |

Install a provider process-wide, or pass it per-config:

```rust
// process-wide (errors if one is already installed)
some_provider().install_default().expect("install crypto provider");

// explicit per-config
let cfg = ClientConfig::builder_with_provider(some_provider().into())
    .with_safe_default_protocol_versions()?
    .with_root_certificates(roots)
    .with_no_client_auth();
```

**The "ambiguous provider" panic.** If Cargo feature-unification links **both**
`ring` and `aws-lc-rs` (common via transitive deps — reqwest, sqlx, hyper-rustls,
rcgen), rustls 0.23 **panics at runtime about being unable to determine a
process-level `CryptoProvider`** because it can't auto-pick. Fixes: `install_default()`
at startup, pass the provider explicitly, or drop one with `default-features = false` /
the `custom-provider` feature. Seeing both in `cargo tree` is also why the **binary**
must be checked (`detection.md`).

**rustls's own FIPS story is still bundled.** `rustls::crypto::default_fips_provider()`
(the `fips` feature) is backed by `aws-lc-fips-sys` — a *compile-time* choice (no
runtime `/proc/sys/crypto/fips_enabled` detection, rustls#3054) and **a separate
validated module, not the system one** (see `fips-pqc-policy.md`).

## The system-OpenSSL-backed provider: native-ossl

[**native-ossl**](https://akamu.dev/native-ossl/doc/) is an idiomatic Rust wrapper over
the **system** OpenSSL 3.x **EVP / libcrypto** API. It **links the system OpenSSL
dynamically and never ships its own copy** — which is exactly what puts the primitives
inside the system validated module. It needs **OpenSSL 3.5.0+** and **Rust 1.77+**; the
crates are **pre-1.0 (`0.3.x`) — treat as experimental and pin exact versions.**

> **Architecture — this is a `CryptoProvider`, not a libssl handshake.** `rustls-native-ossl`
> is a rustls **`CryptoProvider`**: **rustls runs the TLS protocol / handshake state
> machine in Rust**, and OpenSSL's **libcrypto (EVP)** performs only the cryptographic
> operations — it does **not** use OpenSSL's **libssl** for the handshake. (Contrast
> `native-tls`, below, where OpenSSL's **libssl** runs the whole handshake.) The
> consequence runs through the whole skill: the provider swap keeps rustls's memory-safe
> protocol engine and gets FIPS-per-operation (and, ≥ 0.3.1, the hybrid KX group) from the
> system module — but **rustls**, not libssl, still decides suite/group *selection and
> ordering*, so the system crypto-policy's cipher-string ordering is not applied (that
> needs libssl — `native-tls`/direct).

Workspace crates:

| Crate | Role |
| --- | --- |
| `native-ossl-sys` | raw FFI bindings (bindgen at build time) |
| `native-ossl` | safe EVP wrappers (digests, AEAD, HMAC/CMAC/KMAC, RSA/ECDSA/Ed25519/X25519, **ML-KEM/ML-DSA**, HKDF/PBKDF2, X.509/CMS, TLS 1.2/1.3) |
| `ring-native-ossl` | a **`ring`-compatible API backed by `native-ossl`** (system OpenSSL) |
| `rustls-native-ossl` | a **complete** rustls **`CryptoProvider`** routing *all* crypto through system OpenSSL (via `native-ossl`); replaces the bundled provider — **no `ring` (or bundled aws-lc) left anywhere in the TLS stack** |

```rust
// swap rustls's crypto backend to system OpenSSL — no change to the rustls version or
// to client/connection code, just the provider:
rustls_native_ossl::default_provider()
    .install_default()
    .expect("install OpenSSL provider");
```

`LibCtx`-style "library contexts" enable **FIPS-provider isolation and PKCS#11**
hardware tokens; PQC (ML-KEM/ML-DSA) comes from the OpenSSL 3.x providers. It omits
deprecated OpenSSL 1.x APIs (EVP-only) and is **sync TLS only**. It can also **route
certificate validation through OpenSSL** (`X509_verify_cert`) — not just the primitives —
so a provider swap fixes crypto *and* trust in one move. **FIPS is inherited from the
OpenSSL installation** (the crate sets no FIPS flag; its `fips()` returns `false` because
compliance is a property of the linked OpenSSL, not the crate). The `tls12` feature
(default-on) enables TLS 1.2 suites; drop it for TLS-1.3-only.

> **Naming trap — three different "ossl".** (1) `rustls-native-ossl` is the native-ossl
> workspace member above. (2) The crates.io crate **`ossl`** (from the `latchset/kryoptic`
> project) is a *separate* OpenSSL-EVP-bindings library — **not** part of native-ossl.
> (3) In the uv fork below, **`ossl` is a Cargo *feature*** on `uv-client`, not a crate.
> Don't conflate them in a finding.

> **native-ossl and hybrid PQ KX.** When `rustls-native-ossl` (**≥ 0.3.1**) is built
> against **OpenSSL 3.5.0+**, **`X25519MLKEM768` is the preferred KX group** — the
> provider offers it first in the handshake, so the provider-swap path gets PQC out of the
> box. (0.3.0 — which the uv branch below pinned — exposed only X25519 / P-256 / P-384; the
> hybrid landed in a point release.) native-ossl already **requires** OpenSSL 3.5.0+, so
> this is the normal case; still verify the negotiated group on the wire.

### Worked wiring: system trust store + OpenSSL verifier + mTLS

The full provider-swap shape — OS roots (plus optional extra CAs) validated by an
**OpenSSL-backed verifier**, `SSL_CLIENT_CERT` mTLS, ALPN. Note the comment: the OpenSSL
verifier takes **explicit** roots, so the system store is loaded by `load_native_certs()`
(which honors `SSL_CERT_FILE`/`SSL_CERT_DIR`) and handed in — OpenSSL then does the path
validation (`X509_verify_cert`):

```rust
use std::sync::Arc;

use anyhow::{bail, Result};
use rustls::ClientConfig;
use rustls::pki_types::CertificateDer;
use rustls_native_certs::load_native_certs;
use rustls_native_ossl::OsslServerCertVerifier;
// `default_provider` is used fully-qualified below. Certificates / load_client_auth() /
// ALPN_PROTOCOLS are crate-local to the application.

pub(crate) fn client_config(custom_certificates: Option<&Certificates>) -> Result<ClientConfig> {
    // Always trust the system store; add any user-provided custom certs on top.
    let mut roots: Vec<CertificateDer<'static>> = load_native_certs().certs;
    if let Some(custom) = custom_certificates {
        roots.extend(custom.der().iter().cloned());
    }
    if roots.is_empty() {
        bail!("No trusted CA certificates found in the system trust store");
    }

    // OpenSSL-backed cert verification (chain + hostname via X509_verify_cert).
    let verifier = OsslServerCertVerifier::builder(&roots)?.build();

    let builder = ClientConfig::builder_with_provider(rustls_native_ossl::default_provider().into())
        .with_safe_default_protocol_versions()?
        .dangerous()                                        // custom verifier ⇒ the dangerous() API
        .with_custom_certificate_verifier(Arc::new(verifier));

    // mTLS from SSL_CLIENT_CERT (key loaded/signed through OpenSSL, never non-OpenSSL crypto).
    let mut config = match load_client_auth()? {
        Some((chain, key)) => builder.with_client_auth_cert(chain, key)?,
        None => builder.with_no_client_auth(),
    };
    config.alpn_protocols = ALPN_PROTOCOLS.iter().map(|p| p.to_vec()).collect();
    Ok(config)
}
```

`install_default()` (above) is enough when rustls's default verifier + root handling suit
you; use the explicit `builder_with_provider(...).dangerous().with_custom_certificate_verifier(...)`
form shown here to route **certificate validation** through OpenSSL as well.

## native-tls and the trust-store crates

- [**`native-tls`**](https://docs.rs/native-tls/) — an abstraction over the OS-native
  TLS stack: **SChannel** (Windows), **Secure Transport** (macOS), **OpenSSL**
  elsewhere. On Linux it wraps the system OpenSSL and **OpenSSL's `libssl` runs the whole
  TLS handshake** (not just the primitives) — so it inherits crypto-policy cipher/group
  selection *and* ordering, plus FIPS. Its **`vendored`** feature statically links a
  bundled OpenSSL instead — **the opposite of what you want**; flag it.
- [**`rustls-native-certs`**](https://github.com/rustls/rustls-native-certs) — loads the
  **OS trust store** for rustls (maintainers now steer users to
  **`rustls-platform-verifier`** for full platform verification incl. revocation).
  Fixes *trust source* only — **not** the crypto module (`fips-pqc-policy.md`).
- **`webpki-roots`** — the bundled-Mozilla-roots crate to **remove**.

## The four remediation paths (step 8)

Same outcome (crypto through system OpenSSL); choose by patch size vs. need.

| # | Path | How | Keeps rustls? | Gets full crypto-policy? | Main caveat |
| --- | --- | --- | --- | --- | --- |
| 1 | **Provider swap** | `rustls-native-ossl` `install_default()` | **Yes** | Partial — rustls drives suite/group ordering; OpenSSL runs primitives (FIPS per-op) | `0.3.x` experimental; `X25519MLKEM768` **preferred** with ≥ 0.3.1 on OpenSSL 3.5.0+ |
| 2 | **native-tls backend** | switch the HTTP client (e.g. `reqwest`) to its `native-tls` backend | No | **Yes** — OpenSSL owns the handshake | Linux = OpenSSL-only; **drops macOS/Windows native backends** |
| 3 | **Direct openssl** | bind `openssl`/`openssl-sys` + `hyper-openssl`/`tonic-openssl` | No | **Yes** | highest effort when TLS is pervasive; native build deps; test every arch |
| 4 | **Full rewrite** | replace the rustls stack with OpenSSL | No | **Yes** | most expensive; only when necessary |

Rules for every path:

- **Dynamically link the system OpenSSL; never vendor.** Set `OPENSSL_NO_VENDOR=1`
  (target-prefixed `<TARGET>_OPENSSL_NO_VENDOR` is checked first); ensure no
  `ring`/default provider/`vendored` OpenSSL in the shipped profile (`cargo tree`).
  Build stage needs the OpenSSL dev package; runtime stage needs the OpenSSL runtime libs.
- **Preserve behavior** — per-endpoint TLS config, mTLS, and any dev-only
  no-verify flag kept behind a dev-only build feature (never on in production → class 3).
- **Prefer an upstream-accepted feature flag over a big fork.** A fast-moving dependency
  (several releases/week) makes a sprawling downstream-only patch expensive to rebase;
  the provider swap or an additive feature is the cheapest to carry.
- **Benchmark** handshake latency/throughput before/after for high-throughput TLS
  (OpenSSL vs the bundled provider differ); a commonly cited tolerance is ≤~10% handshake
  regression.
- If it can't land in time, **document a formal exception** (which stack, why it can't
  negotiate the required algorithms).

## Worked example — the uv package manager

`uv` ships rustls + a bundled provider; two **unmerged** efforts (do **not** present
either as shipping in uv today) move it onto system OpenSSL — a clean template for both
the "replace the stack" and "swap the provider" approaches:

- **[PR #21537](https://github.com/astral-sh/uv/pull/21537)** adds an additive,
  compile-time **`native-tls`** feature to `uv-client`: `cargo build -p uv
  --no-default-features --features native-tls`. OpenSSL then owns cert validation + the
  trust store (`SSL_CERT_FILE`/`SSL_CERT_DIR`/`SSL_CLIENT_CERT` for mTLS), and the
  bundled-roots controls become no-ops. Proof it honors policy: under a stricter policy
  (`FUTURE`) the native build **rejects a too-weak server cert** (`EE certificate key
  too weak`) where the rustls build cannot. This is **path 2**, and it fixes uv issue
  [#11595](https://github.com/astral-sh/uv/issues/11595) ("native-tls" previously only
  loaded native *certs*, still via rustls+ring).
- **The `rustls-native-ossl` fork branch** (<https://github.com/tiran/uv/tree/rustls-native-ossl>)
  adds an **`ossl`** feature that keeps rustls and installs the `rustls-native-ossl`
  provider process-wide, dropping aws-lc-rs: `cargo build -p uv --no-default-features
  --features ossl`. Server-cert verification runs through OpenSSL `X509_verify_cert`;
  the mTLS key is loaded/signed through OpenSSL so it never touches non-OpenSSL crypto.
  This is **path 1**. Note the branch pinned `rustls-native-ossl` **0.3.0**, which had no
  hybrid KX; **0.3.1 negotiates `X25519MLKEM768`** (pin ≥ 0.3.1). The remaining path-1
  caveat is that rustls still drives suite/group *ordering* (not OpenSSL's crypto-policy
  cipher-string order).

The contrast is the decision in miniature: **path 2 (native-tls)** gives full
crypto-policy/FIPS control (OpenSSL drives the whole handshake) but drops rustls and the
non-Linux native backends; **path 1 (provider swap)** keeps rustls's memory-safe state
machine and routes primitives — including hybrid PQ KX with a current crate — through
OpenSSL, at the cost of rustls (not the system policy) driving suite/group ordering.
