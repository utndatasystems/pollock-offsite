#!/usr/bin/env bash
# Run the classical (non-LLM) parser baselines against CSV Storm.
#
# This is the no-cost counterpart to run_full_benchmark_on_csvstorm.sh: it makes
# no LLM calls and needs no API key.
#
# Usage:
#   scripts/run_classical_baselines_on_csvstorm.sh [options]
#
# Options:
#   --regenerate       Recreate data/csv_storm with CSV Storm polluters first.
#   --keep-results     Keep existing parser outputs instead of overwriting them.
#   -h, --help         Show this help.
#
# Environment:
#   PYTHON             Optional Python interpreter override.
#   EVAL_NJOBS         Evaluation workers, default 1.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f ".env" ]]; then
    set -o allexport
    source .env
    set +o allexport
fi

regenerate=false
overwrite_results=true

usage() {
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --regenerate)
            regenerate=true
            ;;
        --keep-results)
            overwrite_results=false
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option: $1"
            usage
            exit 2
            ;;
    esac
    shift
done

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        python_bin=".venv/bin/python"
    else
        python_bin="python3"
    fi
fi

dataset="csv_storm"

if [[ "$regenerate" == true ]]; then
    echo "=== Regenerating data/$dataset with CSV Storm ==="
    "$python_bin" pollute_main.py \
        --source ./results/source.csv \
        --output "./data/$dataset" \
        --polluters csv_storm \
        --combinations \
        --rng-seed 1337 \
        --overwrite
fi

if [[ ! -d "data/$dataset/csv" || ! -d "data/$dataset/clean" ]]; then
    echo "Error: data/$dataset must contain csv/ and clean/ directories."
    exit 1
fi
if [[ ! -d "data/$dataset/ground_truth" ]]; then
    echo "Error: data/$dataset/ground_truth does not exist."
    echo "Rerun with --regenerate to create the current ground-truth layout."
    exit 1
fi

export DATASET="$dataset"

classical_overwrite_args=()
if [[ "$overwrite_results" == true ]]; then
    classical_overwrite_args+=(--overwrite)
fi

evaluate_sut() {
    local sut="$1"

    echo
    echo "=== Evaluating $sut on $dataset ==="
    "$python_bin" evaluate.py \
        --dataset "$dataset" \
        --sut "$sut" \
        --njobs "${EVAL_NJOBS:-1}"
}

run_classical_sut() {
    local label="$1"
    local sut="$2"
    local script="$3"
    shift 3

    echo
    echo "=== $label on $dataset ==="
    "$python_bin" "$script" "$@" "${classical_overwrite_args[@]}"
    evaluate_sut "$sut"
}

echo "=== Configuration ==="
echo "Dataset:       $dataset"
echo "SUTs:          duckdbauto_strict duckdbparse pandas clevercs pycsv"
echo "Python:        $python_bin"
echo "LLM calls:     none"

run_classical_sut "DuckDB Auto" "duckdbauto_strict" "sut/duckdbauto/duck-bench.py" --strict
run_classical_sut "DuckDB Explicit" "duckdbparse" "sut/duckdbparse/duck-bench.py"
run_classical_sut "pandas" "pandas" "sut/pandas/panda.py"
run_classical_sut "CleverCSV" "clevercs" "sut/clevercs/clevercs.py"
run_classical_sut "Python CSV" "pycsv" "sut/pycsv/pycsv.py"

echo
echo "=== Classical baselines complete ==="
echo "Dataset-level summaries:"
echo "  results/evaluation_summary_${dataset}.csv"
echo "  results/evaluation_by_file_${dataset}.csv"
echo
echo "Per-SUT outputs are under results/<sut>/$dataset/."
