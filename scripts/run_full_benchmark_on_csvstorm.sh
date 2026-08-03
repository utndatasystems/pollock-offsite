#!/usr/bin/env bash
# Run the requested parser matrix against CSV Storm.
#
# Usage:
#   scripts/run_full_benchmark_on_csvstorm.sh [options]
#
# Options:
#   --regenerate       Recreate data/csv_storm with CSV Storm polluters first.
#   --keep-results     Keep existing parser outputs instead of overwriting them.
#   --keep-llm-results Keep existing LLM parser outputs (avoids paid calls) while
#                      still overwriting the classical SUT outputs.
#   --verbose          Print hybrid-parser LLM prompts and responses.
#   --confirm-cost     Confirm the potentially large paid LLM matrix.
#   -h, --help         Show this help.
#
# Environment:
#   OPENAI_API_KEY     Required for the three remote GPT models.
#   OPENAI_ENDPOINT    Remote OpenAI-compatible chat-completions endpoint.
#   OLLAMA_API_BASE    Local Ollama API base, default http://localhost:11434/v1.
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
keep_llm_results=false
verbose=false
confirm_cost=false

usage() {
    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --regenerate)
            regenerate=true
            ;;
        --keep-results)
            overwrite_results=false
            ;;
        --keep-llm-results)
            keep_llm_results=true
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
    echo "Rerun with --confirm-cost after reviewing the configured models."
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
    echo "Error: export a real OPENAI_API_KEY for the remote GPT model runs."
    echo "Example: export OPENAI_API_KEY=\"sk-...\""
    exit 1
fi

dataset="csv_storm"
remote_models=("gpt-5.4-mini" "gpt-5.6-sol" "gpt-5.6-luna")
local_models=("qwen3.5:0.8b")
remote_openai_endpoint="${OPENAI_ENDPOINT:-https://api.openai.com/v1/chat/completions}"
ollama_api_base="${OLLAMA_API_BASE:-http://localhost:11434/v1}"

if [[ "$regenerate" == true ]]; then
    echo "=== Regenerating data/$dataset with CSV Storm ==="
    "$python_bin" pollute_main.py \
        --source ./results/source.csv \
        --output "./data/$dataset" \
        --polluters csv_storm \
        --combinations \
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
export OLLAMA_API_BASE="$ollama_api_base"

classical_overwrite_args=()
llm_overwrite_args=()
hybrid_verbose_args=()
if [[ "$overwrite_results" == true ]]; then
    classical_overwrite_args+=(--overwrite)
    if [[ "$keep_llm_results" != true ]]; then
        llm_overwrite_args+=(--overwrite)
    fi
fi
if [[ "$verbose" == true ]]; then
    hybrid_verbose_args+=(--verbose)
fi

model_slug() {
    printf "%s" "$1" \
        | tr "[:upper:]" "[:lower:]" \
        | sed -E "s/[^a-z0-9]+/_/g; s/^_+|_+$//g"
}

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

configure_remote_model() {
    local model="$1"

    export LLM_BACKEND="openai"
    export OPENAI_MODEL="$model"
    export OPENAI_ENDPOINT="$remote_openai_endpoint"
}

configure_local_model() {
    local model="$1"

    export LLM_BACKEND="ollama"
    export OLLAMA_MODEL="$model"
    # code_generation_llm uses OPENAI_MODEL/OPENAI_ENDPOINT directly while
    # recognizing LLM_BACKEND=ollama for its Ollama-specific request options.
    export OPENAI_MODEL="$model"
    export OPENAI_ENDPOINT="${ollama_api_base%/}/chat/completions"
    export OPENAI_API_KEY="${OPENAI_API_KEY:-ollama}"
}

run_llm_model() {
    local backend="$1"
    local model="$2"
    local slug
    local backend_args=()
    local llm_hybrid_sut
    local duckdb_hybrid_sut
    local code_generation_sut

    slug="$(model_slug "$model")"
    llm_hybrid_sut="llm_hybrid_parser_${slug}"
    duckdb_hybrid_sut="llm_hybrid_parser_${slug}_duckdb"
    code_generation_sut="code_generation_llm_${slug}"

    if [[ "$backend" == "ollama" ]]; then
        configure_local_model "$model"
        backend_args=(--backend ollama --api-base "$ollama_api_base")
    else
        configure_remote_model "$model"
        backend_args=(--backend openai)
    fi

    echo
    echo "=== Hybrid parser (LLM sniffer): $model via $backend on $dataset ==="
    "$python_bin" sut/llm_hybrid_parser/llm-hybrid-bench.py \
        --model "$model" \
        "${backend_args[@]}" \
        "${llm_overwrite_args[@]}" \
        "${hybrid_verbose_args[@]}"
    evaluate_sut "$llm_hybrid_sut"

    echo
    echo "=== Hybrid parser (DuckDB + LLM sniffer): $model via $backend on $dataset ==="
    "$python_bin" sut/llm_hybrid_parser/llm-hybrid-bench.py \
        --model "$model" \
        --duckdb-sniff \
        "${backend_args[@]}" \
        "${llm_overwrite_args[@]}" \
        "${hybrid_verbose_args[@]}"
    evaluate_sut "$duckdb_hybrid_sut"

    echo
    echo "=== Code-generation parser: $model via $backend on $dataset ==="
    "$python_bin" sut/code_generation_llm/custom-bench.py \
        --model "$model" \
        "${llm_overwrite_args[@]}"
    evaluate_sut "$code_generation_sut"
}

echo "=== Configuration ==="
echo "Dataset:       $dataset"
echo "Remote models: ${remote_models[*]}"
echo "Local models:  ${local_models[*]} (Ollama: $ollama_api_base)"
echo "LLM methods:   hybrid/LLM-sniffer hybrid/DuckDB-sniffer code-generation"
echo "Other SUTs:    duckdbauto_strict duckdbparse pandas clevercs pycsv"
echo "Python:        $python_bin"
echo "Remote API:    $remote_openai_endpoint"

run_classical_sut "DuckDB Auto" "duckdbauto_strict" "sut/duckdbauto/duck-bench.py" --strict
run_classical_sut "DuckDB Explicit" "duckdbparse" "sut/duckdbparse/duck-bench.py"
run_classical_sut "pandas" "pandas" "sut/pandas/panda.py"
run_classical_sut "CleverCSV" "clevercs" "sut/clevercs/clevercs.py"
run_classical_sut "Python CSV" "pycsv" "sut/pycsv/pycsv.py"

for model in "${remote_models[@]}"; do
    run_llm_model "openai" "$model"
done
for model in "${local_models[@]}"; do
    run_llm_model "ollama" "$model"
done

echo
echo "=== Benchmark matrix complete ==="
echo "Dataset-level summaries:"
echo "  results/evaluation_summary_${dataset}.csv"
echo "  results/evaluation_by_file_${dataset}.csv"
echo
echo "Per-SUT outputs are under results/<sut>/$dataset/."
