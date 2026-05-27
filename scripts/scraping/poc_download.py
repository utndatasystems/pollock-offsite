#!/usr/bin/env python3
"""Tiny proof-of-concept download for one Data.gov CSV resource."""

from __future__ import annotations

from pathlib import Path

from common import CsvCandidate, build_dataset_dirs, download_candidate, write_manifest


POC_CSV = CsvCandidate(
    source="data.gov",
    name="datagov_electric_vehicle_population_data.csv",
    url="https://data.wa.gov/resource/f6w7-q2d2.csv?$limit=1000",
    description="Washington State Electric Vehicle Population Data",
)


def main() -> int:
    dirs = build_dataset_dirs("web_csv_poc", Path("data"))
    path = download_candidate(POC_CSV, dirs, max_mb=10.0, timeout=90, overwrite=True)
    downloaded = [path] if path else []
    write_manifest(downloaded, dirs, {"dataset": "web_csv_poc", "sources": ["data.gov"], "errors": []})
    if path:
        print(f"downloaded {path}")
        print("try: DATASET=web_csv_poc python3 ./sut/pandas/panda.py")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
