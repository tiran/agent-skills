#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyelftools", "macholib", "pefile"]
# ///
"""Cross-format crypto evidence reader for compiled extensions.

Pure-Python parsing of ELF / Mach-O / PE via pyelftools / macholib / pefile,
dispatched by file magic. Unlike readelf/nm/otool/dumpbin (host-native), this runs
on any host and reads *any* arch/OS artifact -- so one Linux runner can inspect a
macOS ``.dylib`` or Windows ``.pyd`` from a wheel it never built.

For each file it reports the three signals SKILL step 5 turns on:

* linked libraries (ELF ``DT_NEEDED`` / PE imports / Mach-O load commands) --
  is a crypto provider a *system* dependency, or a bundled/hash-mangled copy?
* defined vs imported crypto symbols -- *defined* means crypto compiled straight
  in (static); *imported* means it calls an external copy it may not ship.
* version-banner strings -- an ``OpenSSL x.y.z`` banner with ``OPENSSLDIR:`` marks
  a real compiled-in copy; fork tells (BoringSSL / AWS-LC) disambiguate the API.

This gathers evidence; it does not decide FIPS compliance. See
``reference/binary-inspection.md`` for how to read the output, and
``https://github.com/Quansight/torch-abi-audit`` (objectfile.py) for the fuller,
tested parser this is modelled on.

Usage:
  uv run scan_crypto.py path/to/_ext.so [more files ...]
  python scan_crypto.py path/to/_ext.pyd        # if deps already installed
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Crypto API symbols worth surfacing, across the validated system providers
# (OpenSSL/forks, NSS, GnuTLS, libgcrypt, nettle) plus common bundled libraries
# (ring, libsodium, BoringCrypto).
CRYPTO_SYM = re.compile(
    r"EVP_|SSL_|OSSL_|RAND_|BN_|HMAC_|PKCS5_|X509_|EC_KEY_|RSA_"  # OpenSSL & forks
    r"|PK11_|NSS_|SECMOD_|SECKEY_|SECOID_"  # NSS
    r"|gnutls_|gcry_|nettle_"  # GnuTLS / libgcrypt / nettle
    r"|ring_|GFp_|aws_lc|awslc|sodium_|nacl_|BORINGSSL|goboringcrypto"  # bundled
)
# Version banners / fork tells found in a raw string scan.
CRYPTO_STR = re.compile(
    rb"OpenSSL \d[\w. ]+|OPENSSLDIR|BoringSSL|OPENSSL_IS_AWSLC|AWSLC_VERSION"
    rb"|LibreSSL|libsodium|/ring-\d|/openssl-sys-\d|/aws-lc-"
    rb"|GnuTLS|libgcrypt|Libgcrypt|nettle|NSS ",  # GnuTLS / libgcrypt / nettle / NSS
)
# System crypto-provider sonames / DLL names.
CRYPTO_LIB = re.compile(
    r"crypto|ssl|sodium|nacl|gcrypt|gnutls|nettle|hogweed"  # OpenSSL/GnuTLS/gcrypt/nettle
    r"|nss|nspr|freebl|softokn|smime"  # NSS family
)

_ELF_MAGIC = b"\x7fELF"
_PE_MAGIC = b"MZ"
# Mach-O thin (LE/BE, 32/64-bit) and fat/universal (LE/BE, 32/64) magics.
_MACHO_MAGICS = frozenset(
    {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }
)


class Report:
    """Evidence for one object file."""

    def __init__(self, path: Path, fmt: str) -> None:
        self.path = path
        self.fmt = fmt
        self.needed: set[str] = set()
        self.defined: set[str] = set()
        self.imported: set[str] = set()
        self.banners: set[str] = set()

    def crypto_defined(self) -> list[str]:
        return sorted(s for s in self.defined if CRYPTO_SYM.search(s))

    def crypto_imported(self) -> list[str]:
        return sorted(s for s in self.imported if CRYPTO_SYM.search(s))

    def crypto_needed(self) -> list[str]:
        return sorted(n for n in self.needed if CRYPTO_LIB.search(n))


def read(path: Path) -> Report:
    magic = path.read_bytes()[:4]
    if magic == _ELF_MAGIC:
        rep = _read_elf(path)
    elif magic in _MACHO_MAGICS:
        rep = _read_macho(path)
    elif magic[:2] == _PE_MAGIC:
        rep = _read_pe(path)
    else:
        raise ValueError(f"unrecognised object file format: {path}")
    _scan_strings(path, rep)
    return rep


def _read_elf(path: Path) -> Report:
    from elftools.elf.dynamic import DynamicSection
    from elftools.elf.elffile import ELFFile
    from elftools.elf.sections import SymbolTableSection

    rep = Report(path, "ELF")
    with path.open("rb") as fh:
        elf = ELFFile(fh)
        dyn = elf.get_section_by_name(".dynamic")
        if isinstance(dyn, DynamicSection):
            for tag in dyn.iter_tags("DT_NEEDED"):
                rep.needed.add(tag.needed)
        # .dynsym is authoritative for dynamic linkage; .symtab (unstripped) can
        # additionally surface a static copy hidden from .dynsym by a version script.
        for name in (".dynsym", ".symtab"):
            sec = elf.get_section_by_name(name)
            if isinstance(sec, SymbolTableSection):
                for sym in sec.iter_symbols():
                    if not sym.name:
                        continue
                    if sym["st_shndx"] == "SHN_UNDEF":
                        rep.imported.add(sym.name)
                    else:
                        rep.defined.add(sym.name)
    return rep


def _read_macho(path: Path) -> Report:
    from macholib.mach_o import LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB
    from macholib.MachO import MachO
    from macholib.SymbolTable import SymbolTable

    rep = Report(path, "Mach-O")
    dep_cmds = {LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB}
    for header in MachO(str(path)).headers:  # fat binary: one header per arch
        for load_cmd, _, data in header.commands:
            if load_cmd.cmd in dep_cmds and isinstance(data, bytes):
                rep.needed.add(data.rstrip(b"\x00").decode("utf-8", "replace"))
        table = SymbolTable(header)
        for _, raw in table.undefsyms:
            if name := _macho_name(raw):
                rep.imported.add(name)
        for _, raw in (*table.extdefsyms, *table.localsyms):
            if name := _macho_name(raw):
                rep.defined.add(name)
    return rep


def _macho_name(raw: bytes | str) -> str:
    name = raw.decode("utf-8", "surrogateescape") if isinstance(raw, bytes) else raw
    return name.removeprefix("_")  # drop the external-symbol underscore


def _read_pe(path: Path) -> Report:
    import pefile

    rep = Report(path, "PE")
    pe = pefile.PE(str(path))
    try:
        pe.parse_data_directories()
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", ()):
            if entry.dll:
                rep.needed.add(entry.dll.decode())
            for imp in entry.imports:
                if imp.name:
                    rep.imported.add(imp.name.decode())
        export_dir = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
        if export_dir is not None:
            for exp in export_dir.symbols:
                if exp.name:
                    rep.defined.add(exp.name.decode())
    finally:
        pe.close()
    return rep


def _scan_strings(path: Path, rep: Report) -> None:
    """A strings(1)-style banner scan -- catches a static copy with no imports."""
    data = path.read_bytes()
    for match in CRYPTO_STR.finditer(data):
        rep.banners.add(match.group().decode("utf-8", "replace"))


def _fmt(items: list[str], verbose: bool, cap: int = 12) -> str:
    if not items:
        return "(none)"
    if verbose or len(items) <= cap:
        return ", ".join(items)
    return f"{', '.join(items[:cap])}  (+{len(items) - cap} more; -v for all)"


def _print(rep: Report, verbose: bool) -> None:
    defined, imported = rep.crypto_defined(), rep.crypto_imported()
    print(f"\n{rep.path}  [{rep.fmt}]")
    print(f"  crypto libs linked : {_fmt(rep.crypto_needed(), verbose)}")
    print(f"  defined (static)   : [{len(defined)}] {_fmt(defined, verbose)}")
    print(f"  imported (external): [{len(imported)}] {_fmt(imported, verbose)}")
    print(f"  banners/strings    : {_fmt(sorted(rep.banners), verbose)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="object file(s) to scan")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print every symbol, uncapped"
    )
    args = parser.parse_args(argv)

    exit_code = 0
    for path in args.files:
        try:
            _print(read(path), args.verbose)
        except Exception as exc:  # noqa: BLE001 -- keep going across a file set
            print(f"\n{path}: ERROR: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
