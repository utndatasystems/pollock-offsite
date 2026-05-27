#!/usr/bin/env bash
# Run Python SUTs and evaluation on a web-scraped CSV dataset without
# overwriting prior benchmark data/results.
#
# Usage:
#   scripts/run_web_csv_benchmark.sh [source_dataset] [sut1 sut2 ...]
#
# Examples:
#   scripts/run_web_csv_benchmark.sh web_csv_dump
#   scripts/run_web_csv_benchmark.sh web_csv_poc pandas pycsv clevercs
#
# The script snapshots data/<source_dataset> into a unique run dataset:
#   data/<source_dataset>_run_<timestamp>/
# and writes outputs under:
#   results/<sut>/<source_dataset>_run_<timestamp>/
#   results/global_results_<source_dataset>_run_<timestamp>.csv
#   results/aggregate_results_<source_dataset>_run_<timestamp>.csv

set -euo pipefail

if [[ -f ".env" ]]; then
    set -o allexport
    source .env
    set +o allexport
fi

SOURCE_DATASET="${1:-web_csv_dump}"
if [[ $# -gt 0 ]]; then
    shift
fi

ALL_SUTS=(duckdbauto duckdbparse pandas pycsv clevercs custom)
if [[ $# -gt 0 ]]; then
    SUTS=("$@")
else
    SUTS=("${ALL_SUTS[@]}")
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(pwd)" != "$REPO_ROOT" ]]; then
    echo "Error: run this script from the repo root: cd $REPO_ROOT"
    exit 1
fi

if [[ ! -d "data/$SOURCE_DATASET/csv" ]]; then
    echo "Error: data/$SOURCE_DATASET/csv not found."
    echo "Create it first, for example:"
    echo "  python3 scripts/scraping/scrape_csvs.py --dataset $SOURCE_DATASET"
    exit 1
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
RUN_DATASET="${SOURCE_DATASET}_run_${timestamp}"
RUN_DATA_DIR="data/$RUN_DATASET"

if [[ -e "$RUN_DATA_DIR" ]]; then
    echo "Error: $RUN_DATA_DIR already exists; refusing to overwrite it."
    exit 1
fi

mkdir -p "$RUN_DATA_DIR"
cp -a "data/$SOURCE_DATASET/csv" "$RUN_DATA_DIR/"
cp -a "data/$SOURCE_DATASET/clean" "$RUN_DATA_DIR/"
cp -a "data/$SOURCE_DATASET/parameters" "$RUN_DATA_DIR/"
if [[ -d "data/$SOURCE_DATASET/metadata" ]]; then
    cp -a "data/$SOURCE_DATASET/metadata" "$RUN_DATA_DIR/"
fi

declare -A SUT_SCRIPT=(
    [duckdbauto]="sut/duckdbauto/duck-bench.py"
    [duckdbparse]="sut/duckdbparse/duck-bench.py"
    [pandas]="sut/pandas/panda.py"
    [pycsv]="sut/pycsv/pycsv.py"
    [clevercs]="sut/clevercs/clevercs.py"
    [custom]="sut/custom/custom-bench.py"
)

for sut in "${SUTS[@]}"; do
    if [[ -z "${SUT_SCRIPT[$sut]+_}" ]]; then
        echo "Unknown SUT '$sut'. Valid options: ${!SUT_SCRIPT[*]}"
        exit 1
    fi
done

python_bin="${PYTHON:-python3}"
if [[ -x ".venv/bin/python" && "${PYTHON:-}" == "" ]]; then
    python_bin=".venv/bin/python"
fi

export DATASET="$RUN_DATASET"

echo "Source dataset: data/$SOURCE_DATASET"
echo "Run dataset:    data/$RUN_DATASET"
echo "SUTs:           ${SUTS[*]}"
echo "Python:         $python_bin"

for sut in "${SUTS[@]}"; do
    echo ""
    echo "=== Running $sut on '$RUN_DATASET' ==="
    "$python_bin" "${SUT_SCRIPT[$sut]}"
done

echo ""
echo "=== Evaluating '$RUN_DATASET' ==="
for sut in "${SUTS[@]}"; do
    if [[ -d "results/$sut/$RUN_DATASET/loading" ]]; then
        "$python_bin" evaluate.py --sut "$sut" --dataset "$RUN_DATASET" --njobs 1
    fi
done

echo ""
echo "Done."
echo "Dataset snapshot: data/$RUN_DATASET"
echo "Per-SUT outputs:  results/<sut>/$RUN_DATASET/"
echo "Aggregate CSV:    results/aggregate_results_$RUN_DATASET.csv"
echo "Global CSV:       results/global_results_$RUN_DATASET.csv"
