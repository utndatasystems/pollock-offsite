#!/usr/bin/env python3
"""Collect CSV files from Eurostat and Data.gov for Pollock benchmark datasets."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from common import (
    CsvCandidate,
    add_query,
    build_dataset_dirs,
    download_candidate,
    format_error,
    http_get,
    http_get_json,
    looks_like_csv_url,
    polite_pause,
    positive_int,
    write_manifest,
)


EUROSTAT_INVENTORY_URL = "https://ec.europa.eu/eurostat/api/dissemination/files/inventory?type=data&lang=en"
DATA_GOV_SEARCH_URL = "https://api.gsa.gov/technology/datagov/v3/action/package_search"


def eurostat_candidates(prefixes: list[str], limit: int, timeout: int) -> list[CsvCandidate]:
    raw = http_get(EUROSTAT_INVENTORY_URL, timeout=timeout).decode("utf-8-sig")
    lines = raw.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) < len(header):
            continue
        row = dict(zip(header, cells))
        code = row.get("Code", "")
        if prefixes and not any(code.upper().startswith(prefix.upper()) for prefix in prefixes):
            continue
        url = row.get("Data download url (csv)") or row.get("Data download url (CSV)")
        if not url:
            continue
        rows.append(
            CsvCandidate(
                source="eurostat",
                name=f"eurostat_{code}.csv",
                url=url,
                description=row.get("Title", ""),
            )
        )
        if len(rows) >= limit:
            break
    return rows


def data_gov_candidates(query: str, limit: int, timeout: int, api_key: str) -> list[CsvCandidate]:
    url = add_query(
        DATA_GOV_SEARCH_URL,
        {
            "api_key": api_key,
            "q": query,
            "rows": str(max(limit * 5, 10)),
        },
    )
    payload = http_get_json(url, timeout=timeout)
    results = payload.get("result", {}).get("results", [])
    candidates: list[CsvCandidate] = []
    for package in results:
        package_title = package.get("title") or package.get("name") or "data.gov package"
        for resource in package.get("resources", []):
            resource_url = resource.get("url") or ""
            resource_format = (resource.get("format") or "").lower()
            if resource_format != "csv" and not looks_like_csv_url(resource_url):
                continue
            candidates.append(
                CsvCandidate(
                    source="data.gov",
                    name=f"datagov_{resource.get('name') or package_title}.csv",
                    url=resource_url,
                    description=package_title,
                )
            )
            if len(candidates) >= limit:
                return candidates
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="web_csv_dump", help="Dataset folder below data/.")
    parser.add_argument("--output-root", default="data", type=Path, help="Root output directory.")
    parser.add_argument("--sources", default="eurostat,datagov", help="Comma-separated: eurostat,datagov.")
    parser.add_argument("--max-files", default=10, type=positive_int, help="Maximum files to download total.")
    parser.add_argument("--max-mb", default=25.0, type=float, help="Skip individual files larger than this.")
    parser.add_argument("--timeout", default=60, type=positive_int, help="HTTP timeout in seconds.")
    parser.add_argument("--pause", default=0.2, type=float, help="Seconds to wait between downloads.")
    parser.add_argument(
        "--eurostat-prefixes",
        default="TPS,TEI",
        help="Comma-separated dataset code prefixes to keep from Eurostat inventory.",
    )
    parser.add_argument("--data-gov-query", default="csv", help="Data.gov CKAN package_search query.")
    parser.add_argument(
        "--data-gov-api-key",
        default=os.environ.get("DATA_GOV_API_KEY", "DEMO_KEY"),
        help="Data.gov API key. Defaults to DATA_GOV_API_KEY or DEMO_KEY.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dirs = build_dataset_dirs(args.dataset, args.output_root)
    requested_sources = {source.strip().lower() for source in args.sources.split(",") if source.strip()}
    candidates: list[CsvCandidate] = []
    per_source_limit = max(args.max_files, 1)

    if "eurostat" in requested_sources:
        prefixes = [p.strip() for p in args.eurostat_prefixes.split(",") if p.strip()]
        print(f"discover eurostat candidates from prefixes={prefixes}")
        candidates.extend(eurostat_candidates(prefixes, per_source_limit, args.timeout))

    if "datagov" in requested_sources or "data.gov" in requested_sources:
        print(f"discover data.gov candidates for query={args.data_gov_query!r}")
        candidates.extend(data_gov_candidates(args.data_gov_query, per_source_limit, args.timeout, args.data_gov_api_key))

    downloaded: list[Path] = []
    errors: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        if len(downloaded) >= args.max_files:
            break
        try:
            print(f"download {candidate.source}: {candidate.name}")
            path = download_candidate(candidate, dirs, max_mb=args.max_mb, timeout=args.timeout)
            if path:
                downloaded.append(path)
        except Exception as exc:
            message = format_error(exc)
            print(f"failed {candidate.url}: {message}")
            errors.append({"url": candidate.url, "error": message, "source": candidate.source})
        polite_pause(args.pause)

    write_manifest(
        downloaded,
        dirs,
        {
            "dataset": args.dataset,
            "sources": sorted(requested_sources),
            "errors": errors,
        },
    )
    print(f"downloaded {len(downloaded)} file(s) into {dirs['root']}")
    return 0 if downloaded else 1


if __name__ == "__main__":
    raise SystemExit(main())
