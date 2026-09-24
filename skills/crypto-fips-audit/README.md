# Skill: audit a Python package's cryptography (weak crypto and FIPS 140-3)

Audit a Python package — and any **C/C++/Go/Rust** code it ships — for its **use
of cryptography**: what it uses, whether that use is **insecure or weak**, and its
**FIPS 140-3 compliance** risk. Covers
refused hashes (MD5/MD4/RIPEMD-160), restricted ones (SHA-1), non-approved
primitives (BLAKE2/3, ChaCha20-Poly1305, 3DES, scrypt/Argon2/bcrypt, X25519 key
agreement, secp256k1), weak RSA/EC key sizes, **vendored or statically linked
crypto** that escapes the system validated module, hardcoded TLS/cipher/curve
settings that bypass `/etc/crypto-policies`, bundled CA trust stores, and
problematic PyPI deps (bcrypt, pycryptodome, pynacl, ecdsa, rsa, m2crypto, …).
Source-first, then confirmed against the built wheel/binaries.

**Three use cases** at increasing depth (scope to one): (1) inventory — *does it
use crypto at all*, and what/where; (2) insecure/weak crypto — the security lens,
independent of FIPS; (3) FIPS 140-3 compliance — the approval lens.

**This gathers evidence and assesses risk — it does not certify compliance.** Only
a NIST CMVP validation makes a cryptographic module *validated*. Report findings as
evidence for a human, never as a pass/fail certification.

**"Non-approved" is an allowlist status, not "insecure."** FIPS blocks two very
different things: genuinely weak crypto (MD5, SHA-1 signatures, DES, AES-ECB) *and*
modern, well-regarded crypto that NIST simply hasn't approved (Curve25519/X25519,
ChaCha20-Poly1305, BLAKE2/3, libsodium). An algorithm is approved only if NIST has
standardized it *and* it runs in a validated module — so strong crypto can be
"non-approved" for process reasons, not weakness (and, per Dual_EC_DRBG, an
approved algorithm can still be broken). Keep *strong-but-unapproved* findings
separate from *actually-broken* ones. The full "why" (incl. sodium/curves/BLAKE) is
in [`reference/fips-primer.md`](reference/fips-primer.md); it is **current as of
September 2026** and should be re-verified against the NIST sources over time.

**Status: Experimental** — grounded in the cited NIST/RHEL/Go/Rust/PyPI sources
and in the reference scanner below; the step order is a new draft, and crypto
policy moves. Verify every finding against the sources linked in `SKILL.md`.

## Layout

| File | Role |
| --- | --- |
| `SKILL.md` | The workflow — 8 ordered steps + frontmatter. **Source of truth.** |
| `AGENTS.md` | Cross-agent entry point (Codex and other `AGENTS.md`-aware agents). |
| `reference/fips-primer.md` | What FIPS 140-3 governs; approved vs non-approved per class; key sizes/curves; counterintuitive cases; `usedforsecurity`; PQC; standards map. |
| `reference/python-audit.md` | Stdlib under FIPS + the problematic-PyPI-package table + grep starting points. |
| `reference/native-crypto.md` | Validated vs compliant vs capable; approved providers; why vendoring breaks the boundary; per-language build flags; provenance; CA trust. |
| `reference/binary-inspection.md` | Per-format binary inspection (CLI + pyelftools/macholib/pefile); posture model; embedded SBOM; limitations; tooling. |
| `scripts/scan_crypto.py` | Cross-format (ELF/Mach-O/PE) crypto evidence reader — `uv run` [PEP 723](https://peps.python.org/pep-0723/) script; reads any arch/OS from one host. |

## Related

- [`modernize-python-metadata`](../modernize-python-metadata/) — reads the same
  `pyproject.toml` dependencies this skill audits.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — builds
  the wheels/binaries this skill inspects.

## Further reading

Sources and tools this skill draws on (crypto policy moves — verify against the
primary NIST/vendor pages before relying on a verdict):

- **NIST** — [FIPS 140-3](https://csrc.nist.gov/pubs/fips/140-3/final),
  [CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program),
  [SP 800-131A Rev. 2](https://csrc.nist.gov/pubs/sp/800/131/a/r2/final). The
  authorities on what "validated" means and which algorithms/key sizes are
  approved.
- **Red Hat / Fedora** — [FIPS compliance](https://access.redhat.com/compliance/fips),
  [crypto-policies](https://gitlab.com/redhat-crypto/fedora-crypto-policies),
  [switching RHEL to FIPS mode](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/switching-rhel-to-fips-mode).
- **Go** — [The FIPS 140-3 Go module](https://go.dev/blog/fips140).
- **Crypto-usage guidance** (the *secure-use* side, beyond FIPS approval) —
  [OpenSSF Secure Coding Guide for Python](https://best.openssf.org/Secure-Coding-Guide-for-Python/),
  the OWASP [Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
  and [Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)
  cheat sheets, and the CPython [`hashlib`](https://docs.python.org/3/library/hashlib.html)/[`ssl`](https://docs.python.org/3/library/ssl.html)/[`hmac`](https://docs.python.org/3/library/hmac.html)/[`secrets`](https://docs.python.org/3/library/secrets.html)
  docs. Relevant CWEs: 327/328 (broken/weak hash), 326 (weak key), 330/338 (weak
  RNG), 780 (RSA no OAEP), 295 (cert validation).
- **Source scanners** — [`ruff`](https://docs.astral.sh/ruff/rules/#flake8-bandit-s)
  (preferred crypto/TLS lint: `uvx ruff check --select S`),
  [`bandit`](https://bandit.readthedocs.io), and
  [`semgrep`](https://semgrep.dev/p/crypto) (RSA-padding/IV gaps ruff misses).
- [`wheel-crypto-scan`](https://github.com/EmilienM/wheel-crypto-scan) by **Emilien
  Macchi (Red Hat, Apache-2.0)** — a deterministic scanner that gathers crypto
  evidence from built wheels; the reference tool this skill's binary-inspection
  step recommends. Docs: <https://my1.fr/wheel-crypto-scan/>. Use it for the
  *mechanics* of reading a wheel; for FIPS interpretation the NIST/RHEL sources
  above govern.
- [`check-payload`](https://github.com/openshift/check-payload) by **Red Hat /
  OpenShift (Apache-2.0)** — the Go-and-container counterpart to wheel-crypto-scan:
  scans a container payload, node, or local binary and validates the FIPS build
  regime (native Go FIPS module vs. golang-fips OpenSSL bridge, dynamic linking to
  system OpenSSL). Built for RHSB-2023-001; its `validateGo*` chain is this skill's
  authority for the Go decision tree in `native-crypto.md`.
- [`truststore`](https://github.com/sethmlarson/truststore) — verifies against the
  OS trust store via an `ssl.SSLContext` drop-in (the default in pip 24.2+, Python
  3.10+); the remedy for a bundled-CA finding.

See the repository [`README.md`](../../README.md) for per-agent setup.
