# FIPS boundary, PQC, trust, and crypto-policies for Rust

Companion to SKILL steps 5–7. The *fundamentals* (what FIPS 140-3 governs,
validated-vs-compliant-vs-capable, the approved-algorithm and PQC-hybrid tables, the
container FIPS recipe) are owned by the sibling skill and **cited, not repeated**:

- [`../crypto-fips-audit/reference/native-crypto.md`](../crypto-fips-audit/reference/native-crypto.md) — the validated-module requirement; the AWS-LC callout; the existing Rust detection notes.
- [`../crypto-fips-audit/reference/fips-140-3-and-openssl.md`](../crypto-fips-audit/reference/fips-140-3-and-openssl.md) — 140-2→140-3, the algorithm tables, the PQC-hybrid table (§5), the provider-lag detail, the podman FIPS-in-a-container recipe (§6).
- [`../crypto-fips-audit/reference/fips-primer.md`](../crypto-fips-audit/reference/fips-primer.md) — approved vs non-approved per class; "'non-approved' ≠ insecure."

## The validated-module boundary, applied to Rust

Approved crypto must come from a CMVP-**validated** module. On the enterprise-Linux
baseline that is the **system OpenSSL** (plus the distro's other system modules). A
statically-linked or vendored crypto library is a **different binary** than the
validated one, so it inherits **no certificate** — even if the algorithm is approved
and the version matches, and it can't honor system crypto-policies. For Rust:

| Posture | In the system validated module? | Verdict |
| --- | --- | --- |
| `ring` compiled in | No (not validated at all; no FIPS path) | class 1 |
| `aws-lc-rs` default (stock) | No (bundled, non-FIPS) | class 1 |
| `aws-lc-rs --features=fips` | **No** — see the callout below | class 1 on this distro |
| system OpenSSL, dynamically linked | **Yes** | target state |

> **AWS-LC is FIPS-validated, but it is *not an allowed crypto library* on the
> enterprise distro.** This is the point that trips people up: AWS-LC-FIPS has its own
> CMVP certificate — but it is **AWS's module, validated on AWS-controlled operating
> environments**, *not* the distro's validated module. **FIPS certificates do not cross
> vendors**: the distro trusts **only its own** validated modules (its OpenSSL, NSS,
> GnuTLS, libgcrypt, kernel), and bundling an upstream-validated AWS-LC confers **no**
> certificate on your build. So `aws-lc-rs --features=fips` — which statically bundles
> `aws-lc-fips-sys` — is **still outside the boundary** and **not an approved provider**
> there, *even though it "has a FIPS cert."* "Has a FIPS cert" ≠ "is the approved module
> in this environment." (It also drags in CMake/Go/clang/bindgen to build.) The only
> in-boundary Rust path is the **dynamically-linked system OpenSSL**. Full treatment:
> the sibling's `fips-140-3-and-openssl.md` → AWS-LC callout and
> `native-crypto.md` → "Has a FIPS cert ≠ is the approved module here."

**FIPS mode needs no app opt-in.** When the binary links the system OpenSSL and the
**host** is in FIPS mode (kernel `fips=1`; a container inherits it from a FIPS host via
the runtime), the FIPS provider is selected automatically and applies **per
operation**. The app does not "turn on FIPS." Audit-adjacent: make sure a
verification-bypass flag (`danger_accept_invalid_certs`/`_hostnames`, "accept invalid
hostnames") is **not** shipped on in production — gate it behind a dev-only feature
(class 3 if not).

## PQC in Rust TLS

The deployable PQC mechanism is **hybrid key exchange** (classical + ML-KEM), which
mitigates "harvest now, decrypt later" and is backward-compatible: a non-PQC TLS 1.3
peer falls back to classical ECDHE. Scope is **key exchange** (ML-KEM); PQC
*signatures* for certs (ML-DSA/SLH-DSA) are a separate, later concern.

- **rustls** moved ML-KEM into the main crate around **0.23.22**; **`prefer-post-quantum`**
  makes **X25519MLKEM768** the top KX group and became default in the **0.23.25–0.23.27**
  range — *sources disagree on the exact version, so confirm against the pinned
  `Cargo.lock`*. It applies **only to the aws-lc-rs provider** (which supplies ML-KEM).
  A quick check: a packet capture should show `X25519MLKEM768 (0x11ec)` first in the
  ClientHello "supported groups"; an old build lists it last or not at all. Since it's
  often already default, upstream work is frequently just a **regression test pinning
  the KX order** so the hybrid isn't silently dropped.
- **System OpenSSL** provides ML-KEM when the crypto-policy enables it (OpenSSL 3.5+;
  enabled via a `DEFAULT:PQ`-style subpolicy, on-by-default on newer distro releases).
  **But *which* system-OpenSSL path you took — and *who runs the TLS handshake* — decides
  how PQC reaches the wire:**
  - **OpenSSL (libssl) owns the handshake** (`native-tls` / direct `openssl` — paths 2–4):
    OpenSSL does the TLS protocol **and** selects the groups, so it offers
    `X25519MLKEM768` under `DEFAULT:PQ` and classical under the default policy — it
    **follows the system policy** for group selection and ordering.
  - **Provider swap** (`rustls-native-ossl` — path 1): **rustls runs the TLS protocol in
    Rust**; OpenSSL's **libcrypto/EVP** supplies only the primitives (it is a rustls
    `CryptoProvider`, not libssl). So **rustls** decides which groups are offered, from the
    provider's supported set — and `rustls-native-ossl` **≥ 0.3.1 built against OpenSSL
    3.5.0+ makes `X25519MLKEM768` the preferred group** (offered first), so PQC works out
    of the box here (0.3.0 had no hybrid). native-ossl requires OpenSSL 3.5.0+ anyway, so
    the hybrid is the normal case; rustls (not libssl) still owns the finer suite/group
    *ordering*.

### The strict-FIPS tension and the provider lag

- **`X25519MLKEM768` *is* FIPS-approvable — the ML-KEM-first ordering is why.** NIST
  **SP 800-56Cr2** allows a shared secret `Z = S1‖S2` where **S1 is from a FIPS-approved
  scheme** and S2 from any method; `X25519MLKEM768` deliberately places the **approved
  ML-KEM-768 first** (X25519 is the allowed auxiliary S2), so the combiner is approved.
  (`SecP256r1MLKEM768`/`SecP384r1MLKEM1024` put the EC half first because *both* halves are
  approved.) OpenSSL's 3.5 FIPS provider marks `X25519MLKEM768`, `SecP256r1MLKEM768`,
  `SecP384r1MLKEM1024` as **`fips=yes`** (only `X448MLKEM1024` is `fips=no`); RFC 10024
  ties all three to SP 800-56C. **X25519 being unapproved does not disqualify the hybrid.**
- **The real blockers are elsewhere.** (1) **Provider lag** — the validated module must
  actually implement *certified* ML-KEM; an older certified FIPS provider that predates PQC
  carries **no ML-KEM**, so it simply can't negotiate the hybrid. (2) **Policy
  conservatism** — some strict modes still reject X25519-containing hybrids by choice (Go
  `fips140=only`; some distro FIPS policies), so prefer `SecP256r1MLKEM768` *there*. (3) The
  formal basis is still maturing (SP 800-227; an SP 800-56C update to allow either order).
  Table + CDN reach: the sibling's `fips-140-3-and-openssl.md` §5.
- **So FIPS + PQC is often not co-functional *yet* — because of provider lag, not the
  algorithm.** Where the certified module lacks ML-KEM, FIPS mode has no PQC to offer while
  a `DEFAULT:PQ` policy gives PQC *outside* FIPS mode. **"FIPS host → no PQC" there is
  expected, not a compliance failure** — don't score it as a defect.

## Trust store

- **`webpki-roots`** (and the family: `webpki-root-certs`, any crate shipping a
  `*.pem`/`cacert.pem` CA set) = bundled Mozilla/vendor roots compiled into the binary →
  bypasses OS trust management (enterprise/private CAs, TLS-inspecting middleboxes,
  revocation); updates need a recompile. **A policy / system-integration issue (class 2),
  not FIPS-140** — governed by distro trust-management policy (and STIG/CC in those
  contexts), per the sibling's `trust-store.md`. Symptom: `curl`/`npm` work, the Rust
  binary fails `UnknownIssuer`/`invalid peer certificate`.
- **`rustls-native-certs`** reads the OS store (respects local add *and* remove, honors
  `SSL_CERT_FILE`/`SSL_CERT_DIR`); **`rustls-platform-verifier`** is the steered-to
  option for full platform verification. These fix the **trust source only** — they do
  **not** move the crypto into the validated module. A "native CA certs" flag on a
  pure-Rust client changes where roots come from, nothing more.
- A **system-OpenSSL-backed path** lets OpenSSL own X.509 chain building, verification,
  and hostname checks (`X509_verify_cert`) and drop bundled roots entirely — this holds
  for `native-tls`/direct (libssl), **and `rustls-native-ossl` can route certificate
  validation through OpenSSL too** (so the provider swap fixes crypto *and* trust in one
  move, not just the primitives).

Which compliance regime actually governs a bundled trust store — distro packaging
policy / STIG / CC, and explicitly **not** FIPS-140 or crypto-policies — is in the
sibling's [`trust-store.md`](../crypto-fips-audit/reference/trust-store.md).

## System crypto-policies

Enterprise Linux centrally controls TLS versions/ciphers/groups across TLS/SSH/IPsec
via system-wide crypto-policies; `update-crypto-policies` writes per-backend files that
**OpenSSL/GnuTLS/NSS read automatically**.

- **rustls does not read them** — true for **both** `ring` and `aws-lc-rs` (rustls issue
  [#2402](https://github.com/rustls/rustls/issues/2402)). It uses its own
  `CryptoProvider` defaults.
- **Containers don't inherit the host policy** — each image carries its own; the policy
  is read from the image filesystem. For an OpenSSL-backed component, switching the
  **runtime** stage to a policy-enabled (e.g. PQ) base image is enough to pick it up; no
  special builder image is needed. But a base-image swap only helps a component that
  **actually uses system OpenSSL** — a pure-Rust `rustls` component needs the TLS
  migration first.
- **What an OpenSSL path buys, precisely.** Routing primitives through system OpenSSL via
  the **provider swap** gets you **FIPS enforcement per operation** (a primitive the FIPS
  module forbids fails at execution) — but it does **not** apply the crypto-policy's
  suite/group *selection or ordering*: that is a libssl mechanism, and under the provider
  swap **rustls** drives the handshake from its own fixed lists, so a non-FIPS policy like
  `DEFAULT:PQ`/`FUTURE` is **not** honored for negotiation. Full policy control (cipher
  string + KX selection/ordering, and the policy's algorithm availability reaching the
  wire) requires the whole handshake in OpenSSL (`native-tls`/direct — paths 2–4 in
  `tls-backends.md`).

## Acceptance checks (inside a FIPS host / policy-enabled container)

```bash
update-crypto-policies --show                     # e.g. DEFAULT:PQ, or FIPS
openssl list -kem-algorithms | grep -i ml-kem     # ML-KEM-512/768/1024 ⇒ PQC available via system OpenSSL
openssl list -providers                            # which fips provider version is loaded (validated module)
openssl s_client -connect host:443 -groups X25519MLKEM768 </dev/null 2>&1 | grep -iE 'cipher|group'
# packet capture: confirm X25519MLKEM768 offered and *preferred* in the ClientHello
```

Combine with the `cargo tree` / binary checks in `detection.md`: the build must carry
**no** bundled non-validated crypto, and the binary must **dynamically link the system
`libcrypto`**. For a whole binary/image, `check-payload` validates Rust binaries too.
