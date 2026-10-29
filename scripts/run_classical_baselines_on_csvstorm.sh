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
#   --run-id ID        Name this isolated run (default: UTC timestamp + commit).
#   --resume ID        Continue an interrupted run with matching inputs/settings.
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
run_id=""
resume=false

usage() {
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } /^$/ { print; next } { exit }' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --regenerate)
            regenerate=true
            ;;
        --run-id)
            run_id="${2:?--run-id requires an ID}"
            shift
            ;;
        --resume)
            run_id="${2:?--resume requires an ID}"
            resume=true
            shift
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

if [[ "$resume" == true && "$regenerate" == true ]]; then
    echo "Error: --regenerate cannot be used with --resume."
    exit 2
fi

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        python_bin=".venv/bin/python"
    else
        python_bin="python3"
    fi
fi

dataset="csv_storm"
dataset_seed=1337

if [[ -z "$run_id" ]]; then
    run_id="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short=8 HEAD)"
fi
"$python_bin" scripts/experiment_run.py check-clean

if [[ "$regenerate" == true ]]; then
    echo "=== Regenerating data/$dataset with CSV Storm ==="
    "$python_bin" pollute_main.py \
        --source ./results/source.csv \
        --output "./data/$dataset" \
        --polluters csv_storm \
        --combinations \
        --rng-seed "$dataset_seed" \
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

manifest_args=(
    init --run-id "$run_id" --script classical --dataset "$dataset"
    --seed "$dataset_seed" --suts "duckdbauto_strict duckdbparse pandas clevercs pycsv"
    --repetitions "${N_REPETITIONS:-3}" --eval-njobs "${EVAL_NJOBS:-1}"
    --cache-policy none
)
if [[ "$resume" == true ]]; then
    manifest_args+=(--resume)
fi
export RESULT_ROOT
RESULT_ROOT="$("$python_bin" scripts/experiment_run.py "${manifest_args[@]}")"

finish_run() {
    local exit_code="$1"
    local status=complete
    trap - EXIT
    if [[ "$exit_code" -ne 0 ]]; then
        status=failed
    fi
    "$python_bin" scripts/experiment_run.py finish \
        --run-id "$run_id" --status "$status" --exit-code "$exit_code" || exit 1
    exit "$exit_code"
}
trap 'finish_run "$?"' EXIT

export DATASET="$dataset"

evaluate_sut() {
    local sut="$1"

    echo
    echo "=== Evaluating $sut on $dataset ==="
    "$python_bin" evaluate.py \
        --dataset "$dataset" \
        --result "$RESULT_ROOT" \
        --sut "$sut" \
        --njobs "${EVAL_NJOBS:-1}"
    "$python_bin" scripts/experiment_run.py mark-sut --run-id "$run_id" --sut "$sut"
}

run_classical_sut() {
    local label="$1"
    local sut="$2"
    local script="$3"
    shift 3

    echo
    echo "=== $label on $dataset ==="
    "$python_bin" "$script" "$@"
    evaluate_sut "$sut"
}

echo "=== Configuration ==="
echo "Run ID:        $run_id"
echo "Result root:   $RESULT_ROOT"
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
echo "  $RESULT_ROOT/evaluation_summary_${dataset}.csv"
echo "  $RESULT_ROOT/evaluation_by_file_${dataset}.csv"
echo
echo "Per-SUT outputs are under $RESULT_ROOT/<sut>/$dataset/."
