#!/usr/bin/env python3
"""Encode/decode PyTorch's TORCH_TARGET_VERSION.

The stable-ABI floor is passed to the compiler as a 64-bit hex token where the
major version sits in the top byte and the minor in the next
(``(major << 56) | (minor << 48)``). Getting that bit-packing right by hand is
easy to botch, so use this instead of computing it in your head.

  2.10 -> 0x020a000000000000
  2.11 -> 0x020b000000000000
  2.13 -> 0x020d000000000000

Standard library only; no torch import required.

Usage:
  python torch_target_version.py encode 2.11      # -> 0x020b000000000000
  python torch_target_version.py decode 0x020b000000000000   # -> 2.11
  python torch_target_version.py decode 147211412819673088    # int also accepted -> 2.11
"""

from __future__ import annotations

import argparse
import sys


def encode(major: int, minor: int) -> int:
    """Pack (major, minor) into the TORCH_TARGET_VERSION integer."""
    if not (0 <= major <= 0xFF and 0 <= minor <= 0xFF):
        raise ValueError(f"major/minor must each fit in one byte: {major}.{minor}")
    return (major << 56) | (minor << 48)


def decode(value: int) -> tuple[int, int]:
    """Recover (major, minor) from a TORCH_TARGET_VERSION integer.

    Accepts the value read back from ``_C.TORCH_TARGET_VERSION`` on a stable build.
    """
    return (value >> 56) & 0xFF, (value >> 48) & 0xFF


def _parse_version(text: str) -> tuple[int, int]:
    major, _, minor = text.partition(".")
    if not minor:
        raise ValueError(f"expected MAJOR.MINOR, got {text!r}")
    return int(major), int(minor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_enc = sub.add_parser("encode", help="MAJOR.MINOR -> hex token")
    p_enc.add_argument("version", help="e.g. 2.11")

    p_dec = sub.add_parser("decode", help="hex/int token -> MAJOR.MINOR")
    p_dec.add_argument("token", help="e.g. 0x020b000000000000")

    args = parser.parse_args(argv)

    if args.cmd == "encode":
        major, minor = _parse_version(args.version)
        print(f"0x{encode(major, minor):016x}")
    else:  # decode
        value = int(args.token, 0)  # base 0 -> honours a 0x prefix, else decimal
        major, minor = decode(value)
        print(f"{major}.{minor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
