"""Unified strict and Pollock-style evaluator."""

from __future__ import annotations

import argparse
import os
import warnings

import pandas as pd
from dotenv import load_dotenv

from evaluate_utils import (
    POLLOCK_MEASURES,
    aggregate_system,
    evaluate_files,
    evaluate_single_file,
    load_weights,
    result_suffix,
)
from sut.utils import print

load_dotenv()

SUT_ORDER = [
    "clevercs", "csvcommons", "opencsv", "pandas", "duckdbparse",
    "duckdbauto", "pycsv", "rcsv", "univocity", "mysql", "postgres", "sqlite",
]


def _systems(result_root: str, dataset: str) -> list[str]:
    if not os.path.isdir(result_root):
        return []
    return [
        sut
        for sut in next(os.walk(result_root))[1]
        if sut != "archives"
        and not sut.startswith("_")
        and os.path.isdir(os.path.join(result_root, sut, dataset, "loading"))
    ]


def _compatible(frame: pd.DataFrame, sut: str) -> bool:
    required = {
        f"{sut}_correct",
        f"{sut}_wrong",
        *(f"{sut}_{measure}" for measure in POLLOCK_MEASURES),
    }
    return required.issubset(frame.columns)


def main(default_dataset: str = "polluted_files") -> None:
    parser = argparse.ArgumentParser(
        description="Calculate Pollock similarity metrics and strict accuracy together."
    )
    parser.add_argument("--sut", default=None)
    parser.add_argument("--dataset", default=default_dataset)
    parser.add_argument("--result", default="./results")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--njobs", default=100, type=int)
    parser.add_argument("--origin-csv", default=None)
    parser.add_argument("--nrows", type=int, default=None)
    parser.add_argument("--use-origin-csv", action="store_true", default=False)
    parser.add_argument(
        "--no-row-order-invariant",
        dest="row_order_invariant",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "--cached-only",
        action="store_true",
        default=False,
        help="Aggregate existing combined result files without recomputing.",
    )
    args = parser.parse_args()

    if args.nrows is not None and args.nrows < 0:
        parser.error("--nrows must be non-negative or omitted")

    origin_csv = args.origin_csv
    if origin_csv is None and args.use_origin_csv:
        for candidate in (
            f"data/{args.dataset}/csv/source.csv",
            f"data/{args.dataset}/source.csv",
            "data/polluted_files/csv/source.csv",
            "data/polluted_files/source.csv",
        ):
            if os.path.exists(candidate):
                origin_csv = candidate
                break

    systems = _systems(args.result, args.dataset)
    if args.sut is not None and args.sut not in systems:
        parser.error(
            f"no loading results found for SUT {args.sut!r} "
            f"and dataset {args.dataset!r}"
        )
    selected_systems = systems if args.sut is None else [args.sut]
    files = sorted(
        filename
        for filename in os.listdir(f"data/{args.dataset}/csv")
        if filename.endswith(".csv")
    )
    suffix = result_suffix(origin_csv, args.row_order_invariant)
    weights = load_weights(args.dataset)
    aggregate_rows = []
    system_frames = []

    for sut in systems:
        result_file = os.path.join(
            args.result, sut, args.dataset, f"{sut}_results{suffix}.csv"
        )
        if not args.cached_only and sut in selected_systems:
            position = selected_systems.index(sut) + 1
            print(f"\n[{position}/{len(selected_systems)}] Evaluating {sut}...")
            frame = evaluate_files(
                files,
                args.dataset,
                sut,
                result_file,
                verbose=args.verbose,
                n_jobs=args.njobs,
                origin_csv=origin_csv,
                row_order_invariant=args.row_order_invariant,
                nrows=args.nrows,
                result_root=args.result,
            )
        elif os.path.exists(result_file):
            frame = pd.read_csv(result_file)
        else:
            continue

        if not _compatible(frame, sut):
            print(
                f"Skipping {sut}: cached results do not contain unified metrics. "
                f"Rerun evaluate.py --dataset {args.dataset} --sut {sut}."
            )
            continue
        aggregate_rows.append(
            {"sut": sut, **aggregate_system(frame, sut, args.dataset, weights)}
        )
        system_frames.append(frame.set_index("file"))

    if not aggregate_rows:
        print("No compatible result files found.")
        return

    aggregate = pd.DataFrame(aggregate_rows).set_index("sut")
    base = pd.DataFrame({"file": files}).set_index("file")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
        global_frame = pd.concat([base] + system_frames, axis=1).copy()

    ordered = [sut for sut in SUT_ORDER if sut in aggregate.index]
    ordered.extend(sut for sut in aggregate.index if sut not in SUT_ORDER)
    display_columns = [
        "pollock_simple", "pollock_weighted", "cell_f1", "record_f1",
        "header_f1", "accuracy", "weighted_accuracy", "correct", "wrong",
    ]
    print(
        "\n",
        aggregate.loc[ordered, display_columns].sort_values(
            "accuracy", ascending=False
        ),
    )

    global_frame.to_csv(
        os.path.join(args.result, f"evaluation_by_file_{args.dataset}{suffix}.csv")
    )
    aggregate.to_csv(
        os.path.join(args.result, f"evaluation_summary_{args.dataset}{suffix}.csv")
    )


if __name__ == "__main__":
    main()
