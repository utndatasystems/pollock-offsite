"""Compare a GPT-6.1 Sol CSV Storm run with saved Luna and GPT-5 results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SAVED_ROOT = REPO_ROOT / "results"
LUNA_ROOT = SAVED_ROOT / "runs" / "gpt6-luna-20261101"
METHODS = {
    "hybrid": "llm_hybrid_parser_{model}",
    "hybrid_duckdb": "llm_hybrid_parser_{model}_duckdb",
    "full_llm": "full_llm_loader_naive_{model}",
    "code_generation": "code_generation_llm_{model}",
}
MODELS = {
    "gpt_6_1_sol": None,
    "gpt_6_luna": LUNA_ROOT,
    "gpt_5_6_sol": SAVED_ROOT,
    "gpt_5_6_luna": SAVED_ROOT,
    "gpt_5_4_mini": SAVED_ROOT,
}


def load(root: Path, sut: str) -> pd.DataFrame:
    path = root / sut / "csv_storm" / f"{sut}_results.csv"
    frame = pd.read_csv(path).set_index("file")
    if len(frame) != 69 or frame.index.has_duplicates:
        raise ValueError(f"Expected 69 distinct files in {path}")
    return frame


def outcome(frame: pd.DataFrame, sut: str, filename: str) -> str:
    row = frame.loc[filename]
    if not bool(row[f"{sut}_success"]):
        return "error"
    return "exact" if bool(row[f"{sut}_correct"]) else "inexact"


def explanation(root: Path, frame: pd.DataFrame, sut: str, filename: str) -> str:
    row = frame.loc[filename]
    output = root / sut / "csv_storm" / "loading" / f"{filename}_converted.csv"
    if not bool(row[f"{sut}_success"]):
        return output.read_text(errors="replace").removeprefix("Application Error\n").strip()
    if bool(row[f"{sut}_correct"]):
        return "exact reconstruction"
    affected = [
        measure for measure in ("header", "record", "cell")
        if float(row[f"{sut}_{measure}_f1"]) < 1 - 1e-9
    ]
    if affected:
        return ", ".join(affected) + " mismatch"
    clean = REPO_ROOT / "data" / "csv_storm" / "clean" / filename
    with clean.open(newline="") as expected_file, output.open(newline="") as actual_file:
        expected = list(csv.reader(expected_file))
        actual = list(csv.reader(actual_file))
    for row_number, (expected_row, actual_row) in enumerate(zip(expected, actual)):
        for column_number, (expected_cell, actual_cell) in enumerate(zip(expected_row, actual_row)):
            if expected_cell != actual_cell:
                return f"cell mismatch at row {row_number}, column {column_number}"
    return "strict mismatch"


def markdown_cell(value: object) -> str:
    if pd.isna(value):
        return "—"
    return str(value).replace("|", "/").replace("\n", " ").replace("\r", " ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    records: list[dict] = []
    for method, sut_pattern in METHODS.items():
        frames = {}
        for model, baseline_root in MODELS.items():
            if method == "full_llm" and model == "gpt_5_6_luna":
                continue
            sut = sut_pattern.format(model=model)
            frames[model] = (sut, load(baseline_root or run_root, sut))
        target_sut, target = frames["gpt_6_1_sol"]
        if any(set(frame.index) != set(target.index) for _, frame in frames.values()):
            raise ValueError(f"File sets differ for {method}")
        for filename in sorted(target.index):
            row = {"method": method, "file": filename}
            for model, (sut, frame) in frames.items():
                row[model] = outcome(frame, sut, filename)
            row["sol_diagnosis"] = explanation(run_root, target, target_sut, filename)
            for measure in ("header", "record", "cell"):
                row[f"sol_{measure}_f1"] = target.at[filename, f"{target_sut}_{measure}_f1"]
            records.append(row)

    comparison = pd.DataFrame(records)
    csv_path = run_root / "per_file_comparison.csv"
    comparison.to_csv(csv_path, index=False)
    lines = [
        "# GPT-6.1 Sol CSV Storm per-file analysis",
        "",
        "One cold pass over 69 files per parser. Exact means the whole reconstructed "
        "file matched ground truth; inexact means a mismatch; error means no evaluable CSV.",
        "",
        "The tables show files where Sol's outcome differs from GPT-6 Luna or GPT-5.6 Sol "
        "on the same parser method. The comparison CSV also includes GPT-5.6 Luna "
        "and GPT-5.4 Mini where available.",
        "",
    ]
    for method in METHODS:
        group = comparison.loc[comparison.method == method]
        heading = {
            "hybrid": "Hybrid",
            "hybrid_duckdb": "Hybrid DuckDB",
            "full_llm": "Full LLM",
            "code_generation": "Code generation",
        }[method]
        lines.extend([f"## {heading}", ""])
        for model in ("gpt_6_luna", "gpt_5_6_sol"):
            wins = ((group.gpt_6_1_sol == "exact") & (group[model] != "exact")).sum()
            losses = ((group.gpt_6_1_sol != "exact") & (group[model] == "exact")).sum()
            noun = "file" if wins == 1 else "files"
            lines.append(f"- Versus {model}: {wins} exact {noun} gained, {losses} lost.")
        lines.extend([
            "",
            "| File | GPT-6.1 Sol | GPT-6 Luna | GPT-5.6 Sol | Sol detail |",
            "| --- | --- | --- | --- | --- |",
        ])
        different = group.loc[
            (group.gpt_6_1_sol != group.gpt_6_luna)
            | (group.gpt_6_1_sol != group.gpt_5_6_sol)
        ]
        for _, row in different.iterrows():
            detail = row.sol_diagnosis
            if row.gpt_6_1_sol == "inexact":
                detail += (f"; H/R/C F1 {row.sol_header_f1:.3f}/"
                           f"{row.sol_record_f1:.3f}/{row.sol_cell_f1:.3f}")
            fields = (row.file, row.gpt_6_1_sol, row.gpt_6_luna,
                      row.gpt_5_6_sol, detail[:170])
            lines.append("| " + " | ".join(markdown_cell(value) for value in fields) + " |")
        lines.append("")
    report_path = run_root / "per_file_analysis.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(csv_path)
    print(report_path)


if __name__ == "__main__":
    main()
