#!/usr/bin/env bash
# Run the requested parser matrix against CSV Storm.
#
# Usage:
#   scripts/run_full_benchmark_on_csvstorm.sh [options]
#
# Options:
#   --regenerate       Recreate data/csv_storm with CSV Storm polluters first.
#   --real-world       Run on data/combined_real_world_files instead of csv_storm
#                      (skips DuckDB Explicit; not combinable with --regenerate).
#   --skip-local       Skip the local Ollama models; run only the remote models.
#   --local-only       Skip the remote models; run only the local Ollama models
#                      (no paid calls, so neither --confirm-cost nor an API key
#                      is required).
#   --run-id ID        Name this isolated run (default: UTC timestamp + commit).
#   --resume ID        Continue an interrupted run with matching inputs/settings.
#   --verbose          Print hybrid- and full-agentic-parser LLM prompts/responses.
#   --confirm-cost     Confirm the potentially large paid LLM matrix.
#   -h, --help         Show this help.
#
# Environment:
#   OPENAI_API_KEY     Required for the three remote GPT models (not with --local-only).
#   OPENAI_ENDPOINT    Remote OpenAI-compatible chat-completions endpoint.
#   OLLAMA_API_BASE    Local Ollama API base, default http://localhost:11434/v1.
#   PYTHON             Optional Python interpreter override.
#   EVAL_NJOBS         Evaluation workers, default 100 (capped at CPU count).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f ".env" ]]; then
    set -o allexport
    source .env
    set +o allexport
fi

regenerate=false
dataset="csv_storm"
skip_local=false
local_only=false
verbose=false
confirm_cost=false
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
        --real-world)
            dataset="combined_real_world_files"
            ;;
        --skip-local)
            skip_local=true
            ;;
        --local-only)
            local_only=true
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

if [[ "$skip_local" == true && "$local_only" == true ]]; then
    echo "Error: --skip-local and --local-only cannot be combined."
    exit 2
fi
if [[ "$confirm_cost" != true && "$local_only" != true ]]; then
    echo "Error: this matrix can make thousands of paid LLM calls."
    echo "Rerun with --confirm-cost after reviewing the configured models."
    exit 1
fi
if [[ "$resume" == true && "$regenerate" == true ]]; then
    echo "Error: --regenerate cannot be used with --resume."
    exit 2
fi
if [[ "$regenerate" == true && "$dataset" != "csv_storm" ]]; then
    echo "Error: --regenerate is only available for the default csv_storm dataset."
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

if [[ "$local_only" != true ]] && [[ -z "${OPENAI_API_KEY:-}" || "$OPENAI_API_KEY" == "YOUR_OPENAI_API_KEY" ]]; then
    echo "Error: export a real OPENAI_API_KEY for the remote GPT model runs."
    echo "Example: export OPENAI_API_KEY=\"sk-...\""
    exit 1
fi

dataset_seed=1337
remote_models=("gpt-6.2-sol" "gpt-6.1-terra" "gpt-6-luna")
local_models=("qwen3.5:0.8b")
if [[ "$skip_local" == true ]]; then
    local_models=()
fi
if [[ "$local_only" == true ]]; then
    remote_models=()
fi
remote_openai_endpoint="${OPENAI_ENDPOINT:-https://api.openai.com/v1/chat/completions}"
# full_llm_loader takes an API base and appends /chat/completions itself.
remote_openai_api_base="${remote_openai_endpoint%/}"
remote_openai_api_base="${remote_openai_api_base%/chat/completions}"
if [[ "$remote_openai_api_base" == "${remote_openai_endpoint%/}" ]]; then
    echo "Error: OPENAI_ENDPOINT must end with /chat/completions: $remote_openai_endpoint"
    exit 1
fi
ollama_api_base="${OLLAMA_API_BASE:-http://localhost:11434/v1}"

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

model_slug() {
    printf "%s" "$1" \
        | tr "[:upper:]" "[:lower:]" \
        | sed -E "s/[^a-z0-9]+/_/g; s/^_+|_+$//g"
}

classical_suts=(duckdbauto_strict duckdbparse pandas clevercs pycsv)
if [[ "$dataset" != "csv_storm" ]]; then
    classical_suts=(duckdbauto_strict pandas clevercs pycsv)
fi
suts=("${classical_suts[@]}")
for model in "${remote_models[@]}" "${local_models[@]}"; do
    slug="$(model_slug "$model")"
    suts+=("llm_hybrid_parser_${slug}_duckdb" "code_generation_llm_${slug}")
    suts+=("full_llm_loader_naive_${slug}")
done

# Every SUT reads N_REPETITIONS; run each file once unless overridden.
export N_REPETITIONS="${N_REPETITIONS:-1}"
manifest_args=(
    init --run-id "$run_id" --script full --dataset "$dataset"
    --seed "$dataset_seed" --remote-models "${remote_models[*]}"
    --local-models "${local_models[*]}"
    --suts "${suts[*]}"
    --repetitions "$N_REPETITIONS" --eval-njobs "${EVAL_NJOBS:-100}"
    --cache-policy cold
)
if [[ "$resume" == true ]]; then
    manifest_args+=(--resume)
fi
if [[ "$verbose" == true ]]; then
    manifest_args+=(--verbose)
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
export OLLAMA_API_BASE="$ollama_api_base"

hybrid_verbose_args=()
if [[ "$verbose" == true ]]; then
    hybrid_verbose_args+=(--verbose)
fi

evaluate_sut() {
    local sut="$1"

    echo
    echo "=== Evaluating $sut on $dataset ==="
    "$python_bin" evaluate.py \
        --dataset "$dataset" \
        --result "$RESULT_ROOT" \
        --sut "$sut" \
        --njobs "${EVAL_NJOBS:-100}"
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
    local duckdb_hybrid_sut
    local code_generation_sut
    local full_agentic_sut
    local full_agentic_api_base

    slug="$(model_slug "$model")"
    duckdb_hybrid_sut="llm_hybrid_parser_${slug}_duckdb"
    code_generation_sut="code_generation_llm_${slug}"
    full_agentic_sut="full_llm_loader_naive_${slug}"

    if [[ "$backend" == "ollama" ]]; then
        configure_local_model "$model"
        backend_args=(--backend ollama --api-base "$ollama_api_base")
        full_agentic_api_base="$ollama_api_base"
    else
        configure_remote_model "$model"
        backend_args=(--backend openai)
        full_agentic_api_base="$remote_openai_api_base"
    fi

    echo
    echo "=== Hybrid parser (DuckDB + LLM sniffer): $model via $backend on $dataset ==="
    "$python_bin" sut/llm_hybrid_parser/llm-hybrid-bench.py \
        --model "$model" \
        --no-llm-cache \
        --duckdb-sniff \
        "${backend_args[@]}" \
        "${hybrid_verbose_args[@]}"
    evaluate_sut "$duckdb_hybrid_sut"

    echo
    echo "=== Code-generation parser: $model via $backend on $dataset ==="
    "$python_bin" sut/code_generation_llm/custom-bench.py \
        --model "$model" \
        --no-llm-cache
    evaluate_sut "$code_generation_sut"

    echo
    echo "=== Full-agentic parser: $model via $backend on $dataset ==="
    # Bypass the response cache for cold calls without --overwrite, so --resume
    # still skips files that already have output.
    FULL_LLM_LOADER_BYPASS_CACHE=1 "$python_bin" sut/full_llm_loader/custom-bench.py \
        --model "$model" \
        --backend "$backend" \
        --api-base "$full_agentic_api_base" \
        "${hybrid_verbose_args[@]}"
    evaluate_sut "$full_agentic_sut"
}

echo "=== Configuration ==="
echo "Run ID:        $run_id"
echo "Result root:   $RESULT_ROOT"
echo "Dataset:       $dataset"
echo "Remote models: ${remote_models[*]}"
echo "Local models:  ${local_models[*]} (Ollama: $ollama_api_base)"
echo "LLM methods:   hybrid/DuckDB-sniffer code-generation full-agentic"
echo "Other SUTs:    ${classical_suts[*]}"
echo "Python:        $python_bin"
echo "Remote API:    $remote_openai_endpoint"

run_classical_sut "DuckDB Auto" "duckdbauto_strict" "sut/duckdbauto/duck-bench.py" --strict
if [[ "$dataset" == "csv_storm" ]]; then
    run_classical_sut "DuckDB Explicit" "duckdbparse" "sut/duckdbparse/duck-bench.py"
fi
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
echo "  $RESULT_ROOT/evaluation_summary_${dataset}.csv"
echo "  $RESULT_ROOT/evaluation_by_file_${dataset}.csv"
echo
echo "Per-SUT outputs are under $RESULT_ROOT/<sut>/$dataset/."
