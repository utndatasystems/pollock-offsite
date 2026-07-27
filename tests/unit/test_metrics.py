from __future__ import annotations

import csv

from pollution import metrics


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def test_compare_files_accepts_empty_cell_for_legacy_deleted_value_gt(tmp_path):
    expected = tmp_path / "file_variable_column_count_row_2_col_1.csv"
    loaded = tmp_path / "loaded.csv"

    write_rows(expected, [["a", "b", "c"], ["1", "3"]])
    write_rows(loaded, [["a", "b", "c"], ["1", "", "3"]])

    assert metrics.compare_files(expected, loaded)


def test_compare_files_accepts_empty_cell_for_split_deleted_value_gt(tmp_path):
    expected = tmp_path / "file_less_columns_deleted_value_row_2_col_1.csv"
    loaded = tmp_path / "loaded.csv"

    write_rows(expected, [["a", "b", "c"], ["1", "3"]])
    write_rows(loaded, [["a", "b", "c"], ["1", "", "3"]])

    assert metrics.compare_files(expected, loaded)


def test_compare_files_does_not_pad_unrelated_files(tmp_path):
    expected = tmp_path / "ordinary.csv"
    loaded = tmp_path / "loaded.csv"

    write_rows(expected, [["a", "b", "c"], ["1", "3"]])
    write_rows(loaded, [["a", "b", "c"], ["1", "", "3"]])

    assert not metrics.compare_files(expected, loaded)



def test_compare_files_requires_empty_cell_at_deleted_column(tmp_path):
    expected = tmp_path / "file_less_columns_deleted_value_row_2_col_1.csv"
    loaded = tmp_path / "loaded.csv"

    write_rows(expected, [["a", "b", "c"], ["1", "3"]])
    write_rows(loaded, [["a", "b", "c"], ["", "1", "3"]])

    assert not metrics.compare_files(expected, loaded)
