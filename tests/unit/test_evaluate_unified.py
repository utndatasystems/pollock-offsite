import shutil
import sys

import pandas as pd
import pytest

import evaluate
from evaluate_utils import POLLOCK_MEASURES, aggregate_system


def test_single_file_reports_soft_and_strict_metrics(tmp_path, monkeypatch):
    dataset = tmp_path / "data" / "demo"
    clean = dataset / "clean" / "case.csv"
    source = dataset / "csv" / "case.csv"
    output = (
        tmp_path
        / "results"
        / "sut"
        / "demo"
        / "loading"
        / "case.csv_converted.csv"
    )
    clean.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    clean.write_text("name,value\nAlice,1\n", encoding="utf-8")
    shutil.copyfile(clean, source)
    shutil.copyfile(clean, output)
    monkeypatch.chdir(tmp_path)

    result = evaluate.evaluate_single_file("case.csv", "demo", "sut")

    assert result["sut_success"] == 1
    assert result["sut_header_f1"] == pytest.approx(1.0)
    assert result["sut_record_f1"] == pytest.approx(1.0)
    assert result["sut_cell_f1"] == pytest.approx(1.0)
    assert result["sut_correct"] == 1
    assert result["sut_wrong"] == 0
    assert result["sut_metric_ground_truth"] == "legacy_clean"
    assert result["sut_strict_ground_truth"] == "legacy_clean"
    assert result["sut_matched_ground_truth"] == "legacy_clean"
    assert result["sut_evaluation_error"] is None


def test_missing_output_has_complete_zero_result(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = evaluate.evaluate_single_file("missing.csv", "demo", "sut")

    assert result["sut_correct"] == 0
    assert result["sut_wrong"] == 1
    assert all(result[f"sut_{measure}"] == 0 for measure in POLLOCK_MEASURES)
    assert result["sut_evaluation_error"] == "missing_output"


def test_aggregate_contains_pollock_and_accuracy_metrics():
    rows = []
    for filename, value in (("a.csv", 1.0), ("b.csv", 0.0)):
        row = {
            "file": filename,
            "sut_correct": int(value),
            "sut_wrong": int(not value),
        }
        row.update({f"sut_{measure}": value for measure in POLLOCK_MEASURES})
        rows.append(row)

    aggregate = aggregate_system(
        pd.DataFrame(rows),
        "sut",
        "demo",
        weights={"a.csv": 1.0, "b.csv": 3.0},
    )

    assert aggregate["pollock_simple"] == pytest.approx(5.0)
    assert aggregate["pollock_weighted"] == pytest.approx(2.5)
    assert aggregate["accuracy"] == pytest.approx(0.5)
    assert aggregate["weighted_accuracy"] == pytest.approx(0.25)
    assert aggregate["correct"] == 1
    assert aggregate["wrong"] == 1


def test_cli_writes_combined_per_file_and_aggregate_results(
    tmp_path, monkeypatch
):
    dataset = tmp_path / "data" / "demo"
    clean = dataset / "clean" / "case.csv"
    source = dataset / "csv" / "case.csv"
    output = (
        tmp_path
        / "results"
        / "sut"
        / "demo"
        / "loading"
        / "case.csv_converted.csv"
    )
    clean.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    clean.write_text("name,value\nAlice,1\n", encoding="utf-8")
    shutil.copyfile(clean, source)
    shutil.copyfile(clean, output)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate.py", "--dataset", "demo", "--sut", "sut", "--njobs", "1"],
    )

    evaluate.main()

    per_file = pd.read_csv(tmp_path / "results" / "sut" / "demo" / "sut_results.csv")
    aggregate = pd.read_csv(tmp_path / "results" / "evaluation_summary_demo.csv")
    by_file = pd.read_csv(tmp_path / "results" / "evaluation_by_file_demo.csv")
    assert {"sut_cell_f1", "sut_correct", "sut_wrong"}.issubset(per_file.columns)
    assert {"sut_cell_f1", "sut_correct", "sut_wrong"}.issubset(by_file.columns)
    assert {
        "pollock_simple",
        "cell_f1",
        "accuracy",
        "correct",
        "wrong",
    }.issubset(aggregate.columns)
