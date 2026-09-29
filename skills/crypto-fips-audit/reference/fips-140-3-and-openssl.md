# FIPS 140-2 → 140-3, algorithm changes, and use-scoping (OpenSSL-focused)

Companion to [`fips-primer.md`](fips-primer.md) (the by-class approved/non-approved
reference) and [`native-crypto.md`](native-crypto.md) (the validated-*module*
requirement). This lens covers three things a developer or packager actually asks:
**what changed from 140-2 to 140-3**, **which algorithms were added / removed /
constrained**, and **how approval is scoped by purpose** — all mapped onto how
**OpenSSL** (the dominant provider on Linux) exposes it.

**Framing:** FIPS 140-3 the standard does **not** define the algorithm list. The
approved set lives in **SP 800-140C** + the component standards (FIPS 197/180-4/186-5/
202/203-205, SP 800-38x/56x/90x/108/131A/132) and is enforced by **CAVP** testing.
So "140-3 added/removed X" means "the approved set evolved across the 140-3 era."
**Current as of September 2026** — re-verify dates/verdicts against NIST/OpenSSL.

> **"Not approved" ≠ insecure or slow.** Many algorithms flagged *not approved* in
> the tables below — **X25519/X448 key agreement, ChaCha20-Poly1305, BLAKE2/BLAKE3,
> Argon2/scrypt/bcrypt, and the NaCl/libsodium suite** — are modern, secure, and
> frequently **faster or more misuse-resistant** than their approved counterparts
> (ChaCha20-Poly1305 without AES-NI; Argon2 vs PBKDF2; X25519's simpler, safer
> implementation vs the NIST P-curves). They're excluded because approval requires
> **NIST standardization *and* a CMVP-validated module** — a government-assurance
> allowlist, **not** a ranking of cryptographic quality. The inverse has happened:
> Dual_EC_DRBG was FIPS-approved for a decade while backdoored. So a "not approved"
> row is a **compliance** blocker on a FIPS host, not a "weak crypto" finding — keep
> the two apart (SKILL step 8). Full treatment: `fips-primer.md` → "'Not approved' is
> an allowlist status, not 'insecure'."

## 1. What changed 140-2 → 140-3 (developers & packagers)

- **Structural.** 140-2 was a self-contained NIST standard; **140-3 wraps ISO/IEC
  19790:2012 + 24759**, with NIST deltas in the **SP 800-140x** series. Same four
  security levels, same CMVP/CAVP.
- **Timeline / Historical List (the packaging headline).** CMVP stopped accepting new
  **140-2** submissions on **2021-09-22**; **all 140-2 certificates moved to the
  Historical List** (2026-09-21 is the last Active-List day; Historical from 09-22).
  Target modules with an **active 140-3**
  certificate. RHEL 8 was the 140-2/140-3 mix; **RHEL 9 and 10 are 140-3-only**.
- **Self-tests.** 140-3 splits **pre-operational** from **conditional** self-tests and
  lets many **algorithm KATs defer to first use** — startup does less work.
- **Service indicator (new 140-3 requirement).** A module must indicate whether a
  service used approved crypto. OpenSSL added **FIPS indicators in 3.4**, and **3.5**
  made them per-approved-algorithm and stricter — "**no indicator ⇒ not approved**,"
  and it reclassified some operations as unapproved (below).
- **Entropy.** Sources must meet **SP 800-90B** (ESV validation), stricter than 140-2.
- **OE / certificate scope.** A cert is a *specific module build on specific tested
  platforms*; rebuilding, static-linking into your extension, or a different OS/arch
  voids it (see `native-crypto.md`).

## 2. OpenSSL provider model & RHEL mapping (the packaging crux)

OpenSSL 3 splits algorithms into **providers**:

- **default** — modern algs (AES, RSA, SHA-2/3, ECDSA, Ed25519, ChaCha20…).
- **fips** — the NIST-approved subset (a separate validated `fips` module).
- **base** — non-crypto only (key (de)serialization); load it alongside `fips`.
- **legacy** — MD4, MDC2, RIPEMD-160, Whirlpool; DES(single), Blowfish, CAST5, IDEA,
  SEED, RC2, RC4, RC5. **Not loaded by default.**

**In FIPS mode you load `fips` + `base` — not `default`, not `legacy`.** So:

- Everything in **legacy** is unavailable (MD4/RC4/DES/Blowfish/CAST5/IDEA/SEED/…).
- **default-only** algorithms are also unavailable: **MD5** (MD5 lives in *default*,
  not legacy), **3DES**, **ChaCha20-Poly1305**.

| RHEL | OpenSSL | FIPS module shape | Regime | Cert(s) |
| --- | --- | --- | --- | --- |
| 8 | 1.1.1 | monolithic FIPS module | **140-2** (Historical after 2026-09-21) | plan move to 9/10 |
| 9.0–9.6 | 3.0.x | standalone `fips` provider RPM (since 9.2) | **140-3** (first-ever) | #4746 (9.0), #4857 (9.2–9.6) |
| **9.7 / 9.8** | base lib **rebased to 3.5** (also NSS; 9.8 adds GnuTLS) | `fips` provider is the **reused 3.0.7 validated module** (not 3.5) | **140-3**; PQC **opt-in** via `DEFAULT:PQ`/`FIPS:PQ` | #4857 lineage |
| 10.0–10.1 | 3.x | reuses the RHEL 9 `fips` provider | **140-3 only** | (reused) |
| 10.2 | 3.5 | `fips` provider | **140-3**; PQC **on by default** (`DEFAULT`) | |
| upstream | 3.0 / 3.5 | `fips.so` provider | 3.0 module = 140-2 | #4282 (3.0) |

Packaging notes: `cryptography` PyPI wheels bundle their **own static OpenSSL** — that
crypto is **outside** the system `fips` provider, so it's a *module* finding regardless
of algorithm (`native-crypto.md`). Verify with `openssl list -providers`; RHEL toggles
via `fips-mode-setup`. On **RHEL 10 in FIPS mode**, PKCS#12 files use **PBMAC1**
(RFC 9579) and aren't readable by older tools.

> **A third-party FIPS cert is not RHEL's FIPS crypto — e.g. AWS-LC.** AWS-LC is FIPS
> 140-3 *validated*, but as **Amazon's own module** — a BoringSSL fork (certs
> #4631/#4816/#5314…) tested on **AWS-controlled operating environments** (Amazon
> Linux / Ubuntu on the earlier certs; Amazon Linux 2023 on the newer ones) —
> **outside RHEL's validated boundary.** RHEL's boundary is Red Hat's *own* modules:
> **OpenSSL, GnuTLS, NSS, Libgcrypt, and the Kernel Crypto API** (historically also
> OpenSSH/Libreswan), each with Red Hat certificates on RHEL OEs. **FIPS certs don't
> cross vendors:** Red Hat's don't cover AWS-LC, AWS-LC's don't cover RHEL, and
> incorporating an upstream-validated AWS-LC confers **no** cert on your build (you'd
> owe the OE/validation work yourself). Even `aws-lc-rs --features=fips` gives you a
> *statically bundled* AWS-LC validated on AWS's OEs — still outside RHEL's boundary.
> **Where this actually bites: Rust, not OpenSSL.** You'd rarely swap AWS-LC into
> OpenSSL on RHEL, but **`aws-lc-rs` is rustls's default crypto provider**, so a
> rustls-based extension (or any `aws-lc-rs` dependency) **statically bundles AWS-LC** —
> a *bundled-module* finding on RHEL even though AWS-LC "has a FIPS cert." (Amazon
> separately ships an *Amazon Linux* OpenSSL FIPS provider — also not RHEL's.) See
> `native-crypto.md` → Rust for `aws-lc-rs` fips-vs-stock detection; this is its "a FIPS
> cert ≠ *the* validated module in this environment," made concrete.

> **PQC on RHEL (as of 9.7/9.8).** RHEL 9.7 **rebased OpenSSL to 3.5** (and NSS; 9.8
> adds GnuTLS), so ML-KEM/ML-DSA are present on the RHEL 9 stream — but **off by
> default**: enable with `update-crypto-policies --set DEFAULT:PQ` (or `FIPS:PQ`).
> **The subtle part: the base library is 3.5.5 but the *validated FIPS provider* is
> the reused 3.0.7 module**, which predates PQC and therefore carries **no ML-KEM/
> ML-DSA**. ML-KEM lives only in the 3.5 **default** provider. Consequence, confirmed
> on UBI 9.8 in FIPS mode: `openssl genpkey -algorithm ML-KEM-768` is **refused**
> ("unsupported"), and `openssl list -providers` shows *"…OpenSSL FIPS Provider,
> version 3.0.7-…"*. So **In FIPS mode**, hybrid ML-KEM is supported only by fetching
> the **ECDH half from the validated `fips` provider** (the classical part stays
> FIPS-compliant; the ML-KEM half runs from the unvalidated default provider);
> `FIPS:PQ` turns the hybrid groups on. **RHEL 10.2** enables ML-KEM/ML-DSA in the
> plain `DEFAULT` policy (no subpolicy). **OpenSSH** PQ key exchange is **not** in
> RHEL 9.7 — use RHEL 10 for PQ SSH. (Verify any of this yourself with the container
> recipe below.)

## 3. Added / removed / constrained algorithms (OpenSSL-mapped)

### Added (approved in the 140-3 era)

| Algorithm | Standard (year) | OpenSSL exposure | Note |
| --- | --- | --- | --- |
| **EdDSA** (Ed25519/Ed448) | FIPS 186-5 (2023) | `EVP_PKEY_ED25519`/`ED448` | approved *signatures* (≠ X25519) |
| **ML-KEM** | FIPS 203 (2024) | OpenSSL 3.5 default provider | validated FIPS *module* trails the code |
| **ML-DSA / SLH-DSA** | FIPS 204/205 (2024) | OpenSSL 3.5 | same validation-lag caveat |
| **SHA-3 / SHAKE / KMAC / cSHAKE** | FIPS 202, SP 800-185 | `EVP_sha3_*`, `EVP_MAC` "KMAC-128/256" | |
| **AES-XTS** | SP 800-38E | `EVP_aes_256_xts` | **storage-only** (§4) |
| **AES-KW / KWP** | SP 800-38F | `id-aes*-wrap` | key wrap only |

### Removed / disallowed

| Algorithm | When / standard | OpenSSL | In FIPS mode |
| --- | --- | --- | --- |
| **DSA** (keygen + sign) | FIPS 186-5 (2023) | `EVP_PKEY_DSA` | not approved — removed from the approved set; OpenSSL's FIPS provider marks DSA keygen/sign **unapproved** (since 3.4) |
| **3DES / TDEA** | SP 800-131A (disallowed for encryption after 2023) | `EVP_des_ede3_*` (default) | absent from `fips` |
| **MD5** | never approved | `EVP_md5` (**default**, not legacy) | unavailable (fips+base) |
| **MD4 / RIPEMD-160 / Whirlpool / MDC2** | legacy | legacy provider | unavailable |
| **RC4 / single-DES / Blowfish / CAST5 / IDEA / SEED / RC2** | legacy | legacy provider | unavailable |
| **RSA/DH < 2048; EC < 224** | SP 800-131A | | rejected |
| **RSA PKCS#1 v1.5 encryption** | SP 800-56B | `RSA_PKCS1_PADDING` | not approved (use OAEP) |
| **Dual_EC_DRBG / X9.31 / FIPS 186-2 RNG** | removed | | gone |

### Constrained (same algorithm, new rules under 140-3 / OpenSSL 3.5)

| Item | Change |
| --- | --- |
| **AES-GCM IV** | an **externally-supplied IV** is now **unapproved** (3.5 indicator); use module-internal IV generation; 96-bit IV; ≤ 2³² invocations for the deterministic construction |
| **SHA-1** | *restricted*: HMAC/KDF OK, but signature **and verification** with SHA-1 are unapproved (3.5) |
| **RSA v1.5** | *signatures* legacy-verify only; keygen ≥ 2048 |
| **PBKDF2** | the only approved password KDF; RHEL FIPS substitutes it for Argon2; salt/iteration requirements (SP 800-132) |
| **Indicators** | 3.4 added them; 3.5: "no indicator ⇒ not approved"; non-OpenSSL providers (RHEL/SUSE) may use the return code instead |

## 4. Scoped by purpose — there is **no** separate "at-rest" vs "in-transit" list

FIPS 140-3 has **one** approved set; individual functions are scoped to a *purpose*,
which reads like use-case differentiation:

| Purpose | Approved primitives | OpenSSL | Caveat |
| --- | --- | --- | --- |
| **Data at rest / storage** | **AES-XTS-256**, AES-GCM, AES-CBC+HMAC | `EVP_aes_256_xts` / `_gcm` | **XTS is storage-only** (SP 800-38E); the two keys must differ; ≤ 2²⁰ blocks per data unit |
| **Data in transit (TLS/IPsec)** | AES-GCM/CCM; suites per SP 800-52/77 | via `libssl` + crypto-policies | ChaCha20-Poly1305 **not** approved; GCM IV per-protocol |
| **AEAD (general)** | AES-GCM, AES-CCM | `EVP_*_gcm`/`_ccm` | GCM IV/tag/invocation limits (above) |
| **Key wrap / transport** | AES-KW/KWP; **RSA-OAEP** | `id-aes*-wrap` | not RSA v1.5 |
| **Key agreement / handshake** | ECDH (P-256/384/521), ffDHE groups, ML-KEM (§5) | `EVP_PKEY_derive` | **X25519/X448 not approved** |
| **Signature / auth** | RSA-PSS, ECDSA, EdDSA, ML-DSA, SLH-DSA | | DSA removed; v1.5 sign legacy |
| **Password / credential at rest** | **PBKDF2** (SP 800-132) | `EVP_KDF` "PBKDF2" | scrypt/Argon2/bcrypt not approved |
| **Integrity / MAC** | HMAC, CMAC, GMAC, KMAC | `EVP_MAC` | not standalone Poly1305 |

**The only true purpose-restriction in the standard is `XTS = storage only`;** GCM
carries IV/usage caveats. The "which suite for at-rest vs in-transit" *selection* comes
from **SP 800-52 (TLS) / 800-77 (IPsec) / 800-111 (storage)** and, operationally, RHEL
**crypto-policies** — the OS layer, **not** FIPS 140-3.

## 5. Practical PQC: which hybrids are actually usable

RFC 10024 defines three TLS 1.3 hybrid KEMs (ECDHE + ML-KEM). The catch is that the
**common one is not strict-FIPS**, and the **FIPS one is barely deployed client-side**:

| Group (code) | Composition | IANA "Recommended" | Strict-FIPS? | Deployed where |
| --- | --- | --- | --- | --- |
| **X25519MLKEM768** (0x11EC) | X25519 + ML-KEM-768 | **Y** | **No** — X25519 not NIST-approved | **Default everywhere**: Chrome, Firefox, Safari, Edge, Cloudflare, OpenSSL 3.5, Go; ~95% of PQ connections |
| **SecP256r1MLKEM768** (0x11EB) | P-256 + ML-KEM-768 | N | **Yes** (both NIST-approved; SP 800-56Cr2 ordering) | Server/enterprise/federal only — **browsers don't offer it by default** |
| **SecP384r1MLKEM1024** (0x11ED) | P-384 + ML-KEM-1024 | N | Yes (CNSA 2.0 strength) | rare; high-assurance |

The practical tension:

- **X25519MLKEM768** is what browsers and CDNs negotiate, but its X25519 primitive
  fails a strict boundary (e.g. Go **`fips140=only` rejects it**). Fine for *good*
  PQC; **not** for strict-FIPS.
- **SecP256r1MLKEM768** is the strict-FIPS choice, **but mainstream clients don't send
  it**, so a FIPS server that only offers it typically falls back to **classical**
  (no PQC) with real browsers.
- **CDN reality — edge PQC is X25519MLKEM768 across the board.** **Akamai** documents
  **X25519MLKEM768 only**; **Fastly** auto-enables ML-KEM for TLS 1.3 clients (i.e.
  **X25519MLKEM768** in practice); and **Cloudflare's** PQC-support docs list
  **X25519MLKEM768** as what it deployed — the "all three hybrids" list is under the
  docs' **Native libraries** section (per-library support, e.g. AWS-LC), not a
  statement of Cloudflare's own edge groups. **None of the three
  documents `SecP256r1MLKEM768` as an edge option.** ("Not documented" isn't proof
  they reject it, but) a P-256 + ML-KEM server has **little real client/CDN reach**
  today, so strict-FIPS PQC over public CDNs is largely unavailable — verify against
  each provider's current docs.
- A **FIPS-validated ML-KEM module** already exists — **AWS-LC-FIPS** was first to
  include ML-KEM in a 140-3 validation — but that's **AWS's module, not RHEL's** (see
  the AWS-LC callout in §2). On RHEL, ML-KEM comes from the **system OpenSSL 3.5 `fips`
  provider** (9.7+/10, above). So "ML-KEM is FIPS-approved" is true at the *algorithm*
  level, but whether *your* module is validated for it — and whether it's the one your
  platform actually validates — is a separate question (`native-crypto.md`).

**Audit takeaway:** seeing `X25519MLKEM768` is good PQC hygiene but is **not** a
strict-FIPS key exchange; a strict-FIPS deployment needs `SecP256r1MLKEM768` and must
accept limited peer/CDN reach (or classical fallback). Report the hybrid actually
negotiated and the boundary it needs, per `fips-primer.md` → Post-quantum.

## 6. Verify FIPS behavior in a container (no FIPS host needed)

You can check what a RHEL/UBI build actually does in FIPS mode without a FIPS-enabled
machine. OpenSSL decides FIPS mode from `/proc/sys/crypto/fips_enabled` plus the
crypto-policy back-ends; **fake the kernel flag** with a read-only bind mount and set
the policy **inside** the container (so it matches that image's version — no host
`crypto-policies` mount, which would break on a non-matching or non-RHEL host):

```bash
printf '1\n' > fips_enabled            # the kernel flag OpenSSL reads
podman run --rm --security-opt label=disable \
  -v ./fips_enabled:/proc/sys/crypto/fips_enabled:ro \
  registry.access.redhat.com/ubi9:9.8 bash -c '
    update-crypto-policies --set FIPS
    openssl list -providers | grep -A1 -i "fips provider"   # → RHEL 3.0.7 module
    echo x | openssl dgst -md5                               # → refused (unsupported)
    echo x | openssl dgst -sha256                            # → ok
    openssl genpkey -algorithm ML-KEM-768 >/dev/null         # → refused (no PQC in 3.0.7)
    openssl genpkey -algorithm EC -pkeyopt group:P-256 >/dev/null  # → ok
'
```

Use it to confirm, per artifact/OS version: which `fips` provider version is validated
(the version string), whether a given algorithm is refused in FIPS mode, and which
provider serves it (`openssl list -digest-algorithms`/`-kem-algorithms`).

**This is not real FIPS mode — it's a hack for quick testing.** The **kernel is still
in standard mode**; you only *fake* the flag OpenSSL reads (`/proc/sys/crypto/fips_enabled`)
so userspace enters full FIPS mode. It exercises OpenSSL's FIPS wiring and lets you
observe what full FIPS mode refuses/allows, but it is **not** a validated deployment
(no kernel FIPS, no module integrity self-tests, no attestation) and proves nothing
about compliance. Use it only to probe behavior.

**Caveats.** **Match the
UBI tag to your target RHEL minor** (`ubi9:9.6`/`9.8`/`ubi10`…): the base OpenSSL, the
validated `fips` provider version, and PQC availability all differ across minors. The
older, host-dependent form (`-v /usr/share/crypto-policies/back-ends/FIPS:/etc/crypto-policies/back-ends:ro`)
only works when the **host** is the same RHEL version — prefer the in-container
`update-crypto-policies` above.

## Sources

- NIST — [FIPS 140-3](https://csrc.nist.gov/pubs/fips/140-3/final), [CMVP transition](https://csrc.nist.gov/projects/cryptographic-module-validation-program), [SP 800-131A Rev.2](https://csrc.nist.gov/pubs/sp/800/131/a/r2/final), [FIPS 186-5](https://csrc.nist.gov/pubs/fips/186-5/final), [FIPS 203/204/205](https://csrc.nist.gov/pubs/fips/203/final), SP 800-38E (XTS) / 800-38D (GCM) / 800-56C (KDF).
- OpenSSL — [legacy provider](https://docs.openssl.org/3.5/man7/OSSL_PROVIDER-legacy/), [`fips_module`](https://docs.openssl.org/master/man7/fips_module/), [README-FIPS](https://github.com/openssl/openssl/blob/master/README-FIPS.md) (indicators in 3.4/3.5).
- Red Hat — [OpenSSL: FIPS 140-2 upstream to 140-3 downstream](https://www.redhat.com/en/blog/openssl-fips-140-2-upstream-140-3-downstream), [RHEL FIPS certificates](https://access.redhat.com/compliance/fips), [Prepare for a post-quantum future with RHEL 9.7](https://www.redhat.com/en/blog/prepare-post-quantum-future-rhel-97), [RHEL 9.7 release notes](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/9.7_release_notes/new-features), [RHEL core cryptographic components](https://access.redhat.com/articles/3655361).
- PQC TLS — [RFC 10024](https://www.rfc-editor.org/info/rfc10024/), [Cloudflare PQC support](https://developers.cloudflare.com/ssl/post-quantum-cryptography/pqc-support/), [Akamai PQC on the edge](https://www.akamai.com/blog/security/akamai-enables-post-quantum-cryptography-edge), [Fastly PQC](https://www.fastly.com/blog/future-proofing-tls-encryption-against-quantum-threats).
- AWS-LC (separate module) — [AWS-LC is now FIPS 140-3 certified](https://aws.amazon.com/blogs/security/aws-lc-is-now-fips-140-3-certified/), [AWS-LC FIPS 3.0 with ML-KEM](https://aws.amazon.com/blogs/security/aws-lc-fips-3-0-first-cryptographic-library-to-include-ml-kem-in-fips-140-3-validation/), [CMVP security policy #4816 (OEs = Amazon Linux/Ubuntu)](https://csrc.nist.gov/CSRC/media/projects/cryptographic-module-validation-program/documents/security-policies/140sp4816.pdf); rustls uses `aws-lc-rs` as its [default provider](https://docs.rs/rustls/latest/rustls/crypto/index.html).
