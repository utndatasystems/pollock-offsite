"""
Closed-loop scoring primitive for an extended-pollution engine.

Given a dataset name (e.g. `extended_unicode`), this script:

  1. Runs the four Python SuTs (duckdbparse, duckdbauto, pandas, pycsv) on it.
     Each SuT writes to results/<sut>/<dataset>/loading/.
     N_REPETITIONS=1 by default for fast iteration.

  2. Runs evaluate.py on the dataset for those SuTs.
     evaluate.py writes results/global_results_<dataset>.csv with per-file
     metrics for every SuT that has loaded results.

  3. Loads the global results and emits a summary JSON to stdout (or --out)
     describing, for each Python SuT, the worst N pollutions by cell_f1 and
     by header_f1.

Output JSON shape:
    {
      "dataset": "extended_unicode",
      "n_files": 47,
      "summary": {
        "duckdbparse": {"mean_cell_f1": 0.91, "mean_success": 0.98, ...},
        "duckdbauto":  {...},
        "pandas":      {...},
        "pycsv":       {...}
      },
      "worst_per_sut": {
        "duckdbparse": [
          {"file": "unicode_bom_utf16.csv", "cell_f1": 0.12, "header_f1": 0.0,
           "record_f1": 0.05, "success": 1.0},
          ...
        ],
        ...
      }
    }

Usage from the repo root:

    python3 scripts/score_engine.py --dataset extended_unicode --top-n 15

Skip SuT execution (re-score only) with --skip-suts.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Optional

import pandas as pd


PYTHON_SUTS = ["duckdbparse", "duckdbauto", "pandas", "pycsv"]
SUT_SCRIPT = {
    "duckdbparse": "sut/duckdbparse/duck-bench.py",
    "duckdbauto": "sut/duckdbauto/duck-bench.py",
    "pandas": "sut/pandas/panda.py",
    "pycsv": "sut/pycsv/pycsv.py",
}


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_sut(sut: str, dataset: str, n_reps: int) -> None:
    """Run a single Python SuT against the given dataset.

    Honors per-file early-exit in each SuT (skip if loaded output exists),
    so re-runs are cheap.
    """
    env = dict(os.environ)
    env["DATASET"] = dataset
    env["N_REPETITIONS"] = str(n_reps)
    cmd = [sys.executable, SUT_SCRIPT[sut]]
    proc = subprocess.run(cmd, cwd=repo_root(), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    if proc.returncode != 0:
        # Still try to score what's there, but warn loudly.
        sys.stderr.write(f"[score_engine] {sut} exit {proc.returncode}\n")
        sys.stderr.write(proc.stdout[-2000:])
        sys.stderr.write("\n")


def run_evaluate(dataset: str, suts: list, n_jobs: int) -> None:
    for sut in suts:
        # Drop stale per-file results so evaluate.py recomputes.
        rfile = f"{repo_root()}/results/{sut}/{dataset}/{sut}_results.csv"
        if os.path.exists(rfile):
            os.remove(rfile)
    # evaluate.py iterates over all SuTs that have a loading dir for this
    # dataset; running it once per dataset is enough.
    cmd = [sys.executable, "evaluate.py", "--dataset", dataset, "--njobs", str(n_jobs)]
    proc = subprocess.run(cmd, cwd=repo_root(),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    if proc.returncode != 0:
        sys.stderr.write(f"[score_engine] evaluate.py exit {proc.returncode}\n")
        sys.stderr.write(proc.stdout[-4000:])
        sys.stderr.write("\n")


def summarize(dataset: str, top_n: int) -> dict:
    global_path = f"{repo_root()}/results/global_results_{dataset}.csv"
    if not os.path.exists(global_path):
        return {"dataset": dataset, "n_files": 0, "summary": {}, "worst_per_sut": {},
                "error": f"global_results_{dataset}.csv not found at {global_path}"}
    df = pd.read_csv(global_path)
    if "file" not in df.columns:
        df = df.rename(columns={df.columns[0]: "file"})
    df = df.set_index("file")

    summary = {}
    worst = {}
    for sut in PYTHON_SUTS:
        cols = [c for c in df.columns if c.startswith(f"{sut}_")]
        if not cols:
            continue
        sub = df[cols].copy()
        means = {c.replace(f"{sut}_", ""): float(sub[c].mean(skipna=True))
                 for c in cols}
        summary[sut] = means

        sort_col = f"{sut}_cell_f1"
        if sort_col not in sub.columns:
            continue
        bad = sub.sort_values(sort_col, ascending=True).head(top_n)
        bad_records = []
        for fname, row in bad.iterrows():
            bad_records.append({
                "file": fname,
                "cell_f1": float(row.get(f"{sut}_cell_f1", 0.0) or 0.0),
                "header_f1": float(row.get(f"{sut}_header_f1", 0.0) or 0.0),
                "record_f1": float(row.get(f"{sut}_record_f1", 0.0) or 0.0),
                "success": float(row.get(f"{sut}_success", 0.0) or 0.0),
            })
        worst[sut] = bad_records

    return {
        "dataset": dataset,
        "n_files": len(df),
        "summary": summary,
        "worst_per_sut": worst,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--suts", nargs="+", default=PYTHON_SUTS,
                   help="Subset of Python SuTs to run")
    p.add_argument("--top-n", type=int, default=15,
                   help="Worst-N pollutions per SuT to report")
    p.add_argument("--n-reps", type=int, default=1,
                   help="N_REPETITIONS env var for SuT runs")
    p.add_argument("--n-jobs", type=int, default=8,
                   help="--njobs for evaluate.py")
    p.add_argument("--skip-suts", action="store_true",
                   help="Skip SuT execution, only re-evaluate existing loadings")
    p.add_argument("--purge-loadings", action="store_true",
                   help="Delete results/<sut>/<dataset>/loading/ before running, forcing a clean re-run")
    p.add_argument("--out", default=None,
                   help="Write JSON summary to this path (also printed to stdout)")
    args = p.parse_args()

    suts = [s for s in args.suts if s in SUT_SCRIPT]
    if args.purge_loadings:
        for sut in suts:
            d = f"{repo_root()}/results/{sut}/{args.dataset}/loading"
            if os.path.isdir(d):
                shutil.rmtree(d)

    if not args.skip_suts:
        for sut in suts:
            run_sut(sut, args.dataset, args.n_reps)

    run_evaluate(args.dataset, suts, args.n_jobs)
    summary = summarize(args.dataset, args.top_n)

    text = json.dumps(summary, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
