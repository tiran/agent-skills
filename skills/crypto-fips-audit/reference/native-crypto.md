# Native crypto: validated providers, vendoring, and per-language rules

Companion to SKILL steps 4 and 6. The *algorithm* verdicts are in
`fips-primer.md`; *how to inspect a binary* is in `binary-inspection.md`. Cited
from the sources in `SKILL.md` plus the vendor pages linked inline.

## What "validated" means (and the three lookalike terms)

- **CMVP** (NIST + Canada) issues a **validation certificate** after an accredited
  lab tests a module against ISO/IEC 19790. Labs can't self-certify.
- **FIPS Validated** — lab-tested, **active CMVP certificate** you can look up.
  Only this carries formal recognition.
- **FIPS Compliant** — an *unverified vendor claim* ("we used approved
  algorithms"). NIST doesn't recognize it; FedRAMP assessors don't accept it.
- **FIPS Capable** — *contains* a validated module but is running non-FIPS. The
  common, hard-to-detect production gap.
- **Algorithm (CAVP) ≠ module (CMVP).** Passing an algorithm test is a
  *prerequisite*, not a substitute for module validation.

**Validation attaches to a specific binary + version + operational environment.**
A rebuild, a different link model, or a different OS/arch steps outside the
boundary. FIPS 140-2 certificates move to the **Historical** list on **2026-09-21**
— treat 140-2-only modules as historical now. **Certificate numbers drift** — always
re-verify against the live
[CMVP database](https://csrc.nist.gov/projects/cryptographic-module-validation-program),
never a cached number.

## Approved providers (RHEL/Fedora)

Red Hat submits system modules to CMVP: **OpenSSL, GnuTLS, libgcrypt, NSS, and the
kernel Crypto API** (nettle counts as part of GnuTLS; `compat-openssl*` is **not**
certified). **The provider set and versions differ by RHEL major — branch on the
target's version:**

| | RHEL 8 | RHEL 9 | RHEL 10 |
|---|---|---|---|
| OpenSSL | 1.1.1 | **3.0.x** | **3.5** (3.2+) |
| libgcrypt | validated | **validated** | **deprecated / no longer validated** |
| System Python | 3.6 (+3.9/3.11 modules) | 3.9 | 3.12 |

So **on RHEL 9 libgcrypt is still an approved provider** — do not flag `gcry_*`
against a system libgcrypt there; only flag it as deprecated when the target is
RHEL 10. On RHEL 10 the guidance is to use the system core crypto and ignore
app-specific FIPS toggles (they already follow system OpenSSL). Certificate numbers
and module names are per-version — re-verify against the live CMVP DB for the exact
RHEL release in scope.

Detection signals (target host): kernel `cat /proc/sys/crypto/fips_enabled` == 1;
`openssl list -providers` shows the `fips` provider; per-library
`EVP_default_properties_is_fips_enabled()` (OpenSSL) / `gcry_fips_mode_active()`
(libgcrypt) / `gnutls_fips140_mode_enabled()` (GnuTLS) / `NSS_GetSystemFIPSEnabled()`
or a `PK11` FIPS token (NSS). OpenSSL 3.x FIPS is a dynamically loaded `fips`
provider (`fips.so`) activated via `openssl.cnf` → `fipsmodule.cnf`, with all
approved algorithms matching the `fips=yes` property query. **NSS's validated
module is the `softokn`/`freebl` pair** (the "NSS Cryptographic Module"), and
**GnuTLS delegates its primitives to `nettle`/`hogweed`** — so with NSS or GnuTLS
the boundary lives in a *low-level* library, not the top-level `libnss3`/
`libgnutls` an app links.

### Containers: the kernel flag comes from the host, the policy from the runtime

Most FIPS audits of a Python package target a **container** (OpenShift/Kubernetes),
so know how a container gets FIPS mode. A container shares the **host kernel**, so
`/proc/sys/crypto/fips_enabled` inside it reflects the *host* — a container on a
FIPS host reads as FIPS at the kernel level. But **userspace crypto-policies**
(`/etc/crypto-policies`) come from the **image**, so a stock image does **not** make
OpenSSL/GnuTLS/NSS enforce FIPS merely by running on a FIPS host. The runtime has to
bridge that gap.

**Podman/CRI-O do** — `addFIPSMounts()` in
[`containers/common`](https://github.com/containers/common/blob/v0.64/pkg/subscriptions/subscriptions.go):
when the host is FIPS (`/proc/sys/crypto/fips_enabled` == `1`) it bind-mounts the
host FIPS policy into the container —
`/usr/share/crypto-policies/back-ends/FIPS` → `/etc/crypto-policies/back-ends`,
`/usr/share/crypto-policies/default-fips-config` (or a temp `FIPS\n` file) →
`/etc/crypto-policies/config`, plus a `system-fips` secret at `/run/secrets` when
`/etc/system-fips` symlinks there. Audit consequences:

- **The runtime decides, not just the image.** Podman/CRI-O/OpenShift wire FIPS in
  on a FIPS host; **plain Docker does not** — its userspace stays non-FIPS even on a
  FIPS kernel. State which runtime the artifact runs under.
- **A FIPS-ready image still needs `crypto-policies` installed** so the mount
  targets exist; a minimal/distroless/from-scratch image can miss them and silently
  run non-FIPS userspace on a FIPS kernel.
- **Bundled/static crypto ignores all of this** — a vendored OpenSSL/BoringSSL/
  libsodium never reads `/etc/crypto-policies`, so the mounts don't reach it. The
  runtime wiring only helps code that goes through the system providers (the reason
  the binary pass in `binary-inspection.md` still matters in a container).

To scan a whole image/payload rather than one binary, [`check-payload`](https://github.com/openshift/check-payload)
(Red Hat/OpenShift) has `payload`/`node`/`local` modes that walk every executable
and apply the Go/OpenSSL-linkage checks above — the container-scale counterpart to
wheel-crypto-scan (see `binary-inspection.md` → "Related tooling").

## Why vendored / self-compiled / embedded crypto fails

A statically linked or vendored crypto library is a **different binary** than the
validated one, so it inherits **no certificate** — even if the algorithm is
approved and the version number matches. This is the core reason to flag static/
vendored OpenSSL, bundled libsodium, vendored BoringSSL, `ring`, etc. Embedding a
validated module lets you claim only that the product *utilizes* it, not that the
product is validated. It also can't honor `/etc/crypto-policies`.

### "Has a FIPS cert" ≠ "is the approved module here"

- **AWS-LC-FIPS** has CMVP certificates (separate ones for static vs. dynamic
  linking — the link model is part of the boundary), but only the **`fips` build**
  qualifies; plain `aws-lc-sys` is not FIPS.
- **BoringSSL/BoringCrypto** is validated for Google's *internal* use; upstream
  tells others not to rely on it.
- RHEL/OpenShift trust **only their own** validated builds — a valid cert elsewhere
  doesn't make a module the approved one in that environment (cf. RHSB-2023-001,
  where OpenShift Go components used Go's own unvalidated crypto).

## Provenance flips the verdict

The same package differs by build. A **distro rebuild** (`python-cryptography` on
RHEL/Fedora) or a **from-source** build links **system** OpenSSL and can pick up
the FIPS provider, whereas the **PyPI binary wheel bundles a static copy**. State
which artifact you judged; note that installing the distro package or building from
source may clear a bundled-crypto finding.

## Per-language rules

### C / C++

Link the **system** OpenSSL / NSS / GnuTLS (or, lower down, libgcrypt / nettle /
hogweed). Flag: a vendored crypto source tree, a static link that pulls crypto into
the extension, an embedded mini-TLS (mbedTLS, wolfSSL, BearSSL) shipped in the
wheel, and hardcoded TLS versions / cipher lists / curve lists (which bypass
crypto-policies — system-integration class). Confirm with `binary-inspection.md`.

- **NSS** — the boundary is `libsoftokn3` + `libfreebl3`; a bundled copy of *those*
  escapes it even if the app links a system `libnss3`. NSS uses its own policy/trust
  DB, so it doesn't inherit `/etc/crypto-policies` the way OpenSSL does.
- **GnuTLS / libgcrypt / nettle** — GnuTLS calls `nettle` (+ `hogweed` for
  public-key); a vendored `nettle`/`hogweed` is a boundary escape just like a
  vendored OpenSSL. libgcrypt's validation is per-RHEL-version (table above).
- **Client libraries pull crypto transitively.** A DB/queue/auth extension that
  links libcurl / libpq / libmysqlclient / FreeTDS / libzmq / libkrb5 /
  librdkafka gets its TLS from *their* crypto, one hop away — a system copy of
  those inherits the system provider, but a wheel that **bundles** them (or a
  static libsodium/BoringSSL inside libzmq/grpc) escapes the boundary. Follow the
  dependency one hop: `readelf -d` the client lib, not just the extension. The
  per-package specifics are in `python-audit.md` → "Native client libraries pull
  crypto in under the hood."

### Go — version-dependent, recently inverted

Two mechanisms; **branch on the target's Go version, don't assume one.** This is
exactly the decision tree [`check-payload`](https://github.com/openshift/check-payload)
(Red Hat/OpenShift's FIPS binary scanner — see below and "Related tooling" in
`binary-inspection.md`) walks in `validateGoNativeFIPS`, and it is the authoritative
reference for it:

- **Native Go FIPS module** — pure Go, **no cgo**; its own CMVP cert (**#5247**,
  module `crypto/fips140` ≥ **v1.0.0**). check-payload enforces the native rules for
  **Go ≥ 1.27** (and **Go 1.26 when activated**). It requires the module be both
  **compiled in** *and* **build-activated**: `DefaultGODEBUG` must contain
  `fips140=auto|on|only` (RH go-toolset injects `fips140=on`; `GOFIPS140=` at build
  time selects the module version). `GOFIPS140` set but *not* activated → it **warns
  and falls back to the legacy checks**. For a native binary it does **not** check
  CGO, static linking, or tags. Verify with `go version -m` (look for a `GOFIPS140`
  setting and a `fips140=` in `DefaultGODEBUG`).
- **Legacy golang-fips OpenSSL bridge** — cgo → dlopen's system OpenSSL. Applies to
  **Go ≤ 1.25** (the native module ships from Go 1.24 as v1.0.0, but check-payload
  doesn't apply the native rules there — it treats these under the bridge regime)
  and **Go 1.26 without fips140
  activated**. Here check-payload **does** enforce, and so should you:
  **`CGO_ENABLED=1`** (never `0`), **dynamically linked** (no `-extldflags
  "-static"`), the **`no_openssl` tag must NOT be set**, and a `strictfipsruntime`
  **tag or `GOEXPERIMENT`** — a fail-closed startup check (warned if missing).
- **So enforce CGO by regime, not blanket** — require CGO/dynamic/no-`no_openssl`
  for a *bridge* build, but **not** for a *native* build (which drops cgo by
  design). Old advice ("must bridge to OpenSSL, must set CGO") is no longer
  universal. Flag stock non-approved algorithms regardless of regime:
  `golang.org/x/crypto/blake2*`, `chacha20poly1305`, X25519 as KEX.

### Rust — providers, vendoring, trust store

- **`ring` and default `rustls` are not FIPS.** rustls decouples protocol from
  provider; FIPS needs the **`aws-lc-rs` provider with `--features=fips`** (pulls
  the validated `aws-lc-fips` module; adds cmake/Go build deps). `ring` has no FIPS
  support.
- **`openssl-sys` `vendored` feature** compiles and statically links a bundled (non-
  validated) OpenSSL — set **`OPENSSL_NO_VENDOR=1`** to force system OpenSSL. Flag
  `vendored`/`vendored-openssl` anywhere in the tree.
- **Doubled sys crates** — a FIPS build can drag in both `aws-lc-sys` and
  `aws-lc-fips-sys` (rustls-webpki feature gap); verify only the FIPS one links.
- **Symbol prefixing** — AWS-LC built with `BORINGSSL_PREFIX` renames symbols (not
  the file); trust the `OPENSSL_IS_AWSLC`/`AWSLC_VERSION` **strings** over symbol
  names.
- **rustls can't inherit `/etc/crypto-policies`** — even a FIPS rustls won't honor
  system policy the way OpenSSL-based apps do.
- **Test-only deps are a false-positive trap.** A crate under
  `[dev-dependencies]` in `Cargo.toml` (or present in `Cargo.lock` only for tests/
  benches) is **not shipped** in the wheel. Before flagging `rustls`/`ring`,
  confirm it's a real `[dependencies]`/`[build-dependencies]` entry **and** that it
  appears in the built artifact (its symbols/strings, or the embedded SBOM — see
  `binary-inspection.md`). Don't flag from `Cargo.lock` alone.

## CA trust store (system-integration class, not FIPS-140 algorithm)

Bundled roots don't break algorithm validation, but they bypass OS trust /
crypto-policy management (a corporate/internal CA added to the system is ignored,
and revocations don't propagate).

- **Python `certifi`** ships Mozilla's roots in a package. RHEL stdlib `ssl` uses
  `/etc/pki/tls/certs/ca-bundle.crt` (from `ca-certificates`); downstream
  `python-certifi` is often **patched** to defer to it.
- **Rust `webpki-roots`** = the same bundled-roots problem; `rustls-native-certs`
  reads the OS store instead.
- **Remediations (Python):** `SSL_CERT_FILE`/`SSL_CERT_DIR` or
  `REQUESTS_CA_BUNDLE` env vars; or [`truststore`](https://github.com/sethmlarson/truststore),
  which verifies against the **OS trust store** through an `ssl.SSLContext` drop-in
  (`truststore.SSLContext`, or `inject_into_ssl()` in an application — not a library).
  It's the default trust mechanism in **pip 24.2+**, adoptable across
  requests/httpx/urllib3, and needs **Python 3.10+**. (RHEL trust is managed via
  `/etc/pki/ca-trust/source/anchors/` + `update-ca-trust`; note containers get their
  own bundle at build time.)
