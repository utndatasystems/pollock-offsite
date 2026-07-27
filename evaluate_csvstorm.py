from __future__ import print_function
import builtins as __builtin__
import os
import argparse
import traceback
import re
import warnings

from pqdm.processes import pqdm
import pandas as pd

from typing import List

import pollock.metrics as metrics
from sut.utils import print

from dotenv import load_dotenv
load_dotenv()


def add_scores(results_df: pd.DataFrame, sut: str):
    correct_col = f"{sut}_correct"
    if correct_col not in results_df.columns:
        return results_df

    total_files = len(results_df)
    correct_count = results_df[correct_col].astype(int).sum()
    results_df.attrs["accuracy"] = 0.0 if total_files == 0 else correct_count / total_files
    return results_df

def evaluate_single_file(filename:str, dataset:str, sut:str, verbose=False, n_jobs=1, origin_csv=None, row_order_invariant=False, nrows=None):
    sut_dir = f"results/{sut}/{dataset}/loading/"
    # Each converted result is compared against the canonical clean CSV with
    # the same filename. The original polluted input lives in data/.../csv/.
    clean_path = f"data/{dataset}/clean/{filename}"
    ground_truth_manifest = f"data/{dataset}/ground_truth/{filename}/manifest.json"
    loaded_path = f"{sut_dir}{filename}_converted.csv"

    dict_measures = {"file": filename, sut + "_matched_ground_truth": None}
    if verbose:
        print(f"'{filename}'")
    if not os.path.exists(loaded_path):
        dict_measures[sut + "_correct"] = 0
        dict_measures[sut + "_wrong"] = 1
        return dict_measures
    try:
        if os.path.exists(ground_truth_manifest):
            correct, matched_ground_truth = metrics.compare_ground_truths(
                ground_truth_manifest,
                loaded_path,
                n_jobs,
                origin_csv=origin_csv,
                row_order_invariant=row_order_invariant,
                nrows=nrows,
            )
        else:
            correct = metrics.compare_files(
                clean_path,
                loaded_path,
                n_jobs,
                origin_csv=origin_csv,
                row_order_invariant=row_order_invariant,
                nrows=nrows,
            )
            matched_ground_truth = "legacy_clean" if correct else None
        dict_measures[sut + "_correct"] = int(correct)
        dict_measures[sut + "_wrong"] = int(not correct)
        dict_measures[sut + "_matched_ground_truth"] = matched_ground_truth
    except Exception as e:
        print("Exception:", traceback.format_exc())
        if not verbose:
            print("On file:", filename)
        dict_measures[sut + "_correct"] = 0
        dict_measures[sut + "_wrong"] = 1

    return dict_measures


def evaluate_single_run(files: List[str], dataset: str, result_file:str, sut:str, verbose=False, n_jobs=1, origin_csv=None, row_order_invariant=False, nrows=None):
    effective_jobs = max(1, min(int(n_jobs), os.cpu_count() or 1))

    if effective_jobs == 1:
        file_measures = []
        n = len(files)
        for i, f in enumerate(files):
            if i % max(1, n // 10) == 0:
                print(f"  {i}/{n} files...")
            file_measures.append(evaluate_single_file(filename=f, dataset=dataset, sut=sut, verbose=verbose, origin_csv=origin_csv, row_order_invariant=row_order_invariant, nrows=nrows))
        print(f"  {n}/{n} files done.")
    # parallel
    else:
        args = [{"filename": f, "dataset": dataset, "sut": sut, "verbose": verbose, "origin_csv": origin_csv, "row_order_invariant": row_order_invariant, "nrows": nrows} for f in files]
        # fork() in a multi-threaded parent triggers a DeprecationWarning on Py3.12; silence it at fork time
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"This process .* is multi-threaded")
            file_measures = pqdm(args, evaluate_single_file, n_jobs=effective_jobs, argument_type="kwargs")
    results_df = pd.DataFrame(file_measures)
    results_df.to_csv(result_file, index=False)
    if verbose: print(results_df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sut", default=None, help="The single system to benchmark, if not running the evaluation for all of them")
    parser.add_argument("--dataset", default="csv_storm", help="The dataset containing the input CSV files")
    parser.add_argument("--result", default="./results", help="The root path where the results of the loading are")
    parser.add_argument("--verbose", action="store_true", help="Whether to print filenames as they are processed")
    parser.add_argument("--njobs", default=100, help="The number of jobs to parallelize the computation")
    parser.add_argument("--origin-csv", default=None,
                        help="Pre-pollution source CSV; a cell is accepted if it matches either "
                             "the clean value or this origin value")
    parser.add_argument("--nrows", type=int, default=None,
                        help="Compare only the first N data rows after the header when evaluating correctness")
    parser.add_argument("--use-origin-csv", action="store_true", default=False,
                        help="Auto-detect and use data/{dataset}/csv/source.csv as origin fallback (default: off)")
    parser.add_argument("--no-row-order-invariant", dest="row_order_invariant",
                        action="store_false", default=True,
                        help="Disable row-order invariance and require the loaded rows in the exact "
                             "clean order (invariant is on by default)")
    parser.add_argument("--cached-only", action="store_true", default=False,
                        help="Only read existing *_results.csv files and aggregate; do not recompute "
                             "any scores. Lets you show the full previously-computed results even if "
                             "data/<dataset>/csv is incomplete (ignores --sut).")

    args = parser.parse_args()
    UPDATE_SYSTEM = args.sut
    CACHED_ONLY = args.cached_only
    dataset = args.dataset
    RESULT_DIR = args.result
    N_JOBS = int(args.njobs)
    NROWS = args.nrows

    if NROWS is not None and NROWS < 0:
        parser.error("--nrows must be non-negative or omitted")

    origin_csv = args.origin_csv
    if origin_csv is None and args.use_origin_csv:
        for candidate in [
            f"data/{dataset}/csv/source.csv",
            f"data/{dataset}/source.csv",
            "data/polluted_files/csv/source.csv",
            "data/polluted_files/source.csv",
        ]:
            if os.path.exists(candidate):
                origin_csv = candidate
                break
    row_order_invariant = bool(args.row_order_invariant)
    suffix = ("_incl_origin" if origin_csv is not None else "") + ("" if row_order_invariant else "_no_row_order_invariance")

    verbose = bool(args.verbose)
    systems = [s for s in next(os.walk(f"{RESULT_DIR}"))[1]
               if s != "archives" and not s.startswith("_")
               and os.path.isdir(f"{RESULT_DIR}/{s}/{dataset}/loading")]

    files= [f for f in os.listdir(f"data/{dataset}/csv") if f.endswith("csv")]
    aggregate = []
    global_df = pd.DataFrame({"file": files})
    eval_systems = systems if UPDATE_SYSTEM is None else [s for s in systems if s == UPDATE_SYSTEM]

    

    if CACHED_ONLY:
        print("Cached-only mode: reading existing *_results.csv without recomputing.")

    for s in systems:
        result_file = f"{RESULT_DIR}/{s}/{dataset}/{s}_results{suffix}.csv"
        if not CACHED_ONLY and (UPDATE_SYSTEM is None or s == UPDATE_SYSTEM):
            print(f"\n[{eval_systems.index(s) + 1}/{len(eval_systems)}] Evaluating {s}...")
            evaluate_single_run(files=files, dataset=dataset, result_file=result_file, sut=s, n_jobs=N_JOBS, verbose=verbose, origin_csv=origin_csv, row_order_invariant=row_order_invariant, nrows=NROWS)
        if not os.path.exists(result_file):
            continue
        df = pd.read_csv(result_file)
        expected_cols = {f"{s}_correct", f"{s}_wrong"}
        if not expected_cols.issubset(df.columns):
            print(f"Skipping {s}: result file uses old scoring columns. Rerun evaluate.py --sut {s} to update it.")
            continue
        df = add_scores(df, s)
        d_aggregate = {key[len(s)+1:]: val for key, val in df.sum(axis=0, numeric_only=True).items() if key.startswith(f"{s}_")}
        d_aggregate["accuracy"] = df.attrs["accuracy"]
        d_aggregate.update({"sut": s})
        aggregate += [d_aggregate]
        global_df = global_df.merge(df, how="outer", left_on="file", right_on="file")  # , suffixes=(None,"_"+s))
    aggregate_df = pd.DataFrame(aggregate)
    if aggregate_df.empty:
        print("No compatible result files found.")
        return
    aggregate_df.set_index("sut", inplace=True)
    if not aggregate_df.empty:
        aggregate_df["score"] = aggregate_df["correct"]

    global_df.set_index("file", inplace=True)
    print(
        "\n",
        aggregate_df[["score", "accuracy", "correct", "wrong"]]
        .sort_values("accuracy", ascending=False)
    )

    global_df.to_csv(RESULT_DIR + f"/global_results_{dataset}{suffix}.csv")
    aggregate_df.to_csv(RESULT_DIR + f"/aggregate_results_{dataset}{suffix}.csv")

if __name__ == "__main__":
    main()
