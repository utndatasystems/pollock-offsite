#!/usr/bin/env bash
# Run the hybrid-parser benchmark on CSV Storm and original Pollock files.
#
# Usage:
#   scripts/run_csv_storm_hybrid_benchmark.sh [options]
#
# Options:
#   --regenerate       Recreate only data/csv_storm with Pollock 2.0 first.
#   --keep-results     Keep existing parser outputs instead of overwriting them.
#   --clevercsv        Reconcile LLM dialect detection with CleverCSV.
#   --duckdb-sniff     Reconcile LLM dialect detection with DuckDB sniff_csv.
#   --verbose          Print LLM prompts and responses.
#   --confirm-cost     Confirm the potentially large paid 2x2x2 LLM matrix.
#   -h, --help         Show this help.
#
# Environment:
#   OPENAI_API_KEY     Required API or proxy key.
#   OPENAI_ENDPOINT    Defaults to the public OpenAI chat-completions endpoint.
#   OPENAI_API_BASE    Full-loader API base; derived from OPENAI_ENDPOINT by default.
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
parser_mode="llm"
verbose=false
confirm_cost=false

usage() {
    sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --regenerate)
            regenerate=true
            ;;
        --keep-results)
            overwrite_results=false
            ;;
        --clevercsv)
            if [[ "$parser_mode" != "llm" ]]; then
                echo "Error: --clevercsv and --duckdb-sniff are mutually exclusive."
                exit 2
            fi
            parser_mode="clevercsv"
            ;;
        --duckdb-sniff)
            if [[ "$parser_mode" != "llm" ]]; then
                echo "Error: --clevercsv and --duckdb-sniff are mutually exclusive."
                exit 2
            fi
            parser_mode="duckdb"
            ;;
        --verbose)
            verbose=true
            ;;
        --confirm-cost)
            confirm_cost=true
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

if [[ "$confirm_cost" != true ]]; then
    echo "Error: this matrix can make thousands of paid LLM calls."
    echo "Rerun with --confirm-cost after reviewing the configured models and datasets."
    exit 1
fi

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        python_bin=".venv/bin/python"
    else
        python_bin="python3"
    fi
fi

if [[ -z "${OPENAI_API_KEY:-}" || "$OPENAI_API_KEY" == "YOUR_OPENAI_API_KEY" ]]; then
    echo "Error: export a real OPENAI_API_KEY before running the benchmark."
    echo "Example: export OPENAI_API_KEY=\"sk-...\""
    exit 1
fi

export OPENAI_ENDPOINT="${OPENAI_ENDPOINT:-https://api.openai.com/v1/chat/completions}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-${OPENAI_ENDPOINT%/chat/completions}}"
datasets=("csv_storm" "original_pollock_polluted_files")
models=("gpt-5.4-mini" "gpt-5.4")

if [[ "$regenerate" == true ]]; then
    echo "=== Regenerating data/csv_storm with Pollock 2.0 ==="
    "$python_bin" pollute_main.py \
        --source ./results/source.csv \
        --output ./data/csv_storm \
        --polluters pollock2.0 \
        --rng-seed 1337 \
        --overwrite
fi

if [[ ! -d "data/csv_storm/ground_truth" ]]; then
    echo "Error: data/csv_storm/ground_truth does not exist."
    echo "The dataset predates multi-GT generation; rerun with --regenerate."
    exit 1
fi
for dataset in "${datasets[@]}"; do
    if [[ ! -d "data/$dataset/csv" || ! -d "data/$dataset/clean" ]]; then
        echo "Error: data/$dataset must contain csv/ and clean/ directories."
        exit 1
    fi
done

hybrid_common_args=()
full_common_args=(--version naive)
hybrid_suffix=""
if [[ "$overwrite_results" == true ]]; then
    hybrid_common_args+=(--overwrite)
    full_common_args+=(--overwrite)
fi
case "$parser_mode" in
    clevercsv)
        hybrid_common_args+=(--clevercsv)
        hybrid_suffix="_clevercsv"
        ;;
    duckdb)
        hybrid_common_args+=(--duckdb-sniff)
        hybrid_suffix="_duckdb"
        ;;
esac
if [[ "$verbose" == true ]]; then
    hybrid_common_args+=(--verbose)
    full_common_args+=(--verbose)
fi

model_slug() {
    printf "%s" "$1" \
        | tr "[:upper:]" "[:lower:]" \
        | sed -E "s/[^a-z0-9]+/_/g; s/^_+|_+$//g"
}

echo "=== Configuration ==="
echo "Datasets: ${datasets[*]}"
echo "Models:   ${models[*]}"
echo "Methods:  hybrid${hybrid_suffix} full_llm_loader_naive"
echo "Python:   $python_bin"
echo "Hybrid endpoint: $OPENAI_ENDPOINT"
echo "Full API base:   $OPENAI_API_BASE"
echo

for model in "${models[@]}"; do
    export OPENAI_MODEL="$model"
    slug="$(model_slug "$model")"
    hybrid_sut="llm_hybrid_parser_${slug}${hybrid_suffix}"
    full_sut="full_llm_loader_naive_${slug}"

    for dataset in "${datasets[@]}"; do
        export DATASET="$dataset"

        echo "=== Hybrid parser: $model on $dataset ==="
        "$python_bin" \
            sut/llm_hybrid_parser_Robin/llm-hybrid-bench.py \
            --model "$model" \
            "${hybrid_common_args[@]}"

        echo
        echo "=== Evaluating $hybrid_sut on $dataset ==="
        "$python_bin" evaluate_csvstorm.py \
            --dataset "$dataset" \
            --sut "$hybrid_sut" \
            --njobs "${EVAL_NJOBS:-1}"

        echo
        echo "=== Full LLM naive: $model on $dataset ==="
        "$python_bin" \
            sut/full_llm_loader/custom-bench.py \
            --model "$model" \
            "${full_common_args[@]}"

        echo
        echo "=== Evaluating $full_sut on $dataset ==="
        "$python_bin" evaluate_csvstorm.py \
            --dataset "$dataset" \
            --sut "$full_sut" \
            --njobs "${EVAL_NJOBS:-1}"
        echo
    done
done

echo "=== Benchmark matrix complete ==="
for model in "${models[@]}"; do
    slug="$(model_slug "$model")"
    for sut in \
        "llm_hybrid_parser_${slug}${hybrid_suffix}" \
        "full_llm_loader_naive_${slug}"; do
        for dataset in "${datasets[@]}"; do
            echo
            echo "$sut / $dataset:"
            echo "  Parser outputs:  results/$sut/$dataset/loading/"
            echo "  Per-file scores: results/$sut/$dataset/${sut}_results.csv"
        done
    done
done

echo
echo "Dataset-level summaries:"
for dataset in "${datasets[@]}"; do
    echo "  results/aggregate_results_${dataset}.csv"
    echo "  results/global_results_${dataset}.csv"
done
