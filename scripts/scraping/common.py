#!/usr/bin/env python3
"""Shared helpers for collecting benchmark CSV files from public catalogues."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "pollock-offsite-csv-scraper/0.1 (+https://github.com/)"
DEFAULT_TIMEOUT = 60


@dataclass(frozen=True)
class CsvCandidate:
    source: str
    name: str
    url: str
    description: str = ""


def build_dataset_dirs(dataset: str, output_root: Path) -> dict[str, Path]:
    root = output_root / dataset
    dirs = {
        "root": root,
        "csv": root / "csv",
        "clean": root / "clean",
        "parameters": root / "parameters",
        "metadata": root / "metadata",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def http_get(url: str, *, timeout: int = DEFAULT_TIMEOUT, accept: str = "*/*") -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(req, timeout=timeout) as response:
        body = response.read()
        encoding = response.headers.get("Content-Encoding", "").lower()
        if encoding == "gzip":
            return gzip.decompress(body)
        return body


def http_get_json(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict:
    return json.loads(http_get(url, timeout=timeout, accept="application/json").decode("utf-8"))


def add_query(url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in url else "?"
    return url + separator + urlencode(params)


def safe_filename(name: str, fallback: str = "download.csv") -> str:
    parsed_name = Path(urlparse(name).path).name if "://" in name else name
    stem = parsed_name.rsplit(".", 1)[0] if parsed_name.lower().endswith(".csv") else parsed_name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not stem:
        stem = fallback.rsplit(".", 1)[0]
    return stem[:180] + ".csv"


def unique_path(directory: Path, filename: str) -> Path:
    path = directory / filename
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(2, 10_000):
        candidate = directory / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find a unique filename for {filename}")


def looks_like_csv_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith(".csv") or path.endswith(".csv.gz") or "format=csv" in parsed.query.lower()


def decode_csv_bytes(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding.replace("-sig", "")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


def sniff_dialect(text: str) -> tuple[str, str, str]:
    sample = text[:64_000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
        quotechar = dialect.quotechar or '"'
        escapechar = dialect.escapechar or quotechar
    except csv.Error:
        delimiter = ","
        quotechar = '"'
        escapechar = '"'
    return delimiter, quotechar, escapechar


def sniff_header_and_columns(text: str, delimiter: str, quotechar: str) -> tuple[int, list[str]]:
    first_lines = [line for line in text.splitlines() if line.strip()]
    if not first_lines:
        return 0, []
    try:
        rows = list(csv.reader(first_lines[:5], delimiter=delimiter, quotechar=quotechar or '"'))
    except csv.Error:
        return 1, []
    first = rows[0] if rows else []
    try:
        has_header = csv.Sniffer().has_header("\n".join(first_lines[:20]))
    except csv.Error:
        has_header = True
    return (1 if has_header else 0), first


def newline_for_parameters(raw: bytes) -> str:
    head = raw[:64_000]
    crlf = head.count(b"\r\n")
    lf = head.count(b"\n") - crlf
    cr = head.count(b"\r") - crlf
    if crlf >= lf and crlf >= cr:
        return "\r\n"
    if cr >= lf:
        return "\r"
    return "\n"


def write_clean_csv(csv_path: Path, raw: bytes, clean_dir: Path) -> None:
    text, _ = decode_csv_bytes(raw)
    delimiter, quotechar, escapechar = sniff_dialect(text)
    reader_kwargs = {"delimiter": delimiter, "quotechar": quotechar or "\""}
    if escapechar and escapechar != quotechar:
        reader_kwargs["escapechar"] = escapechar
    input_buffer = io.StringIO(text)
    output_buffer = io.StringIO(newline="")
    writer = csv.writer(output_buffer, lineterminator="\n")
    for row in csv.reader(input_buffer, **reader_kwargs):
        writer.writerow(row)
    (clean_dir / csv_path.name).write_text(output_buffer.getvalue(), encoding="utf-8")


def write_parameter_file(csv_path: Path, raw: bytes, source: CsvCandidate, parameters_dir: Path) -> None:
    text, encoding = decode_csv_bytes(raw)
    delimiter, quotechar, escapechar = sniff_dialect(text)
    header_lines, column_names = sniff_header_and_columns(text, delimiter, quotechar)
    n_columns = len(column_names)
    params = {
        "encoding": encoding,
        "encoding_confidence": 1.0,
        "delimiter": delimiter,
        "quotechar": quotechar,
        "escapechar": escapechar,
        "row_delimiter": newline_for_parameters(raw),
        "header_lines": str(header_lines),
        "preamble_lines": "0",
        "footnote_lines": "0",
        "column_names": column_names if header_lines else [],
        "n_columns": n_columns,
        "source": source.source,
        "source_url": source.url,
        "source_description": source.description,
    }
    out = parameters_dir / f"{csv_path.name}_parameters.json"
    out.write_text(json.dumps(params, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def download_candidate(
    candidate: CsvCandidate,
    dirs: dict[str, Path],
    *,
    max_mb: float,
    timeout: int,
    overwrite: bool = False,
) -> Path | None:
    filename = safe_filename(candidate.name or candidate.url)
    out_path = (dirs["csv"] / filename) if overwrite else unique_path(dirs["csv"], filename)

    raw = http_get(candidate.url, timeout=timeout)
    if candidate.url.lower().split("?", 1)[0].endswith(".gz"):
        raw = gzip.decompress(raw)

    max_bytes = int(max_mb * 1024 * 1024)
    if len(raw) > max_bytes:
        print(f"skip too-large ({len(raw) / 1024 / 1024:.2f} MB): {candidate.url}")
        return None

    if raw.lstrip().startswith(b"<"):
        print(f"skip non-csv/xml-ish response: {candidate.url}")
        return None

    out_path.write_bytes(raw)
    write_clean_csv(out_path, raw, dirs["clean"])
    write_parameter_file(out_path, raw, candidate, dirs["parameters"])
    return out_path


def write_manifest(downloaded: Iterable[Path], dirs: dict[str, Path], metadata: dict) -> None:
    manifest = {
        "files": [path.name for path in downloaded],
        **metadata,
    }
    (dirs["metadata"] / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def polite_pause(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def format_error(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}: {exc.reason}"
    if isinstance(exc, URLError):
        return f"URL error: {exc.reason}"
    return str(exc)
