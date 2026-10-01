# Skill: audit & remediate a Rust project's crypto (FIPS, PQC, trust, policy, ring)

Audit and remediate a **Rust project or service's** TLS/cryptography for **FIPS 140-3**,
**post-quantum crypto (PQC)**, the **system trust store**, and **system
crypto-policies** — and **replace the `ring` crypto library**. Covers the rustls
`CryptoProvider` model (bundled `aws-lc-rs` / `ring` vs a system-OpenSSL-backed
provider), why bundled crypto escapes the validated module and ignores crypto-policies,
the four migration paths (`rustls-native-ossl` provider swap, `native-tls`, direct
`openssl`/`openssl-sys`, full rewrite), `X25519MLKEM768` vs `SecP256r1MLKEM768` under
strict FIPS, `webpki-roots` vs `rustls-native-certs` / the OS store, the **RustCrypto /
pure-Rust primitive crates** (`sha2`, `aes-gcm`, `*-dalek`, `p256`, `rsa`, `ml-kem`) that
sit outside the validated module, and Cargo-graph + binary detection (`aws-lc-sys` vs
`aws-lc-fips-sys`, `ring`).

The **Rust-focused companion** to [`crypto-fips-audit`](../crypto-fips-audit/) (which
audits a Python package). This skill cites that one for the shared FIPS fundamentals —
what FIPS 140-3 governs, validated-vs-compliant-vs-capable, the approved-algorithm and
PQC-hybrid tables, binary-inspection mechanics, and the bundled-CA-trust regime — rather
than repeating them.

**Two modes** (scope to one): (1) **audit** — what crypto, through which backend, and
does it meet the goal; (2) **remediate** — move it onto the system validated provider and
off `ring` / bundled crypto, preserving behaviour.

**This gathers evidence and guides remediation — it does not certify compliance.** Only a
NIST CMVP validation makes a cryptographic module *validated*. Report findings as
evidence for a human, never as a pass/fail certification.

**The core fact:** `rustls` does not route crypto through the system library — its
built-in providers (`aws-lc-rs`, `ring`) are statically bundled, so the process never
links the system OpenSSL and cannot join the validated FIPS module or read system
crypto-policies. Even `aws-lc-rs --features=fips` is **AWS's** validated module, not the
enterprise distro's — so AWS-LC, though FIPS-validated, is **not an allowed crypto
provider** there. The fix is to route crypto through the **dynamically-linked system
OpenSSL**.

**Status: Experimental** — grounded in the cited rustls/aws-lc-rs/native-ossl/OpenSSL
and NIST/crypto-policy sources, but a new draft leaning on fast-moving, pre-1.0 pieces
(native-ossl is `0.3.x`; the uv OpenSSL integrations are unmerged). Verify every
version-gated claim against the target's pinned `Cargo.lock`.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 9 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/tls-backends.md` | The rustls `CryptoProvider` model; the four remediation paths; `rustls-native-ossl`/`native-ossl`; `native-tls`; the uv worked example; the trade-off table and decision. |
| `reference/fips-pqc-policy.md` | The validated-module boundary for Rust (incl. why AWS-LC is not an allowed provider on the enterprise distro); PQC in Rust TLS + the strict-FIPS tension and provider lag; trust store; crypto-policy inheritance; acceptance checks. |
| `reference/detection.md` | Cargo-graph + feature signals, `cargo tree` recipes, the RustCrypto / pure-Rust primitive-crate table, the maturin SBOM, and the binary symbol/string table (`aws-lc-sys` vs `aws-lc-fips-sys`, `ring`, system `libcrypto`). |

## Related

- [`crypto-fips-audit`](../crypto-fips-audit/) — the Python-package counterpart; owns the
  shared FIPS/trust/binary-inspection references this skill cites.
- [`port-to-python-limited-api`](../port-to-python-limited-api/) /
  [`port-to-free-threaded-python`](../port-to-free-threaded-python/) — the build side of
  a Rust *extension* (PyO3/maturin); this skill is about its TLS/crypto backend.

## Further reading

Sources this skill draws on (crypto moves fast — verify against the primary pages and
the pinned `Cargo.lock` before relying on a verdict):

- **rustls** — [crypto provider API](https://docs.rs/rustls/latest/rustls/crypto/) and
  the [FIPS manual](https://docs.rs/rustls/latest/rustls/manual/_06_fips/); the
  `prefer-post-quantum` / provider features.
- **aws-lc-rs** — [repo](https://github.com/aws/aws-lc-rs) and
  [platform/FIPS docs](https://aws.github.io/aws-lc-rs/); the `fips`/`non-fips` features.
- **native-ossl** — [documentation](https://akamu.dev/native-ossl/doc/) for the
  system-OpenSSL-backed rustls provider (`rustls-native-ossl`) and the EVP wrapper.
- **native-tls / trust** — [`native-tls`](https://docs.rs/native-tls/),
  [`rustls-native-certs`](https://github.com/rustls/rustls-native-certs).
- **NIST** — [FIPS 140-3](https://csrc.nist.gov/pubs/fips/140-3/final),
  [CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program),
  [SP 800-131A Rev. 2](https://csrc.nist.gov/pubs/sp/800/131/a/r2/final).
- **crypto-policies** — [Fedora crypto-policies](https://gitlab.com/redhat-crypto/fedora-crypto-policies).
- **FIPS binary scanning** — [`check-payload`](https://github.com/openshift/check-payload)
  (validates Rust binaries) and [`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan).
- **uv OpenSSL integration** (worked example) — [PR #21537](https://github.com/astral-sh/uv/pull/21537),
  [issue #11595](https://github.com/astral-sh/uv/issues/11595), and the
  [`rustls-native-ossl` branch](https://github.com/tiran/uv/tree/rustls-native-ossl).

## Acknowledgments

This skill distills the work of many people and projects:

- **Alexander Bokovoy** and **Simo Sorce** (Red Hat) — the
  [**native-ossl** / **`ossl`**](https://akamu.dev/native-ossl/doc/) crates
  (`native-ossl` / `ring-native-ossl` / `rustls-native-ossl`), the system-OpenSSL-backed
  rustls provider this skill's remediation centres on.
- **The rustls project** and **`aws-lc-rs` (AWS)** — the `CryptoProvider` model and the
  FIPS/PQC behaviour audited here.
- **Red Hat / OpenShift** — [`check-payload`](https://github.com/openshift/check-payload);
  **Emilien Macchi / Red Hat** — [`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan).
- **NIST** and the **Fedora/enterprise crypto-policies** project — the authorities on
  FIPS 140-3 and system-wide crypto policy.
- **The `uv` project** — the system-OpenSSL / `rustls-native-ossl` integration efforts
  used as the worked example.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list, and the
repository [`README.md`](../../README.md) for per-agent setup.
