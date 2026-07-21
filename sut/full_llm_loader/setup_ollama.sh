#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export FULL_LLM_LOADER_BACKEND="ollama"
export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://localhost:11434/v1}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:0.8b}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-ollama}"

OLLAMA_HOST="${OLLAMA_API_BASE%/v1}"
OLLAMA_LOG="${OLLAMA_LOG:-/tmp/full_llm_loader_ollama.log}"

if ! curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "Starting Ollama server at ${OLLAMA_HOST}"
  ollama serve >"${OLLAMA_LOG}" 2>&1 &
  sleep 2
fi

python "${REPO_ROOT}/sut/full_llm_loader/solution.py"
