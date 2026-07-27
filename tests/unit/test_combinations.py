from __future__ import annotations

import csv
import json

import pytest

from pollock.CSVFile import CSVFile
from pollock.combinations import apply_pollution_combination
from pollock import polluters_stdlib_v1 as v1
from pollock import polluters_stdlib_v2 as v2
from tests._helpers import make_csv_file, values


def test_apply_pollution_combination_mutates_one_shared_copy():
    source = make_csv_file()
    source_rows = CSVFile.clean_rows(source)

    combined = apply_pollution_combination(
        source,
        [
            (v1.changeRowQuotationMark, {"row": 2, "target_quotation": "'"}),
            (
                v2.mixedDelimiters,
                {
                    "row": 2,
                    "delimiters": [";"],
                    "mode": "whole_row",
                },
            ),
        ],
        filename="combo.csv",
    )

    assert values(source, "//table[1]/row[2]/field_delimiter") == [",", ","]
    assert values(combined, "//table[1]/row[2]/field_delimiter") == [";", ";"]
    assert combined.filename == "combo.csv"
    assert combined.ground_truth_bundle.tables[0].rows == tuple(
        tuple(value for value in row) for row in source_rows
    )
    assert combined.ground_truth_bundle.accept_origin is True
    assert [
        step["function"]
        for step in combined.pollution_combination["pollutions"]
    ] == ["changeRowQuotationMark", "mixedDelimiters"]


def test_apply_pollution_combination_requires_two_pollutions():
    with pytest.raises(ValueError):
        apply_pollution_combination(
            make_csv_file(),
            [(v2.mixedDelimiters, {"row": 2})],
            filename="combo.csv",
        )


def test_combination_provenance_is_written_to_parameters(tmp_path):
    source_path = tmp_path / "source.csv"
    source_path.write_text("name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n")
    source = CSVFile(str(source_path), quote_all=True)
    combined = apply_pollution_combination(
        source,
        [
            (
                v2.mixedDelimiters,
                {"row": 2, "delimiters": [";"], "mode": "whole_row"},
            ),
            (
                v1.changeRowRecordDelimiter,
                {"row": 2, "target_delimiter": "\n"},
            ),
        ],
        filename="combo.csv",
    )

    combined.write_parameters(f"{tmp_path}/")
    parameters = json.loads(
        (tmp_path / "combo.csv_parameters.json").read_text()
    )

    assert [
        step["function"] for step in parameters["combination"]["pollutions"]
    ] == ["mixedDelimiters", "changeRowRecordDelimiter"]


def test_combination_clean_output_reconstructs_source_after_extra_field(tmp_path):
    source_path = tmp_path / "source.csv"
    source_path.write_text("name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n")
    source = CSVFile(str(source_path), quote_all=True)
    combined = apply_pollution_combination(
        source,
        [
            (v2.moreColumns, {"row": 1}),
            (
                v2.mixedDelimiters,
                {"row": 2, "delimiters": [";"], "mode": "whole_row"},
            ),
        ],
        filename="combo.csv",
    )

    combined.write_clean_csv(f"{tmp_path}/")
    with source_path.open(newline="") as source_file:
        source_rows = list(csv.reader(source_file))
    with (tmp_path / "combo.csv").open(newline="") as clean_file:
        clean_rows = list(csv.reader(clean_file))

    assert clean_rows == source_rows


def test_generated_filename_contains_ordered_pollution_parameters(monkeypatch):
    monkeypatch.setattr(v2.random, "randrange", lambda _: 1)
    combined = apply_pollution_combination(
        make_csv_file(),
        [
            (v2.moreColumns, {"row": 1}),
            (
                v2.mixedDelimiters,
                {
                    "row": 2,
                    "delimiters": [";"],
                    "mode": "within_row",
                    "range_within_row": 2,
                },
            ),
        ],
    )

    assert combined.filename == (
        "combo__more_columns_row_1_col_1__"
        "mixed_delimiters_within_row_row_2_range_2_0x3B.csv"
    )
    assert "l3" not in combined.filename
    assert "l4" not in combined.filename
