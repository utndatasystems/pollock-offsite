#!/usr/bin/env bash
# Run the custom LLM-based CSV parser on one input CSV file.
# Usage: scripts/run_llm_parser.sh <csv_path> [rows]
# Example: scripts/run_llm_parser.sh data/csv_storm/csv/file_field_delimiter_0x3B.csv 128

set -euo pipefail

# Load .env if present (does not override already-exported variables)
if [[ -f ".env" ]]; then
    set -o allexport
    source .env
    set +o allexport
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 <csv_path> [rows]"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CSV_PATH="$1"
ROWS="${2:-128}"
if [[ ! "$ROWS" =~ ^[0-9]+$ ]]; then
    echo "Error: rows must be a non-negative integer"
    exit 1
fi

if [[ ! -f "$CSV_PATH" ]]; then
    echo "Error: file not found: $CSV_PATH"
    exit 1
fi

python3 - "$REPO_ROOT" "$CSV_PATH" "$ROWS" <<'PY'
import sys
from pathlib import Path
from pprint import pprint

repo_root = Path(sys.argv[1])
csv_path = Path(sys.argv[2])
nrows = int(sys.argv[3])

sys.path.insert(0, str(repo_root))
from sut.full_llm_loader.solution import parse_csv

print(f"Parsing: {csv_path}")
print(f"Rows: {nrows}")

try:
    df = parse_csv(str(csv_path), nrows=nrows)
except Exception as exc:
    print(f"Error: {exc}")
    raise

print(f"\nDataFrame shape: {df.shape}")
print("\nDataFrame preview:")
print(df.head().to_string(index=False))
print("\nllm_error_report:")
pprint(df.attrs.get("llm_error_report"))
PY
