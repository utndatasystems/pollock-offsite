"""Unit parsers shared by every CLI in the survey package."""

from __future__ import annotations

import argparse


def human_bytes(s: str) -> int:
    """Parse ``50G`` / ``500M`` / ``2K`` / raw int into bytes."""
    s = s.strip()
    if not s:
        raise argparse.ArgumentTypeError("empty byte spec")
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    last = s[-1].upper()
    if last in units:
        return int(float(s[:-1]) * units[last])
    return int(s)
