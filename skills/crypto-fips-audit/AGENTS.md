# AGENTS.md — crypto-fips-audit

Cross-agent entry point for this skill (Codex CLI and any agent that reads
`AGENTS.md`). Claude Code loads `SKILL.md` directly via its frontmatter; both
share the same content and reference files.

## When to use

You are asked to **audit a Python package** — and any C/C++/Go/Rust code it ships
— for its **use of cryptography**: inventory what crypto it uses, find **insecure
or weak cryptography**, and assess **FIPS 140-3 compliance** risk. Covers refused
hashes (MD5/MD4/RIPEMD-160), restricted ones (SHA-1),
non-approved primitives (BLAKE2/3, ChaCha20-Poly1305, 3DES, scrypt/Argon2/bcrypt,
X25519 key agreement), weak RSA/EC key sizes, **vendored or statically linked
crypto** (bundled OpenSSL/BoringSSL/AWS-LC/libsodium) that escapes the system
validated module, hardcoded TLS/cipher/curve settings that bypass
`/etc/crypto-policies`, bundled CA trust stores, and problematic PyPI deps
(bcrypt, pycryptodome, pynacl, ecdsa, rsa, m2crypto, …).

It serves **three use cases** at increasing depth (scope to one in step 1):
(1) **inventory** — does the package use cryptography at all, and what/where;
(2) **insecure crypto** — the security lens, independent of FIPS; (3) **FIPS
140-3 compliance** — the approval lens.

This **gathers evidence and assesses risk; it does not certify compliance** — only
a NIST CMVP validation makes a module *validated*. Report findings as evidence for
a human, never as a pass/fail certification.

## Status

**Experimental** — grounded in the cited NIST/RHEL/Go/Rust/PyPI sources and in the
reference scanner; the step order is a new draft, and crypto policy moves. Verify
every finding against the sources linked in `SKILL.md`.

## How to run it

1. Read **`SKILL.md`** — the ordered workflow (8 steps). Follow it top to bottom.
2. Open a bundled reference only when a step cites it:
   - `reference/fips-primer.md` — what FIPS 140-3 governs; approved vs
     non-approved per algorithm class; key sizes/curves; the counterintuitive
     cases (Ed25519 vs X25519, SHA-1, BLAKE, scrypt/Argon2, ChaCha20-Poly1305);
     `usedforsecurity`; PQC; standards map.
   - `reference/python-audit.md` — stdlib under FIPS (hashlib/ssl/random/hmac) +
     the problematic-PyPI-package table + grep starting points.
   - `reference/native-crypto.md` — validated vs compliant vs capable; RHEL/Fedora
     approved providers; why vendoring breaks the boundary; per-language build
     flags (C/C++, Go, Rust); provenance; CA trust.
   - `reference/binary-inspection.md` — per-format inspection (ELF/Mach-O/PE/Go/
     Rust) via CLI or `pyelftools`/`macholib`/`pefile`; the
     system/bundled/static/unknown/opaque posture model; the all-providers marker
     table (OpenSSL/NSS/GnuTLS/libgcrypt/nettle); embedded SBOM; limitations;
     tooling.
3. Run **`scripts/scan_crypto.py`** (step 5) for a cross-format, cross-arch/OS
   binary pass: `uv run scripts/scan_crypto.py <file>…` — a PEP 723 script that
   reads ELF/Mach-O/PE symbols, dependencies, and banners from any host.

## Related skills

- [`modernize-python-metadata`](../modernize-python-metadata/) — reads the same
  `pyproject.toml` deps this skill audits.
- [`secure-python-release-pipeline`](../secure-python-release-pipeline/) — builds
  the wheels/binaries this skill inspects.

## Definition of done

Each shipped artifact (source and, where applicable, the built wheel/binaries) is
reviewed across Python, native code, provider/linkage, and policy; findings are
grouped by taxonomy (non-approved / insecure-use-of-approved / context-dependent /
needs-human-review / system-integration) with file:line evidence, the implicated
standard, and remediations; the audited artifact and its provenance are stated;
the finding classes are kept distinct; the report is framed as evidence, not
certification.
