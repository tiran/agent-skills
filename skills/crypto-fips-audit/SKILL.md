---
name: crypto-fips-audit
description: >-
  Audit a Python package — and any C/C++/Go/Rust code it ships — for its use of
  cryptography, across three use cases: inventory what crypto a package uses at
  all (algorithms, providers, linkage, RNG, CA stores), find insecure or weak
  cryptography, and assess FIPS 140-3 / NIST compliance. Flags insecure use of
  approved primitives (AES-ECB, RSA PKCS#1 v1.5, static IV/nonce, `random` for
  secrets, timing-unsafe compares, disabled TLS verification), weak RSA/EC key
  sizes, and — for FIPS — refused hashes (MD5, MD4, RIPEMD-160), restricted ones
  (SHA-1), non-approved primitives (BLAKE2/3, ChaCha20-Poly1305, 3DES,
  scrypt/Argon2/bcrypt, X25519/X448 key agreement, secp256k1), vendored or
  statically linked crypto (bundled OpenSSL/BoringSSL/AWS-LC/NSS/GnuTLS/libgcrypt/
  nettle/libsodium) that escapes the system validated module, hardcoded TLS
  versions/ciphers that bypass crypto-policies, bundled CA trust stores, and
  problematic PyPI deps (bcrypt, pycryptodome, pynacl, ecdsa, rsa, m2crypto, …).
  Source-first, then confirmed against the built wheel/binaries. Gathers evidence;
  does not certify compliance.
---

# Audit a Python package's cryptography (weak crypto and FIPS 140-3)

**Status: Experimental.** Grounded in the sources below (NIST FIPS/SP, Red Hat/
Fedora crypto-policy docs, Go/Rust/PyPI docs) and the reference scanner; the step
order is a new draft and crypto policy moves — **verify findings against the cited
sources** and treat this as an assessment aid, not an authority.

**It gathers evidence and assesses risk; it does not certify FIPS compliance.**
Only a NIST CMVP validation makes a module *validated*. This skill tells you where
a package is *likely* to break on a FIPS-enforcing host or use non-approved crypto;
report findings as evidence, never as a pass/fail certification.

Throughout, **"FIPS"** means **FIPS 140-3 and the related NIST standards** (FIPS
180-4, 186-5, 197, 198-1, 202, 203–205, SP 800 series); `reference/fips-primer.md`
maps them.

## What this skill answers — three use cases

Scope to the one you need (step 1); each builds on the one before it:

1. **Does the package use cryptography at all?** — *inventory only.* Direct crypto:
   what algorithms, which providers and linkage (system/bundled/static/opaque), CA
   stores, RNG, and any code that **modifies** TLS/crypto settings. Steps 2 and 5
   gather it (`scripts/scan_crypto.py`, `reference/binary-inspection.md`); stop here
   for a crypto-agility / CBOM inventory. No verdicts. **Not crypto use:** merely
   calling an HTTP client (`requests`/`httpx`/`urllib`) for an HTTPS request with
   default settings — the crypto lives in that library and the system OpenSSL, not
   this package. Count it only when the package **changes** crypto behaviour (custom
   `SSLContext`, `verify=False`, `set_ciphers`, pinned TLS version, its own cipher/
   curve list, `ctypes` crypto loads, or it ships/calls crypto directly). The same
   guard covers native client bindings (DB/queue/auth: `pycurl`, `psycopg2`,
   `pyzmq`, `grpcio`, `gssapi`, …) — a default connection isn't the package's
   crypto, but a **bundled** crypto copy, a TLS/cipher/enctype override, or an
   inherently non-approved primitive (pyzmq CURVE, grpcio's BoringSSL) is
   (`reference/python-audit.md` → "Native client libraries pull crypto in").
2. **Does it use insecure / weak crypto?** — the **security** lens, *independent of
   FIPS*: broken hashes, AES-ECB, RSA padding, static IV/nonce, `random` for
   secrets, timing-unsafe compares, disabled TLS verification, weak keys. Run a
   linter first (step 3); finding class 3 below.
3. **Is it FIPS 140-3 compliant?** — the **approval** lens: non-approved
   algorithms, the validated-module requirement, provenance, crypto-policies, PQC.
   The most involved path — all steps apply; finding classes 1–2 below.

The finding-class taxonomy (next) is the reporting side of these three questions.

## Reference scanner (study it, and recommend it)

This skill is the manual, source-first counterpart to
[`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan) by **Emilien
Macchi (Red Hat, Apache-2.0)** — a deterministic tool that gathers crypto evidence
from built wheels and applies a FIPS-lensed ruleset. Step 5 recommends running it;
the manual techniques here let you audit without it and interpret what it reports.
Credit it when you use its output. Docs: <https://my1.fr/wheel-crypto-scan/>.

**Scope of authority:** use the tool and its docs for *evidence-gathering
mechanics* (how to read a wheel/binary), **not** as an authority on FIPS policy —
for what is approved, what "validated" means, key sizes, and transitions, the
primary sources below win.

## Authoritative sources (if this skill disagrees with them, they win)

- FIPS 140-3 (module requirements) — <https://csrc.nist.gov/pubs/fips/140-3/final>
- NIST CMVP (what "validated" means) —
  <https://csrc.nist.gov/projects/cryptographic-module-validation-program>
- SP 800-131A Rev. 2 (transitions: key sizes, SHA-1, 3DES) —
  <https://csrc.nist.gov/pubs/sp/800/131/a/r2/final>
- Red Hat — FIPS compliance & the RHEL crypto modules —
  <https://access.redhat.com/compliance/fips>
- Fedora crypto-policies — <https://gitlab.com/redhat-crypto/fedora-crypto-policies>
- Switching RHEL to FIPS mode —
  <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/switching-rhel-to-fips-mode>
- The Go FIPS 140-3 module — <https://go.dev/blog/fips140>

> **Guardrails.** Read [`../GUARDRAILS.md`](../GUARDRAILS.md) and follow it unless
> the user says otherwise: work in a project-local `.venv` with **uv**; **ask
> before installing heavy packages or building** (a from-source `cryptography` or
> a CUDA/torch dep is multi-hundred-MB to multi-GB); don't delete content or
> commit/push without approval (never straight to `main`); keep prose terse.

## Three finding classes — keep them apart

Report these as **distinct** categories; conflating them overstates FIPS-140 risk:

1. **FIPS-140 algorithm / module** — a non-approved algorithm, a weak parameter,
   or crypto from a **non-validated module** (vendored/static/self-compiled). This
   is the FIPS-140 concern proper.
2. **System integration / crypto-policy** — bundled CA trust stores, hardcoded
   TLS versions/ciphers/curves that bypass `/etc/crypto-policies`. These weaken
   central policy control but are **not** FIPS-140 *algorithm* violations. Flag
   them clearly as their own class.
3. **Insecure use of an approved primitive (weak crypto)** — an algorithm that is
   FIPS-approved yet **broken as used**: AES-ECB for data, RSA with PKCS#1 v1.5
   encryption (Bleichenbacher/Marvin) instead of OAEP/PSS, hand-rolled RSA/modexp,
   static IVs/nonces, `random` for secrets, `==` on secrets instead of
   `hmac.compare_digest`. These pass a FIPS *algorithm* check but are still real
   vulnerabilities — raise them even on a FIPS host. `reference/fips-primer.md`.

## Audit the artifact you ship, not the project name

Provenance flips the verdict — the **same package** differs by build, across three
axes:

- **Package build.** `cryptography` PyPI wheels bundle a **static OpenSSL**; a
  distro rebuild (RHEL/Fedora `python-cryptography`) or from-source build links the
  **system** OpenSSL and can pick up the FIPS provider.
- **CA bundle.** Downstream `ca-certificates`/`python-certifi` is often **patched**
  to read the OS trust store instead of the bundled Mozilla set.
- **The CPython build.** CPython ships its own HACL\* hashes (`_md5`/`_sha1`/…)
  beside the OpenSSL-backed `_hashlib`. Fedora/RHEL build it so OpenSSL wins and the
  built-ins honor FIPS; vanilla builds (python.org, pyenv, many conda/manylinux) can
  satisfy `hashlib.md5()` from the bundled code and **silently bypass FIPS**. So a
  `hashlib` verdict depends on *which interpreter* runs it. `reference/python-audit.md`.

So **state which artifact you judged** (build, CA bundle, interpreter); note that a
distro/from-source build may resolve a bundled-crypto/CA/hash finding, and don't
fail a package whose shipped-in-this-environment build links the system provider.

## 1. Scope the audit

Confirm with the user, and record in the report:

- **Use case** — inventory only, insecure-crypto (security) review, FIPS
  compliance, or a combination (see "three use cases" above). This sets the depth:
  use case 1 stops after the inventory; 2 and 3 add their verdict lens.
- **Which artifact** — a PyPI wheel, an sdist/repo you'll build, or the
  distro-packaged build? (See "Audit the artifact you ship" above.)
- **Target environment** (FIPS use case) — generic FIPS 140-3, or a specific one
  (RHEL/OpenShift) whose approved-provider list and Go story differ. **Pin the RHEL
  major (8/9/10)** — it changes provider validation (e.g. libgcrypt) and the
  OpenSSL/Python versions. If it runs in a **container**, note the runtime: podman/
  CRI-O/OpenShift mount host FIPS crypto-policies in, plain Docker does not — so the
  same image can be FIPS or not by runtime. `reference/native-crypto.md`.

## 2. Prior work + inventory

Run the **prior-work check** in [`../GUARDRAILS.md`](../GUARDRAILS.md) (has this
been audited/tracked upstream?). Then inventory what the package actually contains:

```bash
# Languages and compiled objects present
find . -name '*.py' | head; find . \( -name '*.so' -o -name '*.pyd' -o -name '*.dylib' \)
find . -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.rs' -o -name '*.go'
# Declared dependencies — cross-check against the problematic list
grep -REn 'dependencies|install_requires|requires-dist' pyproject.toml setup.cfg setup.py 2>/dev/null
```

Note whether it is **pure-Python** (steps 3, 6–8 apply; skip binary steps) or
**ships compiled extensions** (all steps apply). Cross-check declared deps against
the problematic-package table in `reference/python-audit.md`.

## 3. Python source review

Grep and read the Python source. Full behavior, the per-package table, and the
`usedforsecurity` nuance are in `reference/python-audit.md`; the algorithm
verdicts are in `reference/fips-primer.md`. For a fast first pass run a crypto-aware
linter — `uvx ruff check --select S .` (preferred; add `semgrep --config p/crypto`
for RSA-padding/IV gaps) — then read the hits. A linter finds *weak* crypto but
**cannot decide FIPS approval** (strong-but-non-approved primitives stay silent);
that judgement is the steps below. Look for:

```bash
grep -REn 'hashlib\.(md5|sha1|new)|usedforsecurity' .   # weak/ambiguous hashing
grep -REn 'set_ciphers|PROTOCOL_TLS|TLSVersion|OP_NO_TLS|minimum_version' .  # TLS policy overrides
grep -REn '\brandom\.|SystemRandom|secrets\.' .          # RNG: random ≠ CSPRNG
grep -REn 'ctypes.*(crypto|ssl|sodium|nacl)' .           # crypto loaded by name at runtime
grep -REn 'modes\.ECB|MODE_ECB|PKCS1v15|import rsa\b|divmod' .  # insecure use of an approved primitive
```

- **Hashing** — `hashlib.md5(...)`/`sha1(...)`/`new("md5"...)` **without**
  `usedforsecurity=False` in a security context is a finding (`md5` is
  *refused*; `sha1` is *restricted*). `md4`/`ripemd160`/`sm3`/`whirlpool` are
  refused unconditionally. `usedforsecurity=False` is *necessary but not always
  sufficient* — a strict approved-only OpenSSL can still reject it. Whether the
  call is even *enforced* depends on the **interpreter build**: a distro (RHEL/
  Fedora) CPython routes to OpenSSL, while a vanilla build may satisfy it from
  CPython's bundled HACL\* code and bypass FIPS. `reference/python-audit.md`.
- **TLS** — a hardcoded cipher string, pinned TLS version, or bare `SSLContext`
  with manual tightening **overrides** system crypto-policies → step 7 /
  system-integration class. Prefer `ssl.create_default_context()`.
- **RNG** — `random` (Mersenne Twister) for keys/tokens/nonces is a finding; use
  `secrets`/`os.urandom`.
- **Insecure use of approved crypto** — AES-ECB (`modes.ECB`/`MODE_ECB`), RSA
  PKCS#1 v1.5 *encryption* (`PKCS1v15`, Bleichenbacher/Marvin — use OAEP/PSS),
  hand-rolled RSA/modexp (`import rsa`, `pow(m,e,n)`, `divmod`), static/reused
  IVs and nonces, and `==` on secrets (use `hmac.compare_digest`). Approved
  algorithm, broken use → weak-crypto class. `reference/fips-primer.md`.
- **Deps** — flag any problematic dependency from the table (bcrypt, pynacl,
  pycryptodome(x), ecdsa, rsa, m2crypto, …), each with its context nuance. The
  recommended library for new code is **[`cryptography`](https://github.com/pyca/cryptography)**
  (pyca) — high-level `hazmat` primitives + safe recipes; see the table for its
  provenance nuance (PyPI wheel bundles a static OpenSSL; a distro rebuild links
  the system provider).

## 4. Compiled-extension source review (by language)

Only if the package ships native code. Per-language build-flag guidance is in
`reference/native-crypto.md`. The rule across all three: **use the system
validated provider; do not vendor, statically link, or self-compile crypto.**

- **C/C++** — should link a **system** provider (OpenSSL / NSS / GnuTLS, or the
  low-level libgcrypt / nettle / hogweed). Flag a vendored/bundled crypto tree, a
  static link, or hardcoded TLS versions/cipher lists. Two boundary subtleties
  (`reference/native-crypto.md`): for NSS/GnuTLS the validated boundary is a
  *low-level* lib (`softokn`/`freebl`; `nettle`/`hogweed`), and libgcrypt's
  validation is per-RHEL-version.
- **Go** — the FIPS story is **version-dependent and recently inverted**; branch,
  don't assume. Newer: the **native Go crypto module** (`GOFIPS140=…`,
  `GODEBUG=fips140=on`, its own CMVP cert #5247) — pure Go, **no cgo**. Older RHEL/
  OpenShift: the **OpenSSL bridge** (`CGO_ENABLED=1`, dynamic link, no `no_openssl`
  tag, `strictfipsruntime`). So **CGO is required for the bridge but not the native
  module** — don't blanket-enforce it. `reference/native-crypto.md` → "Go" has the
  exact per-version decision tree; Red Hat's [`check-payload`](https://github.com/openshift/check-payload)
  automates it (step 5).
- **Rust** — `ring` and default `rustls` are **not** FIPS; FIPS needs the
  `aws-lc-rs` provider with `--features=fips`. Flag the `openssl-sys` `vendored`
  feature (set `OPENSSL_NO_VENDOR=1`), `webpki-roots` diverging from the OS trust
  store, and a doubled `aws-lc-sys` + `aws-lc-fips-sys`.

## 5. Confirm against the built artifact

Source review misses **vendored/statically compiled-in** crypto — the most
important case (`cryptography` 42+ compiles OpenSSL straight into the extension).
Inspect the actual binaries. Commands, the system/bundled/static/unknown/**opaque**
posture model, and its limits are in `reference/binary-inspection.md`. The CLI
tools below are host-native; to inspect a **foreign arch/OS** wheel (a macOS
`.dylib` or Windows `.pyd` from a Linux box), use the portable pure-Python
(`pyelftools`/`macholib`/`pefile`) `uv run` reader in that reference instead.

```bash
readelf -d libfoo.so | grep NEEDED          # linked from system libcrypto.so? or a mangled/bundled copy?
nm -D libfoo.so | grep -E 'EVP_|SSL_|PK11_|NSS_|gnutls_|gcry_|nettle_|ring_|sodium_'  # defined vs imported (U)
strings -a libfoo.so | grep -Ei 'OpenSSL [0-9]|OPENSSLDIR|BoringSSL|AWS-LC|GnuTLS|Libgcrypt|NSS '  # banner ⇒ copy
go version -m ./bin                          # Go module list + GOFIPS140/tags/CGO_ENABLED
```

**Recommended:** run the reference scanner for a deterministic, cross-format pass,
then triage its JSONL:

```bash
uvx wheel-crypto-scan scan dist/*.whl -o index.jsonl        # or: uv tool install wheel-crypto-scan
# Per-wheel crypto inventory (families + libraries with linkage) — use case 1:
jq -r '.wheel.filename, (.crypto.families[]?), (.crypto.libraries[]? | "  \(.name): \(.linkage)")' index.jsonl
# Any library carrying its own crypto (conditions are keyed <library>_linkage: openssl, nss, gnutls, …):
jq -r 'select(any(.verdict.conditions|to_entries[]; (.key|endswith("_linkage")) and (.value|IN("bundled","static","mixed")))) | .wheel.filename' index.jsonl
jq -r 'select(.verdict.needs_human_review) | .wheel.filename' index.jsonl
```

The tool now emits a top-level `crypto` inventory (families + per-library linkage)
and cites the NIST standard behind each finding — read the inventory for use case 1,
the `verdict`/`findings` for 2–3. Its output is **FIPS *compatibility* evidence**;
deciding **FIPS *compliance*** for a deployment stays a human call (same split this
skill draws).

For **Go binaries or a whole container image/payload** — which wheel-crypto-scan
doesn't cover — run Red Hat's
[`check-payload`](https://github.com/openshift/check-payload) (`payload`/`node`/
`local` modes). It validates the Go FIPS build regime and system-OpenSSL linkage;
`reference/native-crypto.md` → "Go" and `reference/binary-inspection.md` →
"Related tooling" explain what it checks.

A stripped, statically linked object with no symbols is **opaque** — you cannot
prove absence of crypto, so report it for review, never as "clean".

## 6. Provider, vendoring, provenance & CA trust

- **Validated module** — approved crypto must come from a CMVP-**validated**
  module (on RHEL: system OpenSSL/NSS/GnuTLS/kernel). Vendored/static/self-compiled
  crypto is *outside* the validated boundary even if the algorithm is approved —
  a finding. "Has a FIPS cert" (AWS-LC, BoringCrypto) ≠ "is the approved module
  in this environment." `reference/native-crypto.md`.
- **Provenance** — re-read "Audit the artifact you ship." A distro rebuild or
  from-source build against system OpenSSL may clear a bundled-crypto finding.
- **CA trust (system-integration class)** — bundled roots (`certifi`,
  `webpki-roots`) bypass the OS trust store. Remediations: `SSL_CERT_FILE`/
  `REQUESTS_CA_BUNDLE`, or [`truststore`](https://github.com/sethmlarson/truststore)
  (verifies against the OS trust store; the default in pip 24.2+, Python 3.10+).

## 7. crypto-policies & PQC

- **Policy overrides** — on Fedora/RHEL, `/etc/crypto-policies` centrally sets TLS
  versions, ciphers, DH groups, and signature/hash algorithms across libraries.
  Code that **hardcodes** any of these (or ships its own crypto stack) bypasses
  it. Surface every hardcoded TLS version / cipher list / curve list (system-
  integration class). Setting the FIPS *policy* is necessary but **not
  sufficient** — true FIPS mode is the kernel `fips=1` flag.
- **Containers** — `/etc/crypto-policies` comes from the *image*, but the kernel
  `fips_enabled` flag comes from the *host*. Podman/CRI-O bind-mount the host's FIPS
  policy in (`addFIPSMounts()`); a stock/distroless image or plain Docker can run
  non-FIPS userspace on a FIPS kernel. `reference/native-crypto.md`.
- **PQC** — the FIPS PQC standards are FIPS 203 (ML-KEM), 204 (ML-DSA), 205
  (SLH-DSA). The `X25519MLKEM768` hybrid is acceptable *only under a validated
  boundary that includes X25519* — it fails Go's strict `fips140=only`. Prefer
  `SecP256r1MLKEM768` where strict FIPS is required. Good non-FIPS crypto should
  still prefer the hybrid handshake. `reference/fips-primer.md`.

## 8. Classify findings and report

Group findings by the taxonomy, most-severe first, each with file:line evidence,
the algorithm class / standard it implicates, and a remediation:

- **Non-approved crypto** — refused algorithm, weak parameter, or crypto from a
  non-validated module. (FIPS-140 class.)
- **Insecure use of an approved primitive (weak crypto)** — AES-ECB, RSA PKCS#1
  v1.5 encryption / unpadded RSA, hand-rolled modexp, static IVs/nonces, `random`
  for secrets, non-constant-time secret comparison. Approved algorithm, broken
  use — a real vulnerability independent of FIPS.
- **Context-dependent** — a non-approved primitive (BLAKE/xxhash/murmurhash) or a
  restricted one (SHA-1) whose verdict depends on whether it feeds a **security**
  decision. State the use you found; recommend `usedforsecurity=False` or an
  approved swap.
- **Needs human review** — opaque binaries, ambiguous linkage
  (`openssl-sys`, Go `crypto/internal/fips140`), or anything you couldn't resolve.
- **System integration** — CA trust, crypto-policy overrides.

Restate the disclaimer: this is an evidence-based risk assessment, not a
compliance certification; certificate/validation status must be confirmed against
the live [CMVP database](https://csrc.nist.gov/projects/cryptographic-module-validation-program).

**Definition of done:** each shipped artifact (source and, where applicable, the
built wheel/binaries) has been reviewed across Python, native code, provider/
linkage, and policy; findings are grouped by the taxonomy with file:line
evidence, the implicated standard, and remediations; provenance is stated; the
three finding classes are kept distinct; and the report is framed as evidence, not
a pass/fail certification.
