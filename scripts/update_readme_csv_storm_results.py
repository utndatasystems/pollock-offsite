#!/usr/bin/env python3
"""Refresh the CSV Storm evaluation table embedded in README.md."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
DATASET = "csv_storm"
START_MARKER = "<!-- CSV_STORM_RESULTS_START -->"
END_MARKER = "<!-- CSV_STORM_RESULTS_END -->"


@dataclass(frozen=True)
class ParserResult:
    parser: str
    model: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


DEFAULT_SUTS = (
    ("Full LLM (naive)", "full_llm_loader_naive_qwen3_5_0_8b"),
    ("Hybrid", "llm_hybrid_parser_qwen3_5_0_8b"),
)


def _read_model(result_dir: Path, sut: str) -> str:
    time_path = result_dir / f"{sut}_time.csv"
    if not time_path.is_file():
        return "unknown"
    with time_path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle), None)
    return (row or {}).get("model") or "unknown"


def _read_result(label: str, sut: str) -> ParserResult:
    result_dir = REPO_ROOT / "results" / sut / DATASET
    result_path = result_dir / f"{sut}_results.csv"
    if not result_path.is_file():
        raise FileNotFoundError(
            f"Missing evaluation output: {result_path.relative_to(REPO_ROOT)}"
        )

    correct_column = f"{sut}_correct"
    with result_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if rows and correct_column not in rows[0]:
        raise ValueError(f"Missing column {correct_column!r} in {result_path}")

    return ParserResult(
        parser=label,
        model=_read_model(result_dir, sut),
        correct=sum(int(row[correct_column]) for row in rows),
        total=len(rows),
    )


def _render_table(results: list[ParserResult]) -> str:
    lines = [
        START_MARKER,
        "| Parser | Model | Exact file matches | Accuracy |",
        "| --- | --- | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.parser} | `{result.model}` | "
            f"{result.correct}/{result.total} | {result.accuracy:.1%} |"
        )
    lines.append(END_MARKER)
    return "\n".join(lines)


def _replace_results_section(readme: str, rendered: str) -> str:
    if START_MARKER not in readme or END_MARKER not in readme:
        raise ValueError(
            "README result markers are missing; expected "
            f"{START_MARKER!r} and {END_MARKER!r}."
        )
    prefix, remainder = readme.split(START_MARKER, 1)
    _, suffix = remainder.split(END_MARKER, 1)
    return f"{prefix}{rendered}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of updating README.md when the table is stale.",
    )
    args = parser.parse_args()

    results = [_read_result(label, sut) for label, sut in DEFAULT_SUTS]
    current = README_PATH.read_text(encoding="utf-8")
    updated = _replace_results_section(current, _render_table(results))

    if args.check:
        if updated != current:
            raise SystemExit(
                "README CSV Storm results are stale. Run "
                "scripts/update_readme_csv_storm_results.py."
            )
        return

    README_PATH.write_text(updated, encoding="utf-8")
    print(f"Updated {README_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
