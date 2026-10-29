import json
import shutil

import pytest

import evaluate

from pollution import metrics
from pollution.CSVFile import CSVFile
from pollution.ground_truth import (
    GroundTruthAlternative,
    GroundTruthBundle,
    GroundTruthTable,
    load_ground_truth_manifest,
    single_table_alternatives,
)
from pollution.polluters_stdlib_v1 import addTable
from scripts.upload_csv_storm_to_hf import validate_dataset_dir


def _csv_file(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text(
        "name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n",
        encoding="utf-8",
    )
    return CSVFile(str(source), quote_all=True)


def test_default_ground_truth_bundle_contains_one_canonical_gt(tmp_path):
    file = _csv_file(tmp_path)

    manifest_path = file.write_ground_truths(tmp_path / "ground_truth")
    manifest = load_ground_truth_manifest(manifest_path)

    assert manifest["canonical"] == "canonical"
    assert manifest["accept_origin"] is False
    assert manifest["alternatives"] == [
        {
            "id": "canonical",
            "comparison": "single_table",
            "tables": ["primary"],
        }
    ]
    candidates = single_table_alternatives(manifest_path)
    assert [alternative_id for alternative_id, _ in candidates] == ["canonical"]

    correct, matched = metrics.compare_ground_truths(
        manifest_path,
        candidates[0][1],
    )
    assert correct is True
    assert matched == "canonical"


def test_manifest_accept_origin_allows_inferred_source_gt(tmp_path):
    dataset = tmp_path / "data" / "demo"
    source = dataset / "csv" / "source.csv"
    source.parent.mkdir(parents=True)
    write_source = "name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n"
    source.write_text(write_source, encoding="utf-8")

    bundle = GroundTruthBundle.single(
        [["name", "city", "amount"], ["Alice", "Berlin", "999"]],
        accept_origin=True,
    )
    manifest_path = bundle.write(dataset / "ground_truth", "case.csv")
    loaded = tmp_path / "loaded.csv"
    shutil.copyfile(source, loaded)

    manifest = load_ground_truth_manifest(manifest_path)
    assert manifest["accept_origin"] is True
    assert metrics.compare_ground_truths(manifest_path, loaded) == (True, "origin")


def test_cli_origin_still_applies_when_manifest_does_not_accept_origin(tmp_path):
    dataset = tmp_path / "data" / "demo"
    source = dataset / "csv" / "source.csv"
    source.parent.mkdir(parents=True)
    source.write_text("name,city,amount\nAlice,Berlin,10\n", encoding="utf-8")

    bundle = GroundTruthBundle.single(
        [["name", "city", "amount"], ["Alice", "Berlin", "999"]],
    )
    manifest_path = bundle.write(dataset / "ground_truth", "case.csv")
    loaded = tmp_path / "loaded.csv"
    shutil.copyfile(source, loaded)

    assert metrics.compare_ground_truths(manifest_path, loaded) == (False, None)
    assert metrics.compare_ground_truths(
        manifest_path,
        loaded,
        origin_csv=source,
    ) == (True, "origin")


def test_multitable_bundle_accepts_primary_or_secondary_table(tmp_path):
    file = _csv_file(tmp_path)
    addTable(file, n_rows=3, n_cols=5, empty_boundary=True)

    manifest_path = file.write_ground_truths(tmp_path / "ground_truth")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["canonical"] == "all_tables"
    assert {alternative["id"] for alternative in manifest["alternatives"]} == {
        "primary_only",
        "secondary_only",
        "all_tables",
    }
    assert manifest["alternatives"][-1] == {
        "id": "all_tables",
        "comparison": "ordered_tables",
        "tables": ["primary", "secondary"],
    }

    candidates = dict(single_table_alternatives(manifest_path))
    primary_match = metrics.compare_ground_truths(
        manifest_path,
        candidates["primary_only"],
    )
    secondary_match = metrics.compare_ground_truths(
        manifest_path,
        candidates["secondary_only"],
    )

    assert primary_match == (True, "primary_only")
    assert secondary_match == (True, "secondary_only")


def test_ground_truth_bundle_rejects_unknown_table_reference():
    with pytest.raises(ValueError, match="unknown tables"):
        GroundTruthBundle(
            tables=(GroundTruthTable.from_rows("primary", [["name"]]),),
            alternatives=(
                GroundTruthAlternative(
                    id="invalid",
                    table_ids=("missing",),
                ),
            ),
            canonical="invalid",
        )



def test_dataset_manifest_exposes_optional_ground_truth_bundle(tmp_path):
    file = _csv_file(tmp_path)
    file.filename = "case.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    dataset = tmp_path / "dataset"
    clean_dir = dataset / "clean"
    clean_dir.mkdir(parents=True)

    file.write_csv(dataset / "csv")
    file.write_clean_csv(f"{clean_dir}/")
    parameters_dir = dataset / "parameters"
    file.write_parameters(f"{parameters_dir}/")
    file.write_ground_truths(dataset / "ground_truth")

    records = validate_dataset_dir(dataset)

    assert records[0]["ground_truth_manifest"] == (
        "ground_truth/case.csv/manifest.json"
    )



def test_evaluator_reports_matching_ground_truth_alternative(tmp_path, monkeypatch):
    file = _csv_file(tmp_path)
    addTable(file, n_rows=3, n_cols=5, empty_boundary=True)
    file.filename = "case.csv"
    file.xml.getroot().attrib["filename"] = file.filename

    dataset = tmp_path / "data" / "demo"
    clean_dir = dataset / "clean"
    clean_dir.mkdir(parents=True)
    file.write_clean_csv(f"{clean_dir}/")
    manifest_path = file.write_ground_truths(dataset / "ground_truth")
    candidates = dict(single_table_alternatives(manifest_path))

    loading_dir = tmp_path / "results" / "sut" / "demo" / "loading"
    loading_dir.mkdir(parents=True)
    shutil.copyfile(
        candidates["secondary_only"],
        loading_dir / "case.csv_converted.csv",
    )
    monkeypatch.chdir(tmp_path)

    result = evaluate.evaluate_single_file(
        filename="case.csv",
        dataset="demo",
        sut="sut",
    )

    assert result["sut_correct"] == 1
    assert result["sut_matched_ground_truth"] == "secondary_only"
