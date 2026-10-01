# AGENTS.md — rust-crypto-fips

Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). Claude Code loads
`SKILL.md` directly; both share the same content and references.

## When to use

Audit and/or **remediate** the TLS/cryptography of a Rust codebase — a standalone Rust
service **or** the Rust shipped inside a Python package (a maturin/PyO3 extension or a Rust
dependency) — for **FIPS 140-3**, **post-quantum crypto (PQC)**, the **system trust store**,
**system crypto-policies**, or to **replace the `ring` crypto library**. The core issue: `rustls`
bundles its crypto provider (`aws-lc-rs` / `ring`), so it never links the system OpenSSL
and can't join the validated FIPS module or honor crypto-policies — and AWS-LC, though
FIPS-validated, is **not an allowed provider** on an enterprise distro. The fix is to route
crypto through the dynamically-linked system OpenSSL (e.g. the `rustls-native-ossl` provider
swap, `native-tls`, or direct `openssl`). The **same boundary rule covers direct pure-Rust
primitive crates** — the RustCrypto family (`sha2`, `aes-gcm`, `p256`, pure-Rust `ml-kem`…)
and `*-dalek`/`rsa`, which compile in outside the validated module.

Rust-focused companion to [`crypto-fips-audit`](../crypto-fips-audit/), which audits a
*Python package* and owns the shared FIPS fundamentals this skill **cites** (FIPS 140-3
theory, the approved-algorithm/PQC-hybrid tables, binary-inspection mechanics, the CA-trust
regime). Two modes: **audit** (classify, no changes) and **remediate**. It **gathers
evidence; it does not certify compliance.**

## Status

**Experimental** — leans on fast-moving, pre-1.0 pieces (native-ossl `0.3.x`; unmerged uv
integrations). Verify version-gated claims against the pinned `Cargo.lock`.

## How to run it

Read **`SKILL.md`** (9 ordered steps) and follow it top to bottom, opening a `reference/`
file only when a step cites it:

- `reference/tls-backends.md` — the CryptoProvider model + four remediation paths + worked
  code + uv example.
- `reference/fips-pqc-policy.md` — the FIPS boundary for Rust, PQC/strict-FIPS, trust store,
  crypto-policies.
- `reference/detection.md` — Cargo-graph + maturin-SBOM + binary signals.

Reuse the sibling's binary tooling for a Rust *binary*:
`../crypto-fips-audit/scripts/scan_crypto.py` and
[`check-payload`](https://github.com/openshift/check-payload) (validates Rust binaries for
system-OpenSSL linkage).

## Related skills

- [`crypto-fips-audit`](../crypto-fips-audit/) — Python-package counterpart; owner of the
  shared FIPS/trust/binary-inspection references.
- [`port-to-free-threaded-python`](../port-to-free-threaded-python/) /
  [`port-to-python-limited-api`](../port-to-python-limited-api/) — the PyO3/maturin build
  side of a Rust *extension* (this skill is about its TLS/crypto backend).

## Definition of done

Artifact + build/target stated; TLS backend classified; FIPS-module, trust-store, and
crypto-policy/PQC findings separated into the three classes with evidence + remediations;
each remediation names a step-8 path + caveats; experimental/version-gated claims flagged;
framed as evidence, not certification.

## Sources & acknowledgments

Acknowledge these when output leans on their work; preserve upstream license/attribution:

- **System-OpenSSL Rust crypto** — **Alexander Bokovoy** and **Simo Sorce** (Red Hat), for
  the [**native-ossl**](https://akamu.dev/native-ossl/doc/) / **`ossl`** work
  (`native-ossl` / `ring-native-ossl` / `rustls-native-ossl`) that routes rustls crypto
  through the system OpenSSL.
- **rustls / aws-lc-rs** — the [rustls](https://github.com/rustls/rustls) project and
  [`aws-lc-rs`](https://github.com/aws/aws-lc-rs) (the CryptoProvider model + FIPS/PQC
  behaviour audited here).
- **FIPS binary scanning** — **Red Hat / OpenShift**
  ([`check-payload`](https://github.com/openshift/check-payload), Rust support) and
  **Emilien Macchi / Red Hat** ([`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan)).
- **FIPS & crypto-policy** — **NIST** and the **Fedora/enterprise crypto-policies** project.
- **uv OpenSSL integration** (worked example) — the `uv` project and its
  system-OpenSSL/`rustls-native-ossl` integration efforts.

See [`../reference-repos.md`](../reference-repos.md) for the full grounding list, and the
repository [`README.md`](../../README.md) for per-agent setup.
