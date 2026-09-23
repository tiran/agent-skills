# Python source audit: stdlib behavior and the package list

Companion to SKILL step 3. Algorithm verdicts are in `fips-primer.md`; native
linkage (for compiled deps like `cryptography`) is in `binary-inspection.md` /
`native-crypto.md`. Cited from CPython docs, PyPI project pages, and the CPython
FIPS issues linked inline.

## Standard library under FIPS

### hashlib

- **`usedforsecurity=`** (3.9+, keyword-only, default `True`) on every
  constructor. `False` = "not a security use," which is what lets a checksum/dedup
  call survive on a FIPS host. Necessary but **not always sufficient** (a strict
  approved-only OpenSSL can still reject it — cpython#128071).
- **CPython ships its own hash code — the interpreter build decides whether FIPS
  is enforced.** `hashlib` has two backends: `_hashlib` (wraps OpenSSL's EVP API;
  in FIPS mode non-approved digests raise `ValueError: ... disabled for FIPS` /
  `UnsupportedDigestmodError`) **and** the bundled built-ins `_md5`/`_sha1`/`_sha3`/
  `_blake2` (HACL\*), which are self-contained and answer to no OpenSSL policy.
- **Provenance flips this (audit the interpreter, not just the code).** Upstream
  vanilla CPython (python.org, pyenv, most conda/manylinux builds) keeps the
  built-ins, so they historically **bypassed** FIPS — `hashlib.new("md5")` succeeded
  while `hashlib.md5()` failed (cpython#116800). **Fedora/RHEL build CPython so the
  OpenSSL variants win and the built-ins honor FIPS**: downstream patches route
  hashlib through OpenSSL and make the built-ins refuse in FIPS mode unless
  `usedforsecurity=False`, and the distro can drop the built-in modules entirely
  (`configure --with-builtin-hashlib-hashes=`), so a bare constructor raises "code
  for hash md5 was not found." Upstream later adopted the refuse-in-FIPS behaviour
  (cpython PR #127301), but you cannot assume it — **which `python` runs the code
  determines the outcome.**
- **Audit:** flag `hashlib.md5(`/`sha1(`/`new("md5"`/`new("sha1"` without
  `usedforsecurity=False`; flag `md4`/`ripemd160`/`sm3`/`whirlpool`
  unconditionally. State the **interpreter build** assumed: on a distro (RHEL/
  Fedora) CPython the call is enforced/routed to OpenSSL, whereas an upstream or
  self-built interpreter may satisfy it from the bundled HACL\* code and silently
  bypass FIPS.

### ssl

- Follows OpenSSL, which on RHEL/Fedora is wired to `/etc/crypto-policies`.
  **`ssl.create_default_context()` is the compliant path** (inherits system
  policy). Flag as policy overrides (system-integration class, SKILL step 7):
  `ctx.set_ciphers("…")`, pinning `minimum_version`/`maximum_version` to a fixed
  `TLSVersion`, deprecated `OP_NO_TLS*` / `PROTOCOL_TLSv1_2`, or a bare
  `SSLContext(...)` with manual cipher/version tightening.
- **Disabled certificate validation is a *weak-crypto* finding, not a policy one**
  (CWE-295): `verify=False` (`requests`/`httpx`), `ssl.CERT_NONE`,
  `check_hostname=False`, `ssl._create_unverified_context()` /
  `ssl._create_default_https_context = ssl._create_unverified_context`, or paramiko
  `set_missing_host_key_policy(AutoAddPolicy())`. Also flag insecure protocol
  versions — `PROTOCOL_SSLv2`/`SSLv3`/`SSLv23`/`TLSv1`/`TLSv1_1` and
  `ssl.wrap_socket(...)` (no version). (Bandit B501-B504/B507.)

### Higher-level TLS/SSH libraries can bypass the stdlib defaults

A plain HTTPS call is **not** a crypto finding: `requests.get("https://…")` with
defaults inherits the safe stdlib/OpenSSL settings, and the crypto lives in that
library, not the caller. Flag only when the package **modifies** crypto behaviour.
The stdlib `ssl` defaults are safe, but libraries layered on top often **build or
replace the `SSLContext`** with their own settings, and several **don't inherit
`/etc/crypto-policies`**. Audit those overrides, not the mere use:

- **HTTP clients** — `requests`, `urllib3`, `httpx`, `aiohttp`, `pycurl`, and
  friends each let a caller pass a custom `ssl_context`/`SSLContext` or disable
  verification. Flag `verify=False` (`requests`/`httpx`), `urllib3`
  `cert_reqs='CERT_NONE'` / `assert_hostname=False` / `InsecureRequestWarning`
  suppression, `aiohttp` `ssl=False` / `TCPConnector(ssl=...)` /
  `verify_ssl=False`, and any hand-built context that sets `check_hostname=False`
  or `CERT_NONE` or pins ciphers/versions. Prefer `ssl.create_default_context()`
  and leave policy to the system. (CWE-295; also Bandit **B501**.)
- **paramiko (SSH)** is **not** a validated module and does **not** consult
  `/etc/crypto-policies` (it drives `cryptography` directly, not the system SSH
  stack). By default it offers **curve25519-sha256** (X25519 KEX — not
  FIPS-approved) and **chacha20-poly1305@openssh.com** (not approved). Constrain
  with `disabled_algorithms={"kex": ["curve25519-sha256",
  "curve25519-sha256@libssh.org"], "ciphers": ["chacha20-poly1305@openssh.com"]}`,
  or prefer system OpenSSH (which honours crypto-policies). Also flag
  `set_missing_host_key_policy(AutoAddPolicy())` — no host-key verification
  (CWE-295; Bandit **B507**). FIPS approval still hinges on the underlying
  `cryptography`/OpenSSL build being validated.

### Native client libraries pull crypto in under the hood

Many DB drivers, message-queue clients, and auth bindings link a native library
that itself does TLS or auth crypto (libcurl, libpq, libmysqlclient/libmariadb,
FreeTDS, libzmq, libkrb5/GSSAPI, librdkafka, …). The **same rule as HTTP clients
applies**: a plain connection with default settings is **not** the package's
crypto — the crypto lives in that native lib and, on a well-built system, the
**system** OpenSSL/GnuTLS/NSS it dynamically links. Flag one of three things
instead:

1. **A bundled/statically linked copy** — a binary wheel that ships its own
   libcurl/libpq/OpenSSL/BoringSSL/wolfSSL/libsodium escapes the validated
   module (confirm with `binary-inspection.md`; the `openssl_linkage` posture).
2. **Config that overrides crypto/TLS** — the package hardcodes a cipher list,
   pins a TLS version, sets `sslmode`/`sslrootcert`/`ssl_ca`, disables peer
   verification, or selects a Kerberos enctype/GSSAPI mechanism (system-
   integration or weak-crypto class per what it sets).
3. **Inherently non-approved crypto** — a couple carry primitives no config can
   make FIPS-approvable (below).

| Python package | Native lib | Crypto it carries | Audit note |
|---|---|---|---|
| **pycurl** | libcurl | OpenSSL/GnuTLS/NSS/Schannel (build-dependent) TLS | System libcurl → inherits system provider; a bundled libcurl in the wheel is the finding. `CURLOPT_SSL_*`/`CAINFO`/cipher overrides = config class. |
| **psycopg2 / psycopg[c] / psycopg[binary]** | libpq | OpenSSL TLS; SCRAM-SHA-256 auth (approved), legacy `md5` password auth (not FIPS) | `psycopg[binary]` **bundles libpq+OpenSSL**; distro/`psycopg[c]` link system. Flag `sslmode=`/`sslrootcert` overrides; note md5-auth. |
| **asyncpg** | (its own libpq-free proto) | TLS via Python `ssl` | Uses stdlib `ssl` — the `ssl` rules above apply, not a separate native copy. |
| **mysqlclient** | libmysqlclient / libmariadb | OpenSSL (MariaDB C/C can also use **GnuTLS**/Schannel/**wolfSSL**) | wolfSSL is a bundled mini-TLS → boundary escape. Check linkage; flag `ssl_*`/cipher config. |
| **mysql-connector-python** | pure or C-ext | TLS via Python `ssl` (pure) or libmysql (C) | Pure path = stdlib `ssl`. Prefer it on FIPS hosts. |
| **pyodbc / pymssql** | unixODBC+driver / FreeTDS | FreeTDS → OpenSSL/GnuTLS; MS ODBC driver **bundles its own TLS** | MS driver = bundled crypto. FreeTDS usually system. |
| **pyzmq** | libzmq (+ libsodium) | **CurveZMQ = Curve25519/X25519 + Salsa20/Poly1305 via libsodium — NOT approved** | Wheels **bundle libzmq + libsodium** (e.g. `pyzmq.libs/libsodium-*.so`). CURVE security is non-approved regardless of linkage. |
| **redis-py** | pure (opt. hiredis parser) | TLS via Python `ssl`; hiredis does **no** crypto | Mostly a stdlib-`ssl` case; `ssl_*` kwargs = config class. |
| **grpcio** | vendored gRPC C-core | **statically linked BoringSSL** | Always bundled — host FIPS provider bypassed unless rebuilt against OpenSSL. Strong finding. |
| **confluent-kafka** | librdkafka | OpenSSL TLS + SASL/GSSAPI | librdkafka **dynamically links system OpenSSL** by default (good); a vendored/static build or `ssl.cipher.suites` config is the finding. |
| **gssapi / pykerberos / requests-kerberos / kerberos / winkerberos** | MIT krb5 / Heimdal (libgssapi/libkrb5) | Kerberos enctypes: AES approved; **RC4-HMAC (arcfour) and single-DES / MD5 enctypes not approved** | krb5 has its own FIPS mode; flag configs/keytabs allowing RC4/DES enctypes. GSSAPI mechanism selection = config class. |
| **python-ldap** | libldap + libsasl (+ GSSAPI) | OpenSSL/GnuTLS TLS; SASL → GSSAPI/Kerberos | System libldap → system provider; flag `OPT_X_TLS_*` cipher/version overrides. `ldap3` is pure and uses stdlib `ssl`. |

Not every one is a finding — most reduce to "links system OpenSSL, uses defaults"
→ inherits the host provider, nothing to raise. The three that carry
**inherently non-approved** crypto are the ones to always call out on a FIPS host:
**pyzmq CURVE** (libsodium/X25519), **grpcio** (bundled BoringSSL), and
**Kerberos** when RC4-HMAC/DES/MD5 enctypes are permitted. See
`native-crypto.md` for why a bundled copy escapes the boundary and
`binary-inspection.md` for confirming the linkage.

### random vs secrets, hmac

- **`random`** is Mersenne Twister — **not** a CSPRNG/DRBG (its state is
  recoverable from output). Flag `random.*` used for keys/tokens/nonces/salts/
  passwords/session IDs; recommend `secrets` / `os.urandom` / `random.SystemRandom`.
  `secrets` and `os.urandom` are the good path. Non-security use (sampling,
  jitter, test data) is fine — decide by *use*.
- **`hmac`** uses the same OpenSSL backend; HMAC is approved (FIPS 198-1), so
  HMAC-SHA-1 rides SHA-1's *restricted* status, HMAC-MD5 rides MD5's refusal.

### Insecure use of otherwise-approved crypto (weak crypto, independent of FIPS)

Raise these even on a FIPS host — an approved primitive can be broken *as used*
(see `fips-primer.md` → "Approved ≠ used securely"). Report as the weak-crypto
class (SKILL step 8), not as FIPS-140 violations.

- **AES-ECB.** Flag `modes.ECB(` (`cryptography`), `AES.new(key, AES.MODE_ECB)`
  (pycryptodome), or any `MODE_ECB` for confidentiality — it leaks plaintext
  structure. Want AES-GCM (AEAD), or CBC/CTR with a random IV.
- **RSA padding.** Encryption must use **OAEP**, signatures **PSS**. Flag
  `padding.PKCS1v15()` used for `encrypt`/`decrypt` (Bleichenbacher / Marvin timing
  oracle) and any unpadded/"textbook" RSA. `cryptography`'s `OAEP`/`PSS` are the
  good path; v1.5 *signatures* are legacy-tolerated.
- **Hand-rolled crypto.** A pure-Python RSA (`pow(m, e, n)`, `divmod`-based modexp,
  a bespoke `encrypt`/`sign`) is not constant-time and skips padding/RNG/parameter
  checks; **blinding narrows but doesn't close the side channel**. Flag such code
  and the pure-Python `rsa`/`ecdsa` packages (table below); use a vetted library
  over a validated module.
- **Static/reused IVs and nonces.** A hardcoded IV, a zero nonce, or a counter that
  resets is catastrophic for CTR/GCM (nonce reuse breaks GCM entirely). Flag
  literal `iv=b"..."` / `nonce=` constants near cipher construction.
- **Non-constant-time secret comparison.** Comparing a MAC, token, or password
  hash with `==`/`!=` leaks length and content through timing. Use
  `hmac.compare_digest(a, b)` (or `secrets.compare_digest`).

## Problematic PyPI packages

Verdict legend (align with SKILL step 8): **NON-APPROVED** = implements/bundles
crypto no validated module provides; **CONDITIONAL** = OK only if it links the
system OpenSSL/FIPS provider (check the artifact — `binary-inspection.md`);
**CONTEXT** = only a problem in a security context.

| Package | Provides | Implementation | Bundles crypto? | Verdict | Notes |
|---|---|---|---|---|---|
| **bcrypt** | bcrypt password hash | **Rust** (≥4.0; C before) | Yes | NON-APPROVED | bcrypt not approvable under any config |
| **blake3** | BLAKE3 | Rust (PyO3) | Yes | CONTEXT | Not approved; usually checksums/content-addressing |
| **cryptography** | full crypto + X.509/TLS | Rust glue + **OpenSSL** | **wheels: static OpenSSL; source/distro: system** | CONDITIONAL | The pivotal case — check `openssl_linkage`; a distro rebuild flips it |
| **ecdsa** | ECDSA/EdDSA | **pure Python** | n/a | NON-APPROVED | Algorithm approvable, but unvalidated impl outside any module; upstream warns no side-channel protection |
| **libnacl** | NaCl/libsodium primitives | **ctypes** to libsodium | loads system libsodium by name | NON-APPROVED | Invisible to a DT_NEEDED graph (ctypes) |
| **pycryptodome** | self-contained crypto | Python + **C** | Yes (self-contained) | NON-APPROVED | Not an OpenSSL wrapper; `Crypto.*` |
| **pycryptodomex** | same as above | same | Yes | NON-APPROVED | `Cryptodome.*` namespace |
| **pynacl** | libsodium primitives | CFFI over libsodium | **bundles libsodium** (`SODIUM_INSTALL=system` to override) | NON-APPROVED | Bundled → outside any validated module |
| **pyOpenSSL** | TLS/X.509 wrapper | wraps **`cryptography`** | inherits cryptography's OpenSSL | CONDITIONAL | Posture = whatever `cryptography` build is installed |
| **m2crypto** | crypto + SSL | **SWIG over OpenSSL** | usually system OpenSSL | CONDITIONAL | Maintenance mode; verify the linked binary |
| **murmurhash** | MurmurHash2 (non-crypto) | Cython | Yes | CONTEXT | ML feature hashing; almost never security |
| **rsa** | RSA | **pure Python** | n/a | NON-APPROVED | Unvalidated + outside provider; project archived; timing-attack caveats |
| **xxhash** | xxHash (non-crypto) | C (bundled; system via `XXHASH_LINK_SO`) | Yes | CONTEXT | Upstream: not cryptographic; do not use for HMAC |
| **mmh3** | MurmurHash3 (non-crypto) | C/C++ | Yes | CONTEXT | Same class as murmurhash/xxhash |
| **certifi** | CA trust bundle | Mozilla roots in a package | n/a | SYSTEM-INTEGRATION | Bypasses OS trust store; see `native-crypto.md` |

### The good / system-backed choices

**[`cryptography`](https://github.com/pyca/cryptography) (pyca) is the recommended
library for crypto in Python** — the default choice for new code, and the swap to
recommend when you flag a hand-rolled or unmaintained alternative (`rsa`, `ecdsa`,
`pycryptodome`, `m2crypto`). It exposes vetted high-level recipes plus `hazmat`
primitives and delegates to OpenSSL rather than reimplementing crypto.

`cryptography` built **from source or distro-packaged** against system OpenSSL,
plus `pyOpenSSL`/`M2Crypto` on top of it, can pick up the system FIPS provider and
crypto-policies. The caveat that flips this from good to bad is **bundled/static
OpenSSL** — exactly what `cryptography`'s default PyPI wheels ship. So it is the
right library *and* still needs a per-artifact linkage check: **verify linkage per
artifact; don't judge by package name.**

### The non-crypto hashes (CONTEXT only)

`xxhash`, `murmurhash`, `mmh3`, `blake3`, and BLAKE2 libraries are not approved but
are overwhelmingly checksums, dedup, hash tables, ML feature hashing, and content
addressing. **Presence alone is not a finding** — decide by *use*: only flag when
the value feeds a security decision (integrity of a signed artifact, token/nonce
derivation, password handling).

## Grep starting points

```bash
grep -REn 'hashlib\.(md5|sha1|md4|new)|usedforsecurity' .
grep -REn 'import (Crypto|Cryptodome|nacl|libnacl)|from (Crypto|Cryptodome|nacl)' .
grep -REn 'set_ciphers|PROTOCOL_TLS|TLSVersion|OP_NO_(SSL|TLS)|minimum_version|maximum_version' .
grep -REn '\brandom\.(random|randint|choice|getrandbits|shuffle)' .   # then check if security-relevant
grep -REn 'ctypes.*(CDLL|find_library).*(crypto|ssl|sodium|nacl|gcrypt)' .
# Native client libs that pull crypto in under the hood — check linkage + config, not mere use:
grep -REn 'import (pycurl|psycopg2|psycopg|MySQLdb|pymssql|pyodbc|zmq|grpc|gssapi|kerberos|ldap)\b' .
grep -REn 'sslmode|sslrootcert|ssl_ca|CURLOPT_SSL|set_ciphers|CURVE_|enctype|ssl\.cipher' .  # config overrides in those libs
grep -REn 'certifi|webpki|rustls-native-certs' .
# Insecure use of an approved primitive (weak crypto — independent of FIPS):
grep -REn 'modes\.ECB|MODE_ECB' .                        # AES-ECB leaks structure
grep -REn 'PKCS1v15|PKCS1_v1_5' .                        # RSA v1.5 encryption = Bleichenbacher/Marvin; want OAEP/PSS
grep -REn '^\s*import rsa\b|from rsa\b|\bpow\([^,]+,[^,]+,[^)]+\)|divmod' .  # hand-rolled RSA / modexp, not constant-time
grep -REn "\b(iv|nonce)\s*=\s*(b?['\"]|bytes\(|\\\\x00)" .  # static/hardcoded IV or nonce
grep -REn 'key_size\s*=\s*(512|768|1024)' .              # weak RSA/DSA key (SP 800-131A floor: 2048)
grep -REn '\b(DES|TripleDES|ARC4|ARC2|Blowfish|IDEA|CAST5|SEED|XOR)\b' .  # broken/legacy ciphers
# TLS/PKI validation disabled (CWE-295):
grep -REn 'verify\s*=\s*False|CERT_NONE|check_hostname\s*=\s*False|_create_unverified_context|wrap_socket' .
grep -REn 'AutoAddPolicy|WarningPolicy' .                # paramiko SSH host-key not verified
# Timing-unsafe secret comparison — use hmac.compare_digest:
grep -REn '\b(mac|hmac|sig|signature|digest|token)\b.*[!=]=|[!=]=.*\b(mac|hmac|sig|signature|digest|token)\b' .
```

## Crypto scanners (source pass)

grep is the fallback; a crypto-aware linter is faster and more precise. These
scan **Python source** for crypto/TLS/PKI misuse — run one as a first pass, then
read the hits. They cover the *weak-crypto* class well but, by construction,
**cannot decide FIPS approval** (see the caveat below).

- **[`ruff`](https://docs.astral.sh/ruff/rules/#flake8-bandit-s) — preferred.** Its
  flake8-bandit group reimplements Bandit under the **same codes**; no install
  friction: `uvx ruff check --select S .`. Crypto/TLS/PKI-relevant rules:
  `S324`/`S303` (MD5/SHA-1 hashes), `S304` (DES/RC4/Blowfish/IDEA/CAST5/SEED),
  `S305` (ECB mode), `S311` (`random` for security), `S505` (RSA/DSA <2048, EC
  <224), `S501` (`verify=False`), `S502`/`S503` (SSLv2/3, TLSv1/1.1),
  `S504` (`wrap_socket` no version), `S507` (paramiko `AutoAddPolicy`).
- **[`bandit`](https://bandit.readthedocs.io)** — the original; ruff has ported all
  of its crypto checks, so it adds nothing here unless you need custom AST plugins.
- **[`semgrep`](https://semgrep.dev/p/crypto)** (`semgrep --config p/crypto`) —
  closes ruff's real crypto gaps with dataflow rules ruff/bandit lack: **RSA
  PKCS#1 v1.5 vs OAEP** (CWE-780), **static/reused IV/nonce**, and
  **unauthenticated CBC/CTR without a MAC**. Add it when those matter.

**What no source linter catches — resolve by hand (this skill's job):**
timing-unsafe `==` on MACs/tokens, hand-rolled RSA/modexp, and — the crux for
FIPS — cryptographically **strong but non-approved** primitives
(ChaCha20-Poly1305, BLAKE2/3, X25519, scrypt/Argon2/bcrypt): a linter stays silent
because they aren't "weak," yet they fail FIPS. Vendored/static crypto, bundled CA
stores, and hardcoded ciphersuites that bypass crypto-policies need the binary pass
(`binary-inspection.md`) and steps 6-7, not a source linter.
