"""Print the hybrid parser's accuracy, runtime, and cost rows for the paper table.

Accuracy comes from each run's evaluation summary. Runtimes use the same filter as
the notebook (benchmark_runtime.load_file_runtimes: successful, cold, non-stale
timings; source.csv excluded). Costs are the per-file billable costs recorded in
the time CSV over all files; local models are reported as "Local".

Usage:
    python scripts/hybrid_runtime_cost_table.py RUN_DIR [RUN_DIR ...] [--dataset csv_storm]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from benchmark_runtime import load_file_runtimes


def display_name(model: str) -> str:
    if model.startswith("gpt-"):
        version, _, family = model[4:].partition("-")
        return f"GPT-{version} {family.title()}".strip()
    name, _, size = model.partition(":")
    return f"{name.title()} {size.upper()}".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--dataset", default="csv_storm")
    args = parser.parse_args()

    for run in args.runs:
        summary = pd.read_csv(run / f"evaluation_summary_{args.dataset}.csv").set_index("sut")
        for sut in sorted(summary.index):
            if not (sut.startswith("llm_hybrid_parser_") and sut.endswith("_duckdb")):
                continue
            times = pd.read_csv(run / sut / args.dataset / f"{sut}_time.csv")
            model = times["model"].dropna().unique()
            assert len(model) == 1, f"{sut}: expected one model, got {model}"
            model = model[0]

            runtimes = load_file_runtimes(REPO_ROOT, sut, args.dataset, result_root=run)
            runtimes = runtimes.loc[runtimes["file"] != "source.csv", "runtime_mean_seconds"]

            if model.startswith("qwen"):
                cost = "Local & Local"
            else:
                file_costs = times["billable_cost_usd_0"]
                assert file_costs.notna().all(), f"{sut}: files without recorded cost"
                cost = f"{file_costs.median():.4f} & {file_costs.sum():.4f}"

            print(
                f"{display_name(model)} & {100 * summary.loc[sut, 'accuracy']:.1f} & "
                f"{runtimes.median():.2f} & {runtimes.sum():.2f} & {cost} \\\\"
                f"  % {sut}: {len(runtimes)} timed files"
            )


if __name__ == "__main__":
    main()
