# FIPS 140-3 primer: what's approved, what isn't

Cited from the sources in `SKILL.md`. **Current as of September 2026** — crypto
policy and NIST approval status move (transition dates land, SP 800 revisions land,
certificates drift). If you are reading this months later, **re-verify every
verdict against the linked NIST/vendor pages**; treat specific dates and
approved/not-approved calls below as "true when written," not permanent. This
primer is the algorithm/parameter reference; the *module* (validated-provider)
requirement is in `native-crypto.md`.

## What FIPS 140-3 actually governs

FIPS 140-3 is the U.S. federal standard of **security requirements for
cryptographic modules** — it validates that a *module* implements approved
algorithms correctly and protects keys. It adopts ISO/IEC 19790:2012, defines four
security levels, superseded FIPS 140-2, and is operationalized through the SP
800-140x series and the **CMVP** validation program.
(<https://csrc.nist.gov/pubs/fips/140-3/final>)

Two consequences the audit turns on: **compliance attaches to a specific validated
binary**, not to an algorithm or a source tree (see `native-crypto.md`); and only
algorithms in the "approved security functions" list may be used in a security
context.

## "Not approved" is an allowlist status, not "insecure"

The single most important thing to explain to a human reading a FIPS finding:
**FIPS approval is an allowlist, not a verdict on cryptographic strength.** It
blocks two very different things, and conflating them is the most common mistake in
a FIPS review:

1. **Genuinely weak or broken crypto** — MD5, SHA-1 for signatures, single/double
   DES, 1024-bit RSA, AES-ECB for data. Avoid these *everywhere*, FIPS or not.
2. **Modern, secure crypto that NIST simply hasn't approved** — Curve25519/X25519,
   ChaCha20-Poly1305, BLAKE2/BLAKE3, XSalsa20, Argon2/scrypt, libsodium/NaCl.
   Widely regarded as excellent; excluded only because they aren't on NIST's list.

NIST's own guidance says non-approved algorithms can be cryptographically sound
(FIPS 140-3 IG 2.4.A even permits some inside approved services with
documentation), and the inverse has happened: **Dual_EC_DRBG was FIPS-approved for
a decade while backdoored** — approval never guaranteed security.

An algorithm is approved only after clearing **two independent gates**:

- **Standardized by NIST** — written into a FIPS PUB or SP 800 document through
  NIST's own public process (often a competition or a formal adoption).
- **Implemented in a CMVP-validated module** — that code path is lab-tested
  (`native-crypto.md`). For compliance NIST treats *unvalidated* crypto as
  providing **no** protection — so even an approved algorithm in a non-validated
  library doesn't count.

That is why the three most-asked-about cases are blocked — for **process**
reasons, not weakness:

- **libsodium / NaCl** (and `pynacl`, `libnacl`) fail *both* gates. Its primitives
  are mostly non-NIST (X25519, XSalsa20/ChaCha20-Poly1305, BLAKE2b, Argon2), *and*
  libsodium is not a CMVP-validated module — so even Ed25519 (approved as an
  *algorithm* since FIPS 186-5) doesn't count when it comes from libsodium.
- **Curves.** NIST approves only the curves it standardized (P-256/384/521, …).
  **secp256k1** (Bitcoin/Ethereum) was rejected outright — NIST saw "no compelling
  advantage." **Curve25519/Curve448** the *curves* were added to SP 800-186 (2023),
  but the **X25519/X448 key-agreement schemes remain unapproved**: absent from SP
  800-56A, and NIST **declined again in a July 2025 proposal**, deprioritizing new
  classical key exchange in favour of the PQC transition.
- **BLAKE2 / BLAKE3** were never standardized. NIST ran the SHA-3 competition and
  chose **Keccak**, not BLAKE (a finalist); BLAKE2/3 came later and never went
  through a NIST process, so they appear in no FIPS 180-4 / 202 entry. (Their usual
  use — checksums, dedup, content addressing — is a non-security use that can be
  fine; see `usedforsecurity`.)

**Audit consequence:** a "non-approved crypto" finding on a FIPS host is *not* the
same as a "weak crypto" finding — keep them in separate classes (SKILL step 8).
Report ChaCha20-Poly1305 or X25519 as **strong but unapproved** (a compliance
blocker on a FIPS host, a non-issue off one); report MD5-for-signatures or AES-ECB
as **actually broken** (fix everywhere).

## Approved vs non-approved, by algorithm class

| Class | Approved | Not approved (flag in a security context) |
|---|---|---|
| **Hash** | SHA-2 (224/256/384/512, 512/224, 512/256) [FIPS 180-4]; SHA-3 & SHAKE128/256 [FIPS 202] | **MD5, MD4, RIPEMD-160, SM3, Whirlpool** (refused); **BLAKE2, BLAKE3** (never approved) |
| **Hash — special** | **SHA-1**: *restricted* — allowed for non-signature uses (HMAC, KDF) but **disallowed for digital signatures**, and phased out for all uses by **2030-12-31** | — |
| **DRBG / RNG** | SP 800-90A: Hash_DRBG, HMAC_DRBG, CTR_DRBG | Any non-SP-800-90A PRNG (e.g. Python `random` / Mersenne Twister) for security |
| **MAC** | HMAC (approved hash), CMAC, GMAC, KMAC | MACs on non-approved primitives (keyed BLAKE2, standalone Poly1305) |
| **KDF** | HKDF (SP 800-56C), KBKDF (SP 800-108), **PBKDF2** (SP 800-132) | **scrypt, Argon2** (RHEL FIPS substitutes PBKDF2 for Argon2); **bcrypt** |
| **Key agreement** | ECDH on NIST curves; finite-field DH with approved safe-prime (ffDHE/MODP) groups [SP 800-56A] | **X25519 / X448** (not approved; no CAVP test) |
| **Signature** | RSA, ECDSA on NIST curves, **EdDSA (Ed25519, Ed448)** [FIPS 186-5, 2023] | secp256k1 and other non-NIST curves; **DSA** (removed in 186-5) |
| **Symmetric** | **AES** modes CBC/CTR/CFB/OFB/GCM/CCM/XTS/KW/KWP [FIPS 197]; **ECB** as a primitive only | **ChaCha20-Poly1305**; **3DES/TDEA** (disallowed for encryption after 2023); **AES-ECB for data** (approved but insecure — see below) |

### The counterintuitive cases (correcting common assumptions)

- **Ed25519 ≠ X25519.** Same curve family, opposite verdicts: **Ed25519
  *signatures* are approved** (FIPS 186-5, 2023); **X25519 *key agreement* is
  not** — the Curve25519 *curve* is in SP 800-186, but the X25519/X448 *schemes*
  are absent from SP 800-56A and NIST declined to add them again in July 2025.
  Don't blanket-flag "25519".
- **SHA-1 is not MD5.** SHA-1 is *restricted* (bad for signatures/integrity, OK
  for HMAC/KDF, gone by 2030), whereas MD5 was never approved. The reference
  ruleset models this split (`refused_hash_algorithms` vs
  `restricted_hash_algorithms`).
- **BLAKE is simply unapproved**, not "blocked" by a mechanism — it's absent from
  FIPS 180-4 and 202. A *security* use fails FIPS; a checksum/dedup use can be
  fine (see `usedforsecurity` below).
- **scrypt / Argon2 / bcrypt are not approved** despite being *stronger* password
  hashes than PBKDF2 — approval ≠ cryptographic quality. Only PBKDF2 is approved.
- **ChaCha20-Poly1305 is not approved** despite being modern and safe.

### Approved ≠ used securely (insecure crypto, independent of FIPS)

A primitive can be on the approved list and still be broken *as used*. These are
weak-crypto findings the audit must raise even on a FIPS host — flag them as their
own class (SKILL step 8), not as FIPS-140 violations:

- **AES-ECB for data is broken.** ECB is approved as a bare primitive (it appears in
  FIPS 197 / SP 800-38A) but leaks plaintext structure — identical blocks encrypt
  identically (the "ECB penguin"). Flag any ECB use for confidentiality; want an
  AEAD (AES-GCM) or at least CBC/CTR with a random IV.
- **RSA needs modern padding.** Use **OAEP for encryption** and **PSS for
  signatures**. **PKCS#1 v1.5 *encryption* is Bleichenbacher-vulnerable** (adaptive
  chosen-ciphertext / Marvin timing oracle); textbook/"raw" RSA (no padding) is
  worse. v1.5 *signatures* are legacy-tolerated but PSS is preferred. Flag
  `PKCS1v15()` for encryption and any unpadded RSA.
- **Don't hand-roll RSA (or any primitive).** A pure-Python `pow(m, e, n)` /
  `divmod`-based modexp is not constant-time; message/exponent blinding narrows but
  does not close the side channel, and such code invariably lacks padding, RNG, and
  parameter checks. Flag hand-written RSA and the pure-Python `rsa` package; use a
  vetted library binding a validated module (`python-audit.md`).

## Minimum key sizes & curves (SP 800-131A Rev. 2)

- **RSA** ≥ **2048** bits (keygen/signing).
- **ECDSA/ECDH** curve ≥ **224** bits; approved NIST curves **P-256, P-384,
  P-521** (P-224 at 112-bit strength). Non-NIST curves (secp256k1) are not
  approved.
- **Symmetric** ≥ 112-bit strength (so single/double-DES out; AES-128+ in).
- *Forward-looking:* draft SP 800-131A **Rev. 3** raises the floor to 128-bit
  security by end of 2030 and folds asymmetric transitions into PQC migration —
  still a draft; note it, don't enforce it.

## The `usedforsecurity` escape hatch (hashes)

Python `hashlib` constructors take `usedforsecurity=` (3.9+, default `True`). On a
FIPS system a bare `hashlib.md5(...)` raises; `usedforsecurity=False` documents a
**non-security** use (dedup, cache keys, checksums, content addressing) and may be
allowed. Caveats: it must **not** be used for security purposes; a strict
approved-only OpenSSL can reject it anyway (no non-FIPS impl to fall back to); and
some hardened Python builds drop MD5/BLAKE modules entirely. See `python-audit.md`.

## Post-quantum (FIPS 203/204/205)

Finalized 2024-08: **FIPS 203 ML-KEM** (ex-Kyber; ML-KEM-512/768/1024), **FIPS 204
ML-DSA** (ex-Dilithium), **FIPS 205 SLH-DSA** (ex-SPHINCS+) — all approved.
FN-DSA/Falcon (future FIPS 206) not yet finalized.

**`X25519MLKEM768` hybrid** (X25519 + ML-KEM-768) dominates real TLS deployment
(Chrome/Firefox/OpenSSL 3.5/Go 1.24). Its FIPS status is **genuinely disputed**:
usable when the validated boundary *includes* X25519 (Go blog, AWS-LC, rustls), but
Go's strict **`fips140=only` rejects the X25519 primitive** and breaks the
handshake. Practical rule: acceptable under a validated boundary that includes it;
**prefer `SecP256r1MLKEM768`** (P-256 share) where strict FIPS is required. For
*good non-FIPS crypto*, still prefer a hybrid PQC handshake over classical-only.

## Standards quick map (for a finding's citation)

FIPS **140-3** modules · **180-4** SHA-1/SHA-2 · **186-5** RSA/ECDSA/EdDSA ·
**197** AES · **198-1** HMAC · **202** SHA-3/SHAKE · **203/204/205** ML-KEM/
ML-DSA/SLH-DSA. SP **800-131A** transitions/key sizes · **800-56A** key agreement ·
**800-90A** DRBG · **800-108** KBKDF · **800-132** PBKDF2 · **800-52** TLS config.
