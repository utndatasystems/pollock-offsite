import csv
import json

import pytest

from pollock import polluters_stdlib_v1 as p
from pollock.CSVFile import CSVFile
from pollock.polluters_utils import _row_values
from tests._helpers import make_csv_file


def _make_real_csv(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text(
        "name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n",
        encoding="utf-8",
    )
    return CSVFile(str(source), quote_all=True)


@pytest.mark.parametrize(
    ("n_cols", "expected_header", "expected_data", "kind"),
    [
        (2, ["name", "city"], ["Alice", "Berlin"], "less"),
        (3, ["name", "city", "amount"], ["Alice", "Berlin", "10"], "same"),
        (
            5,
            ["name", "city", "amount", "Related name", "Related city"],
            ["Alice", "Berlin", "10", "Alice", "Berlin"],
            "more",
        ),
    ],
)
def test_add_table_serializes_secondary_schema(
    tmp_path, n_cols, expected_header, expected_data, kind
):
    file = _make_real_csv(tmp_path)

    p.addTable(file, n_rows=3, n_cols=n_cols, empty_boundary=False)

    assert _row_values(file, row=1, table=1) == expected_header
    assert _row_values(file, row=2, table=1) == expected_data
    assert [row.get("role") for row in file.xml.xpath("//table[2]/row")] == [
        "secondary_header",
        "secondary_data",
        "secondary_data",
    ]
    assert f"_{kind}_cols" in file.filename

    polluted_dir = tmp_path / "polluted"
    file.write_csv(str(polluted_dir))
    with (polluted_dir / file.filename).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))

    assert rows[:3] == [
        ["name", "city", "amount"],
        ["Alice", "Berlin", "10"],
        ["Bob", "Munich", "20"],
    ]
    assert rows[3] == expected_header
    assert rows[4] == expected_data


def test_add_table_separator_is_blank_and_clean_csv_is_unchanged(tmp_path):
    file = _make_real_csv(tmp_path)

    p.addTable(file, n_rows=10, n_cols=5, empty_boundary=True)

    assert file.filename == "file_multitable_rows_3_more_cols_separated.csv"
    assert _row_values(file, row=1, table=1) == []
    assert file.xml.xpath("//table[2]/row[1]")[0].get("role") == "secondary_boundary"

    polluted_dir = tmp_path / "polluted"
    file.write_csv(str(polluted_dir))
    with (polluted_dir / file.filename).open(newline="", encoding="utf-8") as stream:
        polluted_rows = list(csv.reader(stream))
    assert polluted_rows[3] == []

    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    file.write_clean_csv(f"{clean_dir}/")
    with (clean_dir / file.filename).open(newline="", encoding="utf-8") as stream:
        clean_rows = list(csv.reader(stream))

    assert clean_rows == [
        ["name", "city", "amount"],
        ["Alice", "Berlin", "10"],
        ["Bob", "Munich", "20"],
    ]

    parameters_dir = tmp_path / "parameters"
    file.write_parameters(f"{parameters_dir}/")
    parameters_path = parameters_dir / f"{file.filename}_parameters.json"
    parameters = json.loads(parameters_path.read_text(encoding="utf-8"))

    assert parameters["header_lines"] == 1
    assert parameters["n_columns"] == 3
    assert parameters["column_names"] == ["name", "city", "amount"]


@pytest.mark.parametrize(("n_rows", "n_cols"), [(0, 3), (3, 0), (-1, 3), (3, -1)])
def test_add_table_rejects_invalid_dimensions(n_rows, n_cols):
    with pytest.raises(ValueError):
        p.addTable(make_csv_file(), n_rows=n_rows, n_cols=n_cols)
