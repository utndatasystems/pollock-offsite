"""Shared helpers for strict and Pollock-style CSV evaluation."""

from __future__ import annotations

import json
import os
import re
import traceback
import warnings
from typing import Iterable

import pandas as pd
from pqdm.processes import pqdm

import pollution.metrics as metrics
from sut.utils import print


POLLOCK_MEASURES = (
    "success",
    "header_precision",
    "header_recall",
    "header_f1",
    "record_precision",
    "record_recall",
    "record_f1",
    "cell_precision",
    "cell_recall",
    "cell_f1",
)
SIMILARITY_MEASURES = POLLOCK_MEASURES[1:]
SUB_MEASURES = {
    "table": r"file_double.*|file_header.*|file_no.*|file_one.*|file_multi.*|file_preamble.*",
    "inconsistent": r"%row_less.*|row_more",
    "structural": r"file_field.*|row_field.*|file_quote.*|file_record_delimiter.*|row_extra_quote.*|file_escape.*",
}


def load_weights(dataset: str) -> dict[str, float]:
    if dataset != "polluted_files" or not os.path.exists("pollock_weights.json"):
        return {}
    with open("pollock_weights.json", encoding="utf-8") as handle:
        return json.load(handle)


def result_suffix(origin_csv: str | None, row_order_invariant: bool) -> str:
    return ("_incl_origin" if origin_csv is not None else "") + (
        "" if row_order_invariant else "_no_row_order_invariance"
    )


def _empty_result(filename: str, sut: str) -> dict:
    result = {
        "file": filename,
        f"{sut}_metric_ground_truth": None,
        f"{sut}_strict_ground_truth": None,
        f"{sut}_matched_ground_truth": None,
        f"{sut}_correct": 0,
        f"{sut}_wrong": 1,
        f"{sut}_evaluation_error": None,
    }
    result.update({f"{sut}_{measure}": 0.0 for measure in POLLOCK_MEASURES})
    return result


def evaluate_single_file(
    filename: str,
    dataset: str,
    sut: str,
    verbose: bool = False,
    n_jobs: int = 1,
    origin_csv: str | None = None,
    row_order_invariant: bool = True,
    nrows: int | None = None,
    result_root: str = "./results",
) -> dict:
    """Calculate soft Pollock metrics and strict correctness for one output."""
    clean_path = f"data/{dataset}/clean/{filename}"
    manifest_path = f"data/{dataset}/ground_truth/{filename}/manifest.json"
    loaded_path = os.path.join(
        result_root, sut, dataset, "loading", f"{filename}_converted.csv"
    )
    result = _empty_result(filename, sut)

    if verbose:
        print(f"'{filename}'")
    if not os.path.exists(loaded_path):
        result[f"{sut}_evaluation_error"] = "missing_output"
        return result

    errors = []
    try:
        success = int(metrics.successful_csv(loaded_path))
        result[f"{sut}_success"] = success
        if success and os.path.exists(manifest_path):
            values, metric_ground_truth = metrics.best_ground_truth_measures(
                manifest_path, loaded_path, n_jobs=n_jobs, nrows=nrows
            )
        elif success:
            values = metrics.header_record_cell_measures_csv(
                clean_path, loaded_path, n_jobs=n_jobs, nrows=nrows
            )
            metric_ground_truth = "legacy_clean"
        else:
            values = (0.0,) * len(SIMILARITY_MEASURES)
            metric_ground_truth = None

        for measure, value in zip(SIMILARITY_MEASURES, values):
            result[f"{sut}_{measure}"] = value
        result[f"{sut}_metric_ground_truth"] = metric_ground_truth
    except Exception:
        errors.append("pollock_metrics: " + traceback.format_exc().strip())

    try:
        if os.path.exists(manifest_path):
            correct, strict_ground_truth = metrics.compare_ground_truths(
                manifest_path,
                loaded_path,
                n_jobs=n_jobs,
                origin_csv=origin_csv,
                row_order_invariant=row_order_invariant,
                nrows=nrows,
            )
        else:
            correct = metrics.compare_files(
                clean_path,
                loaded_path,
                n_jobs=n_jobs,
                origin_csv=origin_csv,
                row_order_invariant=row_order_invariant,
                nrows=nrows,
            )
            strict_ground_truth = "legacy_clean" if correct else None

        result[f"{sut}_correct"] = int(correct)
        result[f"{sut}_wrong"] = int(not correct)
        result[f"{sut}_strict_ground_truth"] = strict_ground_truth
        # Backwards-compatible alias used by existing strict-result consumers.
        result[f"{sut}_matched_ground_truth"] = strict_ground_truth
    except Exception:
        errors.append("strict_metrics: " + traceback.format_exc().strip())

    if errors:
        result[f"{sut}_evaluation_error"] = "\n".join(errors)
        if not verbose:
            print(f"Evaluation error on file: {filename}")
    return result


def evaluate_files(
    files: Iterable[str],
    dataset: str,
    sut: str,
    result_file: str,
    verbose: bool = False,
    n_jobs: int = 1,
    origin_csv: str | None = None,
    row_order_invariant: bool = True,
    nrows: int | None = None,
    result_root: str = "./results",
) -> pd.DataFrame:
    """Evaluate files once and write the combined per-file result table."""
    files = list(files)
    effective_jobs = max(1, min(int(n_jobs), os.cpu_count() or 1))
    common = {
        "dataset": dataset,
        "sut": sut,
        "verbose": verbose,
        "origin_csv": origin_csv,
        "row_order_invariant": row_order_invariant,
        "nrows": nrows,
        "result_root": result_root,
    }

    if effective_jobs == 1:
        rows = []
        for index, filename in enumerate(files):
            if index % max(1, len(files) // 10) == 0:
                print(f"  {index}/{len(files)} files...")
            rows.append(evaluate_single_file(filename=filename, n_jobs=1, **common))
        print(f"  {len(files)}/{len(files)} files done.")
    else:
        small = [
            filename
            for filename in files
            if os.path.getsize(f"data/{dataset}/csv/{filename}") < 500 * 1024
        ]
        small_set = set(small)
        large = [filename for filename in files if filename not in small_set]
        arguments = [
            {"filename": filename, "n_jobs": 1, **common} for filename in small
        ]
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=r"This process .* is multi-threaded"
            )
            rows = pqdm(
                arguments,
                evaluate_single_file,
                n_jobs=effective_jobs,
                argument_type="kwargs",
            )

        for index, filename in enumerate(large, 1):
            print(f"  [{index}/{len(large)} large files] {filename}")
            rows.append(
                evaluate_single_file(
                    filename=filename, n_jobs=effective_jobs, **common
                )
            )

    frame = pd.DataFrame(rows)
    frame.to_csv(result_file, index=False)
    return frame


def aggregate_system(
    frame: pd.DataFrame,
    sut: str,
    dataset: str,
    weights: dict[str, float] | None = None,
) -> dict:
    """Aggregate one SUT's combined per-file results."""
    weights = weights or {}
    aggregate = {
        measure: float(frame[f"{sut}_{measure}"].mean())
        for measure in POLLOCK_MEASURES
    }
    aggregate["pollock_simple"] = sum(aggregate[m] for m in POLLOCK_MEASURES)
    aggregate["correct"] = int(frame[f"{sut}_correct"].sum())
    aggregate["wrong"] = int(frame[f"{sut}_wrong"].sum())
    aggregate["accuracy"] = (
        aggregate["correct"] / len(frame) if len(frame) else 0.0
    )

    row_weights = [float(weights.get(name, 1.0)) for name in frame["file"]]
    total_weight = sum(row_weights)
    aggregate["weighted_accuracy"] = (
        sum(
            weight * int(correct)
            for weight, correct in zip(row_weights, frame[f"{sut}_correct"])
        )
        / total_weight
        if total_weight
        else 0.0
    )
    aggregate["pollock_weighted"] = (
        sum(
            weight
            * sum(float(row[f"{sut}_{measure}"]) for measure in POLLOCK_MEASURES)
            for weight, (_, row) in zip(row_weights, frame.iterrows())
        )
        / total_weight
        if total_weight
        else 0.0
    )
    aggregate["score"] = aggregate["correct"]

    if dataset == "polluted_files":
        for subset, pattern in SUB_MEASURES.items():
            selected = frame[
                frame["file"].map(lambda name: bool(re.search(pattern, name)))
            ]
            for measure in ("success", "header_f1", "record_f1", "cell_f1"):
                aggregate[f"{subset}_{measure}"] = float(
                    selected[f"{sut}_{measure}"].mean()
                )

    return aggregate
