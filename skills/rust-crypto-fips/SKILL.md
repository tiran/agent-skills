---
name: rust-crypto-fips
description: >-
  Audit and remediate a Rust project's TLS/cryptography for FIPS 140-3, post-quantum
  crypto (PQC), the system trust store, and system crypto-policies — and replace the
  `ring` crypto library. Covers the rustls CryptoProvider model (bundled aws-lc-rs / ring
  vs a system-OpenSSL-backed provider such as rustls-native-ossl), why bundled crypto
  escapes the validated module and ignores crypto-policies, the migration paths
  (rustls-native-ossl provider swap, native-tls, direct openssl, rewrite), X25519MLKEM768
  vs SecP256r1MLKEM768 under strict FIPS, webpki-roots vs the OS trust store, the
  RustCrypto / pure-Rust primitive crates (sha2, aes-gcm, *-dalek, p256, rsa, ml-kem) that
  sit outside the validated module, and Cargo-graph + binary detection (aws-lc-sys vs
  aws-lc-fips-sys, ring). Rust companion to crypto-fips-audit. Evidence + remediation; does
  not certify compliance.
---

# Audit and remediate a Rust project's crypto (FIPS, PQC, trust, policy, ring)

**Status: Experimental** — grounded in the rustls / aws-lc-rs / native-ossl / OpenSSL and
NIST sources below, but leans on fast-moving, pre-1.0 pieces (native-ossl is `0.3.x`; the
uv OpenSSL integrations are unmerged). **Verify version-gated claims against the pinned
`Cargo.lock`.** Gathers evidence and guides remediation; **does not certify FIPS
compliance** (only a CMVP validation makes a module *validated*) — report findings as
evidence, never pass/fail.

Rust companion to [`crypto-fips-audit`](../crypto-fips-audit/SKILL.md), which audits a
*Python package* and **owns the shared fundamentals** (what FIPS 140-3 governs,
validated-vs-compliant-vs-capable, the approved-algorithm + PQC-hybrid tables,
binary-inspection mechanics, the bundled-CA-trust regime). **Cite those; don't restate
them.** This skill goes deep on **Rust TLS/crypto** — whether a standalone Rust service
**or** the Rust shipped inside a Python package (a maturin/PyO3 extension or a Rust
dependency): its TLS backend and how to move it onto the system validated provider.

## The core problem

**rustls does not route crypto through the system library.** It decouples the TLS
protocol from a pluggable **`CryptoProvider`**; both built-ins are *statically bundled*:

- **`aws-lc-rs`** (rustls's default) — FIPS only via its `fips` feature
  (`aws-lc-fips-sys`), which is **AWS's** validated module on AWS operating environments.
  On an enterprise distro, AWS-LC — though FIPS-validated — is **not an allowed provider**
  (FIPS certs don't cross vendors); bundled, it is outside the boundary.
- **`ring`** — **no FIPS path and no PQC** (its rustls provider offers neither). It is
  still maintained (the rustls team took it over; RUSTSEC-2025-0007 was **withdrawn**), so
  FIPS/PQC — not maintenance — is why you migrate.

Bundled ⇒ the process never links the system OpenSSL, so it **can't join the validated
FIPS module or read system crypto-policies**. Loading OS *roots* (a "native certs" flag)
changes trust anchors, not where crypto runs. The fix: route crypto through the
**dynamically-linked system OpenSSL** (step 8).

The **same boundary rule applies to direct pure-Rust primitive crates** — the RustCrypto
family (`sha2`, `hmac`, `aes-gcm`, `p256`, pure-Rust `ml-kem`…) and friends (`*-dalek`,
`rsa`): compiled in, outside the validated module, so class 1 on a FIPS target even when
the algorithm is approved. Detect and remediate them too (steps 2, 5, 8;
`reference/detection.md`).

**Baseline:** an enterprise Linux distro whose system OpenSSL has a CMVP-validated FIPS
provider governed by system crypto-policies; distro/version specifics in
[`../crypto-fips-audit/reference/fips-140-3-and-openssl.md`](../crypto-fips-audit/reference/fips-140-3-and-openssl.md).
**FIPS mode comes from the host kernel**, not the app.

## Finding classes (report by these; keep apart)

1. **FIPS-140 module/algorithm** — non-approved algorithm, weak parameter, or crypto from
   a **non-validated module** (`ring`, bundled `aws-lc-rs`, vendored OpenSSL, or a
   direct **RustCrypto** / pure-Rust primitive crate).
2. **System integration / crypto-policy** — bundled CA roots (`webpki-roots` & kin), a TLS
   stack that can't honor crypto-policies. Not a FIPS-140 *algorithm* issue.
3. **Insecure use of approved crypto** — `danger_accept_invalid_certs`/`_hostnames` on in
   production, hand-rolled constructions, static nonces
   ([`.../weak-crypto.md`](../crypto-fips-audit/reference/weak-crypto.md)).

> **Guardrails** ([`../GUARDRAILS.md`](../GUARDRAILS.md)): check upstream first; local
> checkout; **ask before heavy builds** (`aws-lc-rs --features=fips` / vendored OpenSSL
> pull CMake/Go/clang); no deletes/commits/pushes without approval (never `main`); match
> the project's Rust style.

## References (open only when a step cites it)

- `reference/tls-backends.md` (steps 3, 8) — CryptoProvider model; the four remediation
  paths; `rustls-native-ossl`/`native-ossl`; `native-tls`; worked code; the uv example.
- `reference/fips-pqc-policy.md` (steps 5, 6, 7) — validated-module boundary; PQC + the
  strict-FIPS tension; trust store; crypto-policy inheritance.
- `reference/detection.md` (steps 2, 4, 5) — Cargo-graph + feature signals; the RustCrypto
  primitive-crate table; the maturin SBOM; the binary symbol/string table.

**Sources** (win over this skill): NIST FIPS 140-3 / CMVP (via the sibling); rustls crypto
+ FIPS manual (<https://docs.rs/rustls/latest/rustls/crypto/>); aws-lc-rs
(<https://github.com/aws/aws-lc-rs>); native-ossl (<https://akamu.dev/native-ossl/doc/>);
crypto-policies (<https://gitlab.com/redhat-crypto/fedora-crypto-policies>).

## 1. Scope

Record: **mode** (audit, or audit + remediate); **goals** (FIPS, PQC, OS trust,
crypto-policies, replace `ring`); **artifact** (source vs the shipped binary — audit the
binary, step 4); **target env** (the baseline above; a container inherits FIPS mode +
crypto-policy per [`.../native-crypto.md`](../crypto-fips-audit/reference/native-crypto.md)).

## 2. Check upstream, then inventory

Prior-work check ([`../GUARDRAILS.md`](../GUARDRAILS.md)); then inventory (full signal
list: `reference/detection.md`):

```bash
grep -REn 'rustls|aws-lc-rs|aws-lc-sys|aws-lc-fips-sys|\bring\b|native-tls|openssl|webpki-roots|rustls-native-certs|prefer-post-quantum|vendored' Cargo.toml Cargo.lock 2>/dev/null
cargo tree -e normal,build -i rustls; cargo tree -e normal,build -i ring   # + aws-lc-sys / aws-lc-fips-sys
grep -REn 'ClientConfig|ServerConfig|CryptoProvider|install_default|builder_with_provider|danger_accept_invalid' src/
```

Also scan for **direct pure-Rust primitive crates** (RustCrypto `sha2`/`hmac`/`aes-gcm`/
`p256`/`rsa`/`*-dalek`/pure-Rust `ml-kem`…) — the primitive grep is in `reference/detection.md`.

A **maturin-built wheel** carries an embedded CycloneDX SBOM (`*.dist-info/sboms/`, PEP
770) listing the compiled-in crates — a fast cross-check. Skip `[dev-dependencies]` (not
shipped). No TLS/crypto crates ⇒ no crypto remediation (only build-gate coverage).

## 3. Classify the backend (sets the path) — `reference/tls-backends.md`

- **No crypto** → nothing to remediate.
- **Already on system OpenSSL** (`openssl`/`native-tls`, no `vendored`) → low effort:
  confirm FIPS inherited, keep any no-verify flag dev-only, verify (step 9).
- **Bundled-provider rustls** (`rustls` + `aws-lc-rs` or `ring`) → the main case; migrate
  (step 8). `ring` = highest-risk sub-case (no FIPS, no PQC).
- **Vendored OpenSSL** (`vendored`/`openssl-src`) → drop the vendoring (`OPENSSL_NO_VENDOR=1`).

## 4. Confirm against the binary

Features/targets resolve differently than source suggests; both aws-lc variants can sit in
the graph while one links. Table: `reference/detection.md`; mechanics:
[`.../binary-inspection.md`](../crypto-fips-audit/reference/binary-inspection.md).

```bash
readelf -d <bin> | grep NEEDED   # libcrypto.so NEEDED ⇒ dynamic system link; none ⇒ bundled
strings -a <bin> | grep -Ei 'aws_lc_fips_|aws_lc_[0-9]|AWS-LC( FIPS)? [0-9]|BORINGSSL_bcm_power_on_self_test|OpenSSL [0-9]'  # strip-proof
nm <bin> 2>/dev/null | grep -E 'ring_|GFp_|aws_lc_fips_|FIPS_mode'   # NOT nm -D (bundled crypto = local symbols; needs unstripped)
```

`aws_lc_fips_*` / `AWS-LC FIPS` ⇒ FIPS aws-lc (bundled → class 1 here); `aws_lc_<ver>_` /
`AWS-LC` ⇒ stock; `ring_`/`GFp_` ⇒ ring; `libcrypto.so` NEEDED + no bundled markers ⇒
system provider (goal). A stripped static binary with none is **opaque** — report for
review, never "clean."

## 5. FIPS assessment — `reference/fips-pqc-policy.md`

Approved crypto must come from the system validated module. `ring` / bundled `aws-lc-rs`
(incl. `--features=fips`) / **direct RustCrypto primitive crates** (`sha2`, `hmac`,
`aes-gcm`, `*-dalek`, `p256`, `rsa`, pure-Rust `ml-kem`…) → **class 1** even when the
algorithm is approved; **dynamically-linked system OpenSSL** → inside the boundary, FIPS
applying **per operation** automatically on a FIPS host (no app opt-in). RustCrypto
detection + verdicts: `reference/detection.md` (and the sibling for per-algorithm calls).

## 6. Trust store — `reference/fips-pqc-policy.md`, regime in [`.../trust-store.md`](../crypto-fips-audit/reference/trust-store.md)

`webpki-roots` & kin (bundled roots) → **class 2** (a policy issue, not FIPS). Fix via the
OS store (`rustls-native-certs` / `rustls-platform-verifier` — trust source only), or an
OpenSSL-backed path: OpenSSL owns `X509_verify_cert` (`native-tls`/direct **and**
`rustls-native-ossl` can route cert validation through OpenSSL), dropping bundled roots.

## 7. crypto-policies & PQC — `reference/fips-pqc-policy.md`

- **rustls ignores crypto-policies** (both providers; issue #2402). Only a system-OpenSSL
  path inherits them — with the *provider swap* rustls still orders suites/groups; full
  ordering needs the handshake in libssl (`native-tls`/direct).
- **PQC** — target = **X25519MLKEM768** hybrid KX; preferred by recent rustls
  (`prefer-post-quantum`, aws-lc-rs) and by `rustls-native-ossl` ≥ 0.3.1 built on OpenSSL
  3.5.0+. **FIPS nuance:** `X25519MLKEM768` *is* FIPS-approvable — NIST SP 800-56C lets the
  approved **ML-KEM-768 go first** with X25519 as the auxiliary secret, and OpenSSL 3.5 FIPS
  marks it `fips=yes`; X25519 is **not** a disqualifier. The real blocker is **provider
  lag** (a validated module must implement *certified* ML-KEM, which older certified
  providers lack) ⇒ **FIPS + PQC often not co-functional yet** (expected, not a defect).
  Where a strict policy rejects X25519 hybrids (e.g. Go `fips140=only`), use
  `SecP256r1MLKEM768`. Detail/tables:
  [`.../fips-140-3-and-openssl.md` §5](../crypto-fips-audit/reference/fips-140-3-and-openssl.md).

## 8. Remediate — cheapest → most involved; code + uv example: `reference/tls-backends.md`

1. **Provider swap** → `rustls-native-ossl` (`default_provider().install_default()`): keeps
   rustls, drops `ring`/aws-lc **entirely**, routes crypto (and optionally cert validation)
   through system OpenSSL; `X25519MLKEM768` preferred on OpenSSL 3.5.0+. Caveat: `0.3.x`
   experimental.
2. **native-tls backend** → OpenSSL (libssl) owns the whole handshake (full crypto-policy +
   FIPS); drops the macOS/Windows native backends.
3. **Direct `openssl`/`openssl-sys`** (+ `hyper-openssl`/`tonic-openssl`) → most effort;
   native build deps; test every arch.
4. **Full rewrite** → last resort.

**Direct primitive use (not TLS):** for RustCrypto/`*-dalek`/`rsa` calls, there is no
provider to swap — route the operations through the **system OpenSSL EVP**: the `openssl`
crate, or native-ossl's `native-ossl` (safe EVP wrappers) / `ring-native-ossl` (a
`ring`-compatible API backed by native-ossl/OpenSSL). Same rule applies.

All paths: **dynamically link the system OpenSSL, never vendor** (`OPENSSL_NO_VENDOR=1`; no
`ring`/default provider in the shipped profile); preserve behavior (per-endpoint config,
mTLS, any no-verify flag kept dev-only); prefer an upstream feature flag over a big fork;
benchmark (~≤ 10 % handshake regression). Can't land → document a formal exception.

## 9. Verify & report

```bash
cargo tree -e normal,build -i ring; cargo tree -e normal,build -i aws-lc-sys   # expect: not found
readelf -d <bin> | grep -E 'libcrypto|libssl'                                  # expect system libcrypto NEEDED
update-crypto-policies --show; openssl list -kem-algorithms | grep -i ml-kem   # policy + PQC availability
# live handshake (tshark / openssl s_client): X25519MLKEM768 for PQC
```

Acceptance: crypto binaries use the system provider on a FIPS host (scan **and** live
handshake); no bundled non-validated crypto; tests pass unchanged (per-endpoint TLS, mTLS);
a PQC-policy container offers/prefers `X25519MLKEM768`; **PQC off under FIPS is
acceptable**. For a whole binary/image, `check-payload` validates Rust too. Group findings
by the three classes with evidence + remediation; restate: **evidence, not certification** —
re-verify against the live
[CMVP DB](https://csrc.nist.gov/projects/cryptographic-module-validation-program) and the
pinned `Cargo.lock`.

**Definition of done:** artifact + build/target stated; backend classified; FIPS, trust,
and policy/PQC findings in the three classes with evidence + remediations; each remediation
names a step-8 path + caveats; experimental/version-gated claims flagged; framed as
evidence, not certification.
