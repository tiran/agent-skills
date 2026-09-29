# Trust store & bundled CA bundles — which regime actually governs it

A **bundled CA trust store** — Python `certifi`, Rust `webpki-roots`, or a `*.pem`/
`ca-bundle.crt` shipped inside a wheel/binary — is a recurring finding that is
routinely **misfiled**. This lens says *which* compliance regime governs it, how to
flag it, and how to remediate. Backs SKILL step 6 (CA trust) and the `certifi`/
`webpki-roots` entries in `python-audit.md` / `native-crypto.md`.

**One-liner:** it is **not** a FIPS-140 issue and **not** a crypto-policies issue —
it's a **trust-management / system-integration** problem, governed by **distro
packaging policy** and, in government/defense contexts, by **STIG (DISA)** and
**Common Criteria (NIAP)**.

## What a trust store is (and isn't)

**Trust anchors** are the set of CA root certs an app trusts to validate peer
certificates during RFC 5280 path validation. That is certificate **data + trust
flags — not cryptographic code.** "Bundling your own" means shipping `certifi`/
`webpki-roots`/a PEM instead of using the OS-managed store. The distinction matters
because it puts the problem in the *trust-management* bucket, not the crypto-module
or algorithm-policy buckets below.

## Which regime governs it — the four-axis map

| Regime | Governs the trust store? | Mechanism / why |
| --- | --- | --- |
| **FIPS 140-3** | **No** | Validates the *crypto module* boundary. Loading trust anchors and RFC 5280 path validation are **application-level, outside the module**; the cert-signature *verification* still runs in the validated module regardless of which anchors you use. Bundled roots move no crypto op out of the module. ([NIST CMVP IG](https://csrc.nist.gov/csrc/media/Projects/cryptographic-module-validation-program/documents/fips%20140-3/FIPS%20140-3%20IG.pdf)) |
| **RHEL crypto-policies** | **No** | Governs **algorithms, protocol versions, key sizes, cipher suites** — *how* you negotiate crypto, not *whom* you trust. The trust store is a **separate subsystem** (`ca-certificates` / `update-ca-trust` / p11-kit). Crypto-policies can reject a cert for a weak algorithm/key, never for *which CA* issued it. ([RHEL crypto-policies](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/security_hardening/using-the-system-wide-cryptographic-policies_security-hardening), [shared system certificates](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/using-shared-system-certificates_securing-networks)) |
| **Distro packaging policy** | **Yes** (Fedora/RHEL strong; Debian softer; not universal) | Fedora: only `ca-certificates` ships roots; other packages **must not** inject into the global trust store, and apps should consume the **shared system store**. Enforced via package review + **downstream-patching** `certifi`/`requests`. Debian ships `ca-certificates` and pushes the same intent (bug #781610) but doesn't fully patch `certifi`; Alpine/Nix/Guix mostly don't. ([Fedora Shared System Certificates](https://fedoraproject.org/wiki/Features/SharedSystemCertificates), [Debian #781610](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=781610)) |
| **STIG (DISA)** | **Yes, in effect** (DoD systems) | Not phrased as "use the OS store" but as **"trust only DoD-approved CAs"**: DoD Root CAs must be installed in the trust store, and app trust stores must contain **only** DoD-approved CAs (else a finding). Controls: **CCI-000185** (validate the path to an accepted trust anchor incl. revocation) and **CCI-002470** (only organization-approved CAs). A bundled Mozilla set has no DoD roots, isn't the managed store, and isn't updated → a finding. ([Tomcat STIG V-222994](https://www.stigviewer.com/stigs/apache_tomcat_application_server_9/2025-02-11/finding/V-222994), [SV-225441](https://www.stigqter.com/stigs/SV-225441r569248_rule.html)) |
| **Common Criteria (NIAP)** | **Steered, not blanket** | The **Application Software PP** steers apps to **platform-provided** credential/cert storage (**FCS_STO_EXT.1**), and the **X.509 Functional Package** requires full path validation, **revocation**, and reference-identifier checks (**FIA_X509_EXT.1/.2**). A self-managed store is permitted only if it meets those (updatable, revocation-aware) — a static bundled set is disfavored. Depends on the claimed PP/selections. ([NIAP App PP](https://www.niap-ccevs.org/static_html/protection-profile/462/462/index.html), [X.509 Functional Package](https://www.niap-ccevs.org/static_html/protection-profile/511/Functional%20Package%20for%20X.509_v1.0.html)) |

The through-line: every regime wants **centrally-managed, updatable, org-controlled
trust with proper validation/revocation.** A static bundled store violates that
*intent* everywhere; only the distro packaging policies and STIG come close to a hard
"must," and both apply only within their scope (distro build / DoD deployment / CC
evaluation).

## Two failure directions (why it matters at all)

- **Over-trust (the dangerous one):** a bundled store keeps trusting a CA that the OS
  / Mozilla has since **distrusted or removed** — revocations and blocklist entries
  don't propagate, so the app trusts a compromised/withdrawn CA long after the system
  stopped.
- **Bypass / under-trust:** an org's internal/enterprise CA (or the DoD roots) added
  via `update-ca-trust` is **ignored**, so internal TLS breaks — often "fixed" with
  `verify=False`, converting a trust bug into a **weak-crypto** finding (class 3).
- **Un-updatable:** no channel for CRL/blocklist/root-program updates.

## Don't conflate bundled *roots* with bundled *crypto*

- `certifi` / `webpki-roots` / a shipped PEM = **trust anchors only** → this lens
  (system-integration / trust class).
- A bundled crypto **library** (static OpenSSL / `aws-lc` / rustls+`ring`) = a
  **FIPS-140 module** finding → `native-crypto.md` (non-validated module class).
- A package can carry **both** independently — e.g. `qh3` bundles `aws-lc` (FIPS
  issue) and could also pull `webpki-roots` (trust issue). Report them separately.

## What to flag

- **Python:** `certifi` (Mozilla bundle); `requests`/`httpx`/`urllib3` resolving trust
  through bundled `certifi`; a hardcoded `cafile=`/`REQUESTS_CA_BUNDLE` pointing at a
  shipped PEM; `pip`'s vendored `certifi`.
- **Rust:** the `webpki-roots` crate; absence of `rustls-native-certs` / a
  platform-verifier that reads the OS store.
- **Any artifact** shipping a `*.pem` / `ca-bundle.crt` / `cacert.pem` root bundle.

```bash
grep -REn 'certifi|webpki-roots|cacert\.pem|ca-bundle\.crt' .
grep -REn 'REQUESTS_CA_BUNDLE|CURL_CA_BUNDLE|cafile\s*=|SSL_CERT_FILE' .
grep -REn 'rustls-native-certs|webpki[_-]roots|truststore' .   # remediations present?
```

## Provenance flips it — audit the artifact, not the package name

RHEL/Fedora **downstream `python-certifi` is patched** to defer to the system store,
which resolves the finding *for that build*; Debian/Alpine/PyPI-wheel builds usually
are **not**. So state **which build** you judged, and don't flag a distro-patched
`certifi` the way you'd flag an upstream PyPI wheel. (See "Audit the artifact you
ship" in SKILL.)

## Remediation

- **Python:** use the OS store — `SSL_CERT_FILE`/`SSL_CERT_DIR`, or
  [`truststore`](https://github.com/sethmlarson/truststore) (validates against the OS
  store; default in pip 24.2+, needs 3.10+), or `certifi-system-store`. On RHEL, rely
  on the distro-patched `certifi`.
- **Rust:** `rustls-native-certs` (reads the OS store) or the platform verifier,
  instead of `webpki-roots`.
- **STIG:** install the DoD roots via `update-ca-trust` and trust **only**
  DoD-approved CAs. **CC:** use the platform keystore (FCS_STO_EXT.1) and ensure
  path validation + revocation (FIA_X509).

## Classify & report

- **Class:** system-integration / trust-management (SKILL step 8, class 2) — **not**
  FIPS-140 (class 1) and **not** weak-crypto (class 3, unless it degenerates into
  `verify=False`).
- **Severity by regime:** distro-hygiene (low) < STIG/CC compliance finding (in those
  regimes) < **over-trust of a distrusted CA** (a real security regression).
- **State** the applicable regime(s) and the artifact/build judged. This is evidence,
  not a certification.
