from __future__ import print_function
import os
import argparse
import traceback

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

def evaluate_single_file(filename:str, dataset:str, sut:str, verbose=False, n_jobs=1):
    sut_dir = f"results/{sut}/{dataset}/loading/"
    clean_path = f"data/{dataset}/clean/{filename}"
    loaded_path = f"{sut_dir}{filename}_converted.csv"

    dict_measures = {"file": filename}
    if verbose:
        print(f"'{filename}'")
    if not os.path.exists(loaded_path):
        dict_measures[sut + "_correct"] = 0
        dict_measures[sut + "_wrong"] = 1
        return dict_measures
    try:
        succ = metrics.successful_csv(loaded_path)
        correct = False
        if succ:
            measures = metrics.header_record_cell_measures_csv(clean_path, loaded_path, n_jobs)
            correct = all(measure == 1 for measure in measures)
        dict_measures[sut + "_correct"] = int(correct)
        dict_measures[sut + "_wrong"] = int(not correct)

    except Exception as e:
        print("Exception:", traceback.format_exc())
        if not verbose:
            print("On file:", filename)
        dict_measures[sut + "_correct"] = 0
        dict_measures[sut + "_wrong"] = 1

    return dict_measures


def evaluate_single_run(files: List[str], dataset: str, result_file:str, sut:str, verbose=False, n_jobs=1):

    if os.cpu_count()< n_jobs:
        file_measures = []
        n = len(files)
        for i, f in enumerate(files):
            if i % max(1, n // 10) == 0:
                print(f"  {i}/{n} files...")
            file_measures.append(evaluate_single_file(filename=f, dataset=dataset, sut=sut, verbose=verbose))
        print(f"  {n}/{n} files done.")
    else:
        tiny_files = [f for f in files if os.path.getsize(f"data/{dataset}/csv/{f}")/ 1024 < 500]
        args = [{"filename" : f, "dataset":dataset, "sut": sut, "verbose": verbose} for f in tiny_files]
        tiny_file_measures = pqdm(args, evaluate_single_file, n_jobs=n_jobs, argument_type="kwargs")

        large_filenames = [f for f in files if os.path.getsize(f"data/{dataset}/csv/{f}")/ 1024 >= 500]
        large_file_measures = []
        if large_filenames:
            print(f"Evaluating {len(large_filenames)} large file(s)...")
        for i, f in enumerate(large_filenames, 1):
            print(f"  [{i}/{len(large_filenames)}] {f}")
            large_file_measures.append(evaluate_single_file(f, dataset, sut, verbose=verbose, n_jobs=n_jobs))

        file_measures = tiny_file_measures+large_file_measures
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

    args = parser.parse_args()
    UPDATE_SYSTEM = args.sut
    dataset = args.dataset
    RESULT_DIR = args.result
    N_JOBS = int(args.njobs)

    verbose = bool(args.verbose)
    systems = [s for s in next(os.walk(f"{RESULT_DIR}"))[1]
               if s != "archives" and os.path.isdir(f"{RESULT_DIR}/{s}/{dataset}/loading")]

    files= [f for f in os.listdir(f"data/{dataset}/csv") if f.endswith("csv")]
    aggregate = []
    global_df = pd.DataFrame({"file": files})
    eval_systems = systems if UPDATE_SYSTEM is None else [s for s in systems if s == UPDATE_SYSTEM]
    for s in systems:
        result_file = f"{RESULT_DIR}/{s}/{dataset}/{s}_results.csv"
        if UPDATE_SYSTEM is None or s == UPDATE_SYSTEM:
            print(f"\n[{eval_systems.index(s) + 1}/{len(eval_systems)}] Evaluating {s}...")
            evaluate_single_run(files=files, dataset=dataset, result_file=result_file, sut=s, n_jobs=N_JOBS, verbose=verbose)
        if not os.path.exists(result_file):
            continue
        df = pd.read_csv(result_file)
        expected_cols = {f"{s}_correct", f"{s}_wrong"}
        if not expected_cols.issubset(df.columns):
            print(f"Skipping {s}: result file uses old scoring columns. Rerun evaluate.py --sut {s} to update it.")
            continue
        d_aggregate = {"".join(key.split("_")[1:]): val for key, val in df.sum(axis=0, numeric_only=True).items()}
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
    print("\n", aggregate_df.loc[present][["score", "correct", "wrong"]].sort_values("score", ascending=False))

    global_df.to_csv(RESULT_DIR + f"/global_results_{dataset}.csv")
    aggregate_df.to_csv(RESULT_DIR + f"/aggregate_results_{dataset}.csv")

if __name__ == "__main__":
    main()
