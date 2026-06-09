#!/usr/bin/env bash
# Run the custom LLM-based CSV parser on one input CSV file.
# Usage: scripts/run_llm_parser.sh <csv_path>
# Example: scripts/run_llm_parser.sh data/csv_storm/csv/file_field_delimiter_0x3B.csv

set -euo pipefail

# Load .env if present (does not override already-exported variables)
if [[ -f ".env" ]]; then
    set -o allexport
    source .env
    set +o allexport
fi

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <csv_path>"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CSV_PATH="$1"
if [[ ! -f "$CSV_PATH" ]]; then
    echo "Error: file not found: $CSV_PATH"
    exit 1
fi

python3 - "$REPO_ROOT" "$CSV_PATH" <<'PY'
import sys
from pathlib import Path
from pprint import pprint

repo_root = Path(sys.argv[1])
csv_path = Path(sys.argv[2])

sys.path.insert(0, str(repo_root))
from sut.full_llm_loader.solution import parse_csv

print(f"Parsing: {csv_path}")

try:
    df = parse_csv(str(csv_path))
except Exception as exc:
    print(f"Error: {exc}")
    raise

print(f"\nDataFrame shape: {df.shape}")
print("\nDataFrame preview:")
print(df.head().to_string(index=False))
print("\nllm_error_report:")
pprint(df.attrs.get("llm_error_report"))
PY
