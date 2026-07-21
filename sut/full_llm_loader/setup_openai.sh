#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export FULL_LLM_LOADER_BACKEND="openai"
export OPENAI_API_BASE="${OPENAI_API_BASE:-https://api.openai.com/v1}"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required for FULL_LLM_LOADER_BACKEND=openai" >&2
  exit 1
fi

python "${REPO_ROOT}/sut/full_llm_loader/solution.py"
