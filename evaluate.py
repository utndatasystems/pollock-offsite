from __future__ import print_function
import builtins as __builtin__
import os
import argparse
import traceback
import json
import re
import warnings

from pqdm.processes import pqdm
import pandas as pd

from typing import List

import pollock.metrics as metrics
from sut.utils import print

from dotenv import load_dotenv
load_dotenv()


SUT_ORDER = ["clevercs", "csvcommons", "rhypoparsr", 
            "opencsv", "pandas", "duckdbparse","duckdbauto", "pycsv", "rcsv", "univocity", 
            "mariadb", "mysql", "postgres", "sqlite", "libreoffice", 
            "spreaddesktop", "spreadweb", "dataviz"]


def load_weights(dataset: str):
    if dataset != "polluted_files":
        return {}
    weights_path = "pollock_weights.json"
    if not os.path.exists(weights_path):
        return {}
    with open(weights_path) as f:
        return json.load(f)


def add_scores(results_df: pd.DataFrame, sut: str, weights: dict):
    correct_col = f"{sut}_correct"
    if correct_col not in results_df.columns:
        return results_df

    total_files = len(results_df)
    correct_count = results_df[correct_col].astype(int).sum()
    score_10 = 0.0 if total_files == 0 else 10.0 * correct_count / total_files

    if weights:
        total_weight = sum(float(weights.get(filename, 1.0)) for filename in results_df["file"])
        weighted_correct = sum(
            float(weights.get(filename, 1.0)) * int(correct)
            for filename, correct in zip(results_df["file"], results_df[correct_col])
        )
        weighted_score_10 = 0.0 if total_weight == 0 else 10.0 * weighted_correct / total_weight
    else:
        weighted_score_10 = score_10

    results_df.attrs["score_10"] = score_10
    results_df.attrs["weighted_score_10"] = weighted_score_10
    return results_df

def evaluate_single_file(filename:str, dataset:str, sut:str, verbose=False, n_jobs=1, origin_csv=None):
    sut_dir = f"results/{sut}/{dataset}/loading/"
    # Each converted result is compared against the canonical clean CSV with
    # the same filename. The original polluted input lives in data/.../csv/.
    clean_path = f"data/{dataset}/clean/{filename}"
    loaded_path = f"{sut_dir}{filename}_converted.csv"

    dict_measures = {"file": filename}
    if verbose:
        print(f"'{filename}'")
    if not os.path.exists(loaded_path):
        __builtin__.print(f"[{filename}] wrong")
        dict_measures[sut + "_correct"] = 0
        dict_measures[sut + "_wrong"] = 1
        return dict_measures
    try:
        correct = metrics.alex_compare(clean_path, loaded_path, n_jobs, origin_csv=origin_csv)
        dict_measures[sut + "_correct"] = correct
        dict_measures[sut + "_wrong"] = not correct
    except Exception as e:
        print("Exception:", traceback.format_exc())
        if not verbose:
            print("On file:", filename)
        __builtin__.print(f"[{filename}] wrong")
        dict_measures[sut + "_correct"] = False
        dict_measures[sut + "_wrong"] = True

    return dict_measures


def evaluate_single_run(files: List[str], dataset: str, result_file:str, sut:str, verbose=False, n_jobs=1, origin_csv=None):
    effective_jobs = max(1, min(int(n_jobs), os.cpu_count() or 1))

    if effective_jobs == 1:
        file_measures = []
        n = len(files)
        for i, f in enumerate(files):
            if i % max(1, n // 10) == 0:
                print(f"  {i}/{n} files...")
            file_measures.append(evaluate_single_file(filename=f, dataset=dataset, sut=sut, verbose=verbose, origin_csv=origin_csv))
        print(f"  {n}/{n} files done.")
    # parallel
    else:
        args = [{"filename": f, "dataset": dataset, "sut": sut, "verbose": verbose, "origin_csv": origin_csv} for f in files]
        file_measures = pqdm(args, evaluate_single_file, n_jobs=effective_jobs, argument_type="kwargs")
    results_df = pd.DataFrame(file_measures)
    results_df.to_csv(result_file, index=False)
    if verbose: print(results_df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sut", default=None, help="The single system to benchmark, if not running the evaluation for all of them")
    parser.add_argument("--dataset", default="polluted_files", help="The dataset containing the input CSV files")
    parser.add_argument("--result", default="./results", help="The root path where the results of the loading are")
    parser.add_argument("--verbose", default=False, help="Whether to print filenames as they are processed")
    parser.add_argument("--njobs", default=100, help="The number of jobs to parallelize the computation")
    parser.add_argument("--origin-csv", default=None,
                        help="Pre-pollution source CSV; a cell is accepted if it matches either "
                             "the clean value or this origin value (default: data/{dataset}/source.csv if it exists)")

    args = parser.parse_args()
    UPDATE_SYSTEM = args.sut
    dataset = args.dataset
    RESULT_DIR = args.result
    N_JOBS = int(args.njobs)

    origin_csv = args.origin_csv
    if origin_csv is None:
        for candidate in [f"data/{dataset}/source.csv", "data/polluted_files/source.csv"]:
            if os.path.exists(candidate):
                origin_csv = candidate
                break
    weights = load_weights(dataset)

    verbose = bool(args.verbose)
    systems = [s for s in next(os.walk(f"{RESULT_DIR}"))[1]
               if s != "archives" and os.path.isdir(f"{RESULT_DIR}/{s}/{dataset}/loading")]

    sut_dirs = {s for s in os.listdir("sut") if os.path.isdir(f"sut/{s}") and not s.startswith("_")}
    no_results = sorted(sut_dirs - set(systems))
    if no_results:
        print(f"Warning: {len(no_results)} SUT(s) in sut/ have no results for dataset '{dataset}': {no_results}")

    files= [f for f in os.listdir(f"data/{dataset}/csv") if f.endswith("csv")]
    aggregate = []
    global_df = pd.DataFrame({"file": files})
    eval_systems = systems if UPDATE_SYSTEM is None else [s for s in systems if s == UPDATE_SYSTEM]

    

    for s in systems:
        result_file = f"{RESULT_DIR}/{s}/{dataset}/{s}_results.csv"
        if UPDATE_SYSTEM is None or s == UPDATE_SYSTEM:
            print(f"\n[{eval_systems.index(s) + 1}/{len(eval_systems)}] Evaluating {s}...")
            evaluate_single_run(files=files, dataset=dataset, result_file=result_file, sut=s, n_jobs=N_JOBS, verbose=verbose, origin_csv=origin_csv)
        if not os.path.exists(result_file):
            continue
        df = pd.read_csv(result_file)
        expected_cols = {f"{s}_correct", f"{s}_wrong"}
        if not expected_cols.issubset(df.columns):
            print(f"Skipping {s}: result file uses old scoring columns. Rerun evaluate.py --sut {s} to update it.")
            continue
        df = add_scores(df, s, weights)
        d_aggregate = {"".join(key.split("_")[1:]): val for key, val in df.sum(axis=0, numeric_only=True).items()}
        d_aggregate["score_10"] = df.attrs["score_10"]
        d_aggregate["weighted_score_10"] = df.attrs["weighted_score_10"]
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
    present = [s for s in SUT_ORDER if s in aggregate_df.index]
    extra = [s for s in aggregate_df.index if s not in SUT_ORDER]
    missing = [s for s in SUT_ORDER if s not in aggregate_df.index]
    if missing:
        print(f"Note: {len(missing)} SUT(s) from SUT_ORDER not in results and skipped: {missing}")
    if extra:
        print(f"Note: {len(extra)} SUT(s) not in SUT_ORDER, appended: {extra}")
        present += extra
    print(
        "\n",
        aggregate_df.loc[present][["score", "score_10", "weighted_score_10", "correct", "wrong"]]
        .sort_values("score_10", ascending=False)
    )

    global_df.to_csv(RESULT_DIR + f"/global_results_{dataset}.csv")
    aggregate_df.to_csv(RESULT_DIR + f"/aggregate_results_{dataset}.csv")

if __name__ == "__main__":
    main()
