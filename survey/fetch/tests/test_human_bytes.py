"""Unit tests for ``_backend._human_bytes`` byte-spec parser."""

from __future__ import annotations

import argparse

import pytest

from survey.fetch._backend import _human_bytes


@pytest.mark.parametrize(
    "spec,expected",
    [
        ("50G", 50 * 1024**3),
        ("500M", 500 * 1024**2),
        ("2K", 2 * 1024),
        ("1T", 1 * 1024**4),
        ("1024", 1024),
        ("0", 0),
        ("1.5G", int(1.5 * 1024**3)),
        ("  4M  ", 4 * 1024**2),
        ("2k", 2 * 1024),  # lower-case unit accepted
    ],
)
def test_parses_valid_specs(spec: str, expected: int) -> None:
    assert _human_bytes(spec) == expected


@pytest.mark.parametrize("spec", ["", "   ", "abc", "G", "10X", "5.5.5M"])
def test_rejects_malformed(spec: str) -> None:
    with pytest.raises((argparse.ArgumentTypeError, ValueError)):
        _human_bytes(spec)
