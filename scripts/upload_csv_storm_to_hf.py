#!/usr/bin/env python3
"""Upload a Pollock-style CSV dataset folder to the Hugging Face Hub."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from huggingface_hub import HfApi
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    HfApi = None  # type: ignore[assignment]


REQUIRED_SUBDIRS = ("csv", "clean", "parameters")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a data/<dataset> folder with csv, clean, and parameters files to Hugging Face Hub."
    )
    parser.add_argument(
        "dataset_dir",
        nargs="?",
        default="data/csv_storm",
        help="Path to the dataset folder. Defaults to data/csv_storm.",
    )
    parser.add_argument(
        "--repo-id",
        default="csv_storm",
        help=(
            "Hub dataset repository id. Use namespace/csv_storm to upload to an org/user namespace. "
            "Defaults to csv_storm under the authenticated user."
        ),
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create the Hub dataset repository as private if it does not exist.",
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Git revision/branch to upload to. Defaults to main.",
    )
    parser.add_argument(
        "--commit-message",
        default="Upload csv_storm dataset",
        help="Commit message for the Hub upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and stage the dataset, but do not create or upload to the Hub.",
    )
    return parser.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_dataset_dir(dataset_dir: Path) -> list[dict[str, Any]]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory does not exist: {dataset_dir}")
    if not dataset_dir.is_dir():
        raise NotADirectoryError(f"Dataset path is not a directory: {dataset_dir}")

    missing_subdirs = [name for name in REQUIRED_SUBDIRS if not (dataset_dir / name).is_dir()]
    if missing_subdirs:
        raise FileNotFoundError(f"Missing required subdirectories: {', '.join(missing_subdirs)}")

    csv_dir = dataset_dir / "csv"
    clean_dir = dataset_dir / "clean"
    parameters_dir = dataset_dir / "parameters"
    csv_files = sorted(path for path in csv_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv")
    if not csv_files:
        raise ValueError(f"No .csv files found in {csv_dir}")

    records: list[dict[str, Any]] = []
    problems: list[str] = []
    for polluted_path in csv_files:
        filename = polluted_path.name
        clean_path = clean_dir / filename
        parameters_path = parameters_dir / f"{filename}_parameters.json"

        if not clean_path.is_file():
            problems.append(f"missing clean file for {filename}: {clean_path}")
        if not parameters_path.is_file():
            problems.append(f"missing parameters file for {filename}: {parameters_path}")
            parameters: Any = None
        else:
            try:
                parameters = read_json(parameters_path)
            except json.JSONDecodeError as exc:
                problems.append(f"invalid JSON in {parameters_path}: {exc}")
                parameters = None

        records.append(
            {
                "file": filename,
                "polluted_csv": f"csv/{filename}",
                "clean_csv": f"clean/{filename}",
                "parameters_json": f"parameters/{filename}_parameters.json",
                "parameters": parameters,
            }
        )

    if problems:
        raise ValueError("Dataset validation failed:\n  - " + "\n  - ".join(problems))
    return records


def write_manifest(staging_dir: Path, records: list[dict[str, Any]]) -> None:
    with (staging_dir / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    with (staging_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["file", "polluted_csv", "clean_csv", "parameters_json"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record[key] for key in fieldnames})


def write_dataset_card(staging_dir: Path, dataset_name: str, records: list[dict[str, Any]]) -> None:
    card = f"""---
pretty_name: CSV Storm
task_categories:
- tabular-classification
language:
- en
tags:
- csv
- data-cleaning
- benchmark
- pollock
size_categories:
- n<1K
---

# CSV Storm

CSV Storm is a benchmark-style collection of polluted CSV files, their canonical clean parses, and the JSON parameters used to generate or describe each pollution.

## Layout

- `csv/`: polluted CSV inputs.
- `clean/`: expected clean CSV outputs with matching filenames.
- `parameters/`: JSON metadata files named `<filename>_parameters.json`.
- `manifest.csv`: file-level paths for quick inspection.
- `manifest.jsonl`: file-level paths plus embedded parameter JSON.

This upload contains {len(records)} CSV cases staged from `{dataset_name}`.
"""
    (staging_dir / "README.md").write_text(card, encoding="utf-8")


def stage_dataset(dataset_dir: Path, records: list[dict[str, Any]]) -> Path:
    staging_dir = Path(tempfile.mkdtemp(prefix="csv_storm_hf_"))
    for subdir in REQUIRED_SUBDIRS:
        shutil.copytree(dataset_dir / subdir, staging_dir / subdir)
    write_manifest(staging_dir, records)
    write_dataset_card(staging_dir, str(dataset_dir), records)
    return staging_dir


def upload(staging_dir: Path, repo_id: str, private: bool, revision: str, commit_message: str) -> str:
    if HfApi is None:
        raise RuntimeError(
            "huggingface_hub is not installed. Install it with `pip install huggingface_hub` "
            "or `pip install -r requirements.txt` after updating dependencies."
        )

    api = HfApi()
    repo_url = api.create_repo(
        repo_id=repo_id,
        repo_type="dataset",
        private=private,
        exist_ok=True,
    )
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(staging_dir),
        revision=revision,
        commit_message=commit_message,
    )
    return str(repo_url)


def main() -> int:
    args = parse_args()
    dataset_dir = Path(args.dataset_dir)
    records = validate_dataset_dir(dataset_dir)
    staging_dir = stage_dataset(dataset_dir, records)

    print(f"Validated {len(records)} CSV cases from {dataset_dir}")
    print(f"Staged Hugging Face dataset files in {staging_dir}")

    if args.dry_run:
        print("Dry run complete; no Hub repository was created or uploaded.")
        return 0

    repo_url = upload(
        staging_dir=staging_dir,
        repo_id=args.repo_id,
        private=args.private,
        revision=args.revision,
        commit_message=args.commit_message,
    )
    print(f"Uploaded dataset to {repo_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
