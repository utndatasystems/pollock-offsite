"""Unit tests for ``_filters.looks_like_csv`` and ``_filters.is_safe_http_url``."""

from __future__ import annotations

import pytest

from survey.fetch._filters import is_safe_http_url, looks_like_csv


# ---------- looks_like_csv -----------------------------------------------------

@pytest.mark.parametrize(
    "body,content_type,expected",
    [
        # HTML doctype variants.
        (b"<!DOCTYPE html><html>", "text/html", False),
        (b"<html><body>404</body></html>", "", False),
        # JSON wrapper.
        (b'{"error": "not found"}', "application/json", False),
        (b'  {"key": "value"}', "", False),
        # XML.
        (b"<?xml version='1.0'?><doc/>", "application/xml", False),
        (b"<doc/>", "text/xml", False),
        # ZIP magic.
        (b"PK\x03\x04rest_of_zip", "application/octet-stream", False),
        (b"valid,csv,body\n1,2,3\n", "application/zip", False),
        # Valid CSV bodies (some without content-type).
        (b"a,b,c\n1,2,3\n", "text/csv", True),
        (b"col1,col2\nfoo,bar\n", "", True),
        # Tabular with a number-leading first row.
        (b"1,2,3\n4,5,6\n", "application/octet-stream", True),
    ],
)
def test_looks_like_csv(body: bytes, content_type: str, expected: bool) -> None:
    assert looks_like_csv(body, content_type) is expected


# ---------- is_safe_http_url ---------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        # Valid public URLs.
        ("https://catalog.data.gov/dataset/x.csv", True),
        ("http://example.com/file.csv", True),
        ("https://data.europa.eu:443/x.csv", True),
        # Wrong scheme.
        ("file:///etc/passwd", False),
        ("ftp://example.com/x.csv", False),
        ("javascript:alert(1)", False),
        ("data:text/csv;base64,QUJD", False),
        # Userinfo is forbidden.
        ("https://user:pass@example.com/x.csv", False),
        ("https://user@example.com/x.csv", False),
        # RFC1918 / private literal IPs.
        ("http://10.0.0.1/x", False),
        ("http://192.168.1.1/x", False),
        ("http://172.16.0.1/x", False),
        # Loopback.
        ("http://127.0.0.1/x", False),
        ("http://[::1]/x", False),
        # Link-local / multicast.
        ("http://169.254.169.254/x", False),
        ("http://224.0.0.1/x", False),
        # Local-network hostnames.
        ("http://localhost/x", False),
        ("http://my-host.internal/x", False),
        ("http://something.local/x", False),
        # Empty / malformed.
        ("", False),
        ("not a url", False),
        ("https:///nopath", False),
    ],
)
def test_is_safe_http_url(url: str, expected: bool) -> None:
    assert is_safe_http_url(url) is expected
