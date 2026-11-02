"""Compare a GPT-6 Luna CSV Storm run with saved LLM benchmark results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


METHODS = {
    "hybrid": (
        "llm_hybrid_parser_gpt_6_luna",
        ["llm_hybrid_parser_gpt_5_6_sol", "llm_hybrid_parser_gpt_5_6_luna",
         "llm_hybrid_parser_gpt_5_4_mini", "llm_hybrid_parser_qwen3_5_0_8b"],
    ),
    "hybrid_duckdb": (
        "llm_hybrid_parser_gpt_6_luna_duckdb",
        ["llm_hybrid_parser_gpt_5_6_sol_duckdb", "llm_hybrid_parser_gpt_5_6_luna_duckdb",
         "llm_hybrid_parser_gpt_5_4_mini_duckdb", "llm_hybrid_parser_qwen3_5_0_8b_duckdb"],
    ),
    "full_llm": (
        "full_llm_loader_naive_gpt_6_luna",
        ["full_llm_loader_naive_gpt_5_6_sol", "full_llm_loader_naive_gpt_5_4_mini",
         "full_llm_loader_naive_qwen3_4_0_8b"],
    ),
    "code_generation": (
        "code_generation_llm_gpt_6_luna",
        ["code_generation_llm_gpt_5_6_sol", "code_generation_llm_gpt_5_6_luna",
         "code_generation_llm_gpt_5_4_mini", "code_generation_llm_qwen3_5_0_8b"],
    ),
}


def load_results(root: Path, sut: str) -> pd.DataFrame:
    path = root / sut / "csv_storm" / f"{sut}_results.csv"
    frame = pd.read_csv(path).set_index("file")
    if len(frame) != 69 or frame.index.has_duplicates:
        raise ValueError(f"Expected 69 distinct files in {path}, found {len(frame)} rows")
    return frame


def status(frame: pd.DataFrame, sut: str, filename: str) -> str:
    row = frame.loc[filename]
    if not bool(row[f"{sut}_success"]):
        return "error"
    return "exact" if bool(row[f"{sut}_correct"]) else "inexact"


def diagnosis(frame: pd.DataFrame, sut: str, filename: str, run_root: Path) -> str:
    row = frame.loc[filename]
    if not bool(row[f"{sut}_success"]):
        error = row.get(f"{sut}_evaluation_error")
        if pd.notna(error) and str(error):
            return str(error)
        output = run_root / sut / "csv_storm" / "loading" / f"{filename}_converted.csv"
        return output.read_text(errors="replace").removeprefix("Application Error\n").strip()
    if bool(row[f"{sut}_correct"]):
        return "exact reconstruction"
    affected = [
        label for label in ("header", "record", "cell")
        if float(row[f"{sut}_{label}_f1"]) < 1 - 1e-9
    ]
    if affected:
        return ", ".join(affected) + " mismatch"
    clean = Path(__file__).resolve().parents[1] / "data" / "csv_storm" / "clean" / filename
    output = run_root / sut / "csv_storm" / "loading" / f"{filename}_converted.csv"
    with clean.open(newline="") as expected_file, output.open(newline="") as actual_file:
        expected = list(csv.reader(expected_file))
        actual = list(csv.reader(actual_file))
    for row_number, (expected_row, actual_row) in enumerate(zip(expected, actual)):
        for column_number, (expected_cell, actual_cell) in enumerate(zip(expected_row, actual_row)):
            if expected_cell != actual_cell:
                return f"cell mismatch at row {row_number}, column {column_number}"
    return "strict mismatch"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    saved_root = Path(__file__).resolve().parents[1] / "results"
    records = []
    for method, (luna_sut, previous_suts) in METHODS.items():
        luna = load_results(run_root, luna_sut)
        previous = {sut: load_results(saved_root, sut) for sut in previous_suts}
        if any(set(frame.index) != set(luna.index) for frame in previous.values()):
            raise ValueError(f"File sets differ for {method}")
        for filename in sorted(luna.index):
            row = {
                "method": method,
                "file": filename,
                "gpt_6_luna": status(luna, luna_sut, filename),
                "luna_diagnosis": diagnosis(luna, luna_sut, filename, run_root),
                "luna_header_f1": luna.at[filename, f"{luna_sut}_header_f1"],
                "luna_record_f1": luna.at[filename, f"{luna_sut}_record_f1"],
                "luna_cell_f1": luna.at[filename, f"{luna_sut}_cell_f1"],
            }
            divergent = []
            for sut, frame in previous.items():
                model = sut.removeprefix("llm_hybrid_parser_").removeprefix(
                    "full_llm_loader_naive_").removeprefix("code_generation_llm_")
                model = model.removesuffix("_duckdb")
                result = status(frame, sut, filename)
                row[model] = result
                if result != row["gpt_6_luna"]:
                    divergent.append(model)
            row["divergent_from"] = ", ".join(divergent)
            records.append(row)
    output = run_root / "per_file_comparison.csv"
    pd.DataFrame(records).to_csv(output, index=False)
    print(output)


if __name__ == "__main__":
    main()
