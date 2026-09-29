# Weak / insecure crypto (independent of FIPS)

The skill's **use case 2** and **finding class 3**: cryptography that is **insecure as
used**, regardless of FIPS. Raise these **even on a FIPS host** — an approved algorithm
can still be broken by *how* it's used, and these are real vulnerabilities off a FIPS
host too. Keep them in their **own class** (SKILL step 8), distinct from
*non-approved-but-strong* (`fips-primer.md`) and *system-integration / trust*
(`trust-store.md`). Cited from the OWASP/CWE and library docs referenced inline; a
source linter finds most of these fast (see "Find it," below).

A crypto-aware linter is the fast first pass; run it, then read the hits and resolve
the rest by hand. This lens is the reporting home for whatever it (or grep) surfaces.

## Insecure use of an approved primitive

An algorithm on the approved list, broken by construction or usage:

- **AES-ECB for data.** ECB is approved as a bare primitive (FIPS 197 / SP 800-38A) but
  leaks plaintext structure — identical blocks encrypt identically (the "ECB penguin").
  Flag `modes.ECB(` (`cryptography`), `AES.new(key, AES.MODE_ECB)` (pycryptodome), or
  any `MODE_ECB` for confidentiality; want an **AEAD (AES-GCM)**, or CBC/CTR with a
  random IV.
- **RSA padding.** Encryption must use **OAEP**, signatures **PSS**. **PKCS#1 v1.5
  *encryption* is Bleichenbacher-vulnerable** (adaptive chosen-ciphertext / the Marvin
  timing oracle); textbook/"raw" unpadded RSA is worse. v1.5 *signatures* are
  legacy-tolerated but PSS is preferred. Flag `PKCS1v15()`/`PKCS1_v1_5` for
  encrypt/decrypt and any unpadded RSA. `cryptography`'s `OAEP`/`PSS` are the good path.
- **Hand-rolled crypto.** A pure-Python RSA (`pow(m, e, n)`, `divmod`-based modexp, a
  bespoke `encrypt`/`sign`) is **not constant-time** and skips padding/RNG/parameter
  checks; **blinding narrows but doesn't close the side channel**. Flag such code and
  the pure-Python `rsa`/`ecdsa` packages; use a vetted library (`cryptography`) over a
  validated module.
- **Static / reused IVs and nonces.** A hardcoded IV, a zero nonce, or a counter that
  resets is catastrophic for CTR/GCM — **nonce reuse breaks GCM entirely** (recovers
  the auth key). Flag literal `iv=b"..."` / `nonce=` constants near cipher construction.
- **Unauthenticated encryption.** CBC/CTR with no MAC → malleable, padding-oracle-prone
  ([CWE-347](https://cwe.mitre.org/data/definitions/347.html)). Prefer an AEAD (AES-GCM)
  or encrypt-then-MAC.
- **Non-constant-time secret comparison.** Comparing a MAC, token, or password hash
  with `==`/`!=` leaks length and content through timing. Use
  `hmac.compare_digest(a, b)` (or `secrets.compare_digest`).
- **Home-made MAC / length extension.** `H(secret || message)` with an MD5/SHA-1/SHA-2
  hash is forgeable via a
  [length-extension attack](https://en.wikipedia.org/wiki/Length_extension_attack).
  Use **HMAC** (or KMAC/SHA-3/BLAKE2, which aren't affected), never a raw keyed hash.
- **(EC)DSA nonce reuse / bias.** A reused or predictable per-signature `k` **leaks the
  private key** ([the PS3 / Android-wallet class](https://en.wikipedia.org/wiki/EdDSA#Secret_key_leakage_from_nonce_reuse)).
  Use deterministic (EC)DSA ([RFC 6979](https://www.rfc-editor.org/rfc/rfc6979)) or EdDSA
  via a vetted library; flag hand-rolled signing.

## Weak keys, broken hashes, legacy ciphers

Weak *regardless* of FIPS (several also carry a FIPS status — see `fips-primer.md` for
approval; here they're flagged as insecure-as-used):

- **Weak key sizes / DH parameters.** RSA/DSA/DH **< 2048** bits, EC curves **< 224**
  bits (SP 800-131A floor; weak everywhere, not just under FIPS). Flag
  `key_size=512/768/1024`, and small/non-safe or export-grade **DH groups**
  ([Logjam](https://weakdh.org/)).
- **Broken hashes for security.** **MD5, MD4** (collisions/preimage) and **SHA-1 for
  signatures/integrity** (SHAttered). Fine for non-security checksums with
  `usedforsecurity=False`; a finding when they gate a security decision.
- **Legacy / broken ciphers.** single-DES and two-key/three-key **3DES**, **RC4/ARC4**,
  RC2, **Blowfish**, **IDEA**, **CAST5**, **SEED**, and home-grown `XOR` "encryption" —
  weak for confidentiality. Flag their use; want AES-GCM.

## Randomness for secrets

**`random`** (Mersenne Twister) is **not** a CSPRNG — its state is recoverable from
output. Flag `random.*` used for keys/tokens/nonces/salts/passwords/session IDs; use
**`secrets`** / **`os.urandom`** / `random.SystemRandom`. Non-security use (sampling,
jitter, test data) is fine — decide by *use*. (Stdlib detail: `python-audit.md` →
"random vs secrets".)

## Disabled TLS / certificate validation (CWE-295)

Turning off verification is a weak-crypto finding (distinct from **swapping** the CA
trust store, which is `trust-store.md`):

- `verify=False` (`requests`/`httpx`), urllib3 `cert_reqs="CERT_NONE"` +
  `assert_hostname=False` + `disable_warnings(InsecureRequestWarning)`, aiohttp
  `ssl=False`, pycurl `SSL_VERIFYPEER=0`/`SSL_VERIFYHOST=0`.
- `ssl.CERT_NONE`, `check_hostname=False`, `ssl._create_unverified_context()` /
  reassigning `ssl._create_default_https_context`, bare `ssl.wrap_socket(...)`.
- Insecure protocol versions: `PROTOCOL_SSLv2`/`SSLv3`/`SSLv23`/`TLSv1`/`TLSv1_1`.
- paramiko `set_missing_host_key_policy(AutoAddPolicy())` — no SSH host-key
  verification. (CWE-295; Bandit **B501-B504/B507**.)
- **Broken hostname matching** ([CWE-297](https://cwe.mitre.org/data/definitions/297.html)):
  chain validated but the name not checked — hand-rolled CN/SAN matching (wildcard /
  null-byte bugs), a verify callback that skips the host, or SNI set without binding an
  expected host (`SSL_set_tlsext_host_name` but no `SSL_set1_host`), and deprecated
  `ssl.match_hostname`. Prefer library defaults ([RFC 6125](https://www.rfc-editor.org/rfc/rfc6125)).

## More classes (flag by use; see the reference)

Terse pointers — the linked sources have the detail:

- **Password hashing.** Static/predictable salt
  ([CWE-759](https://cwe.mitre.org/data/definitions/759.html)/[760](https://cwe.mitre.org/data/definitions/760.html)),
  too-few PBKDF2 iterations, or PBKDF2-HMAC-MD5. Per-password random salt + adequate
  work factor (Argon2id/scrypt/bcrypt off a FIPS host; PBKDF2-HMAC-SHA-256/512 on one).
- **Hardcoded keys / secrets / IVs** in source
  ([CWE-321](https://cwe.mitre.org/data/definitions/321.html)/[259](https://cwe.mitre.org/data/definitions/259.html)) —
  unrotatable, leaks via the repo/artifact. Move to a KMS/secret store; run a secret scanner.
- **Token/JWT verification** (if present): `alg=none` and HS/RS algorithm confusion
  ([CWE-347](https://cwe.mitre.org/data/definitions/347.html)) — pin the expected alg server-side.
- General checklists: [OWASP Top 10 A02 Cryptographic Failures](https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/),
  [OWASP WSTG — Testing for Weak Cryptography](https://owasp.org/www-project-web-security-testing-guide/).

## Find it: greps + linters

```bash
grep -REn 'modes\.ECB|MODE_ECB' .                        # AES-ECB leaks structure
grep -REn 'PKCS1v15|PKCS1_v1_5' .                        # RSA v1.5 encryption; want OAEP/PSS
grep -REn '^\s*import rsa\b|from rsa\b|\bpow\([^,]+,[^,]+,[^)]+\)|divmod' .  # hand-rolled RSA/modexp
grep -REn "\b(iv|nonce)\s*=\s*(b?['\"]|bytes\(|\\\\x00)" .  # static/hardcoded IV or nonce
grep -REn 'key_size\s*=\s*(512|768|1024)' .              # weak RSA/DSA key (floor: 2048)
grep -REn '\b(DES|TripleDES|ARC4|ARC2|Blowfish|IDEA|CAST5|SEED|XOR)\b' .  # broken/legacy ciphers
grep -REn '\brandom\.(random|randint|choice|getrandbits|shuffle)' .   # random for secrets?
grep -REn 'verify\s*=\s*False|CERT_NONE|check_hostname\s*=\s*False|_create_unverified_context|wrap_socket' .
grep -REn 'cert_reqs\s*=\s*.CERT_NONE|assert_hostname\s*=\s*False|SSL_VERIFYPEER|SSL_VERIFYHOST|verify_ssl\s*=\s*False|disable_warnings|InsecureRequestWarning' .
grep -REn 'AutoAddPolicy|WarningPolicy' .                # paramiko host-key not verified
grep -REn '\b(mac|hmac|sig|signature|digest|token)\b.*[!=]=|[!=]=.*\b(mac|hmac|sig|signature|digest|token)\b' .  # timing-unsafe compare
```

Exclude test code from the results — suites deliberately use weak/known-bad values
(negative tests, KAT vectors); don't flag `tests/`/fixtures/`examples/` unless imported
at runtime or shipped in the wheel.

grep is the fallback; a crypto-aware linter is faster and more precise. These scan
**Python source** for crypto/TLS/PKI misuse — run one first, then read the hits. They
cover the weak-crypto class well but, by construction, **cannot decide FIPS approval**.

- **[`ruff`](https://docs.astral.sh/ruff/rules/#flake8-bandit-s) — preferred.** Its
  flake8-bandit group reimplements Bandit under the **same codes**; no install
  friction: `uvx ruff check --select S .`. Crypto/TLS/PKI rules: `S324`/`S303`
  (MD5/SHA-1 hashes), `S304` (DES/RC4/Blowfish/IDEA/CAST5/SEED), `S305` (ECB mode),
  `S311` (`random` for security), `S505` (RSA/DSA <2048, EC <224), `S501`
  (`verify=False`), `S502`/`S503` (SSLv2/3, TLSv1/1.1), `S504` (`wrap_socket` no
  version), `S507` (paramiko `AutoAddPolicy`).
- **[`bandit`](https://bandit.readthedocs.io)** — the original; ruff ported its crypto
  checks, so it adds nothing here unless you need custom AST plugins.
- **[`semgrep`](https://semgrep.dev/p/crypto)** (`semgrep --config p/crypto`) — closes
  ruff's gaps with dataflow rules: **RSA PKCS#1 v1.5 vs OAEP** (CWE-780),
  **static/reused IV/nonce**, and **unauthenticated CBC/CTR without a MAC**.

**What no source linter catches — resolve by hand:** timing-unsafe `==` on MACs/tokens,
hand-rolled RSA/modexp, and — the crux for FIPS — cryptographically **strong but
non-approved** primitives (ChaCha20-Poly1305, BLAKE2/3, X25519, scrypt/Argon2/bcrypt):
a linter stays silent because they aren't "weak," yet they fail FIPS (`fips-primer.md`).
Vendored/static crypto, bundled CA stores, and hardcoded ciphersuites that bypass
crypto-policies need the binary pass (`binary-inspection.md`) and SKILL steps 6-7.
