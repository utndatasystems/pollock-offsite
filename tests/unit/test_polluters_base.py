from __future__ import annotations

from lxml import etree

from pollock import polluters_base as pb
from tests._helpers import FakeCSVFile, cell, make_csv_file, row, values


def _row_values(file: FakeCSVFile, row_number: int) -> list[str]:
    """Return the visible cell values for a 1-based row number."""
    return values(file, f"//table[1]/row[{row_number}]/cell/value")


def _row_roles(file: FakeCSVFile) -> list[str]:
    """Return the role attribute for every row in the first table."""
    return [node.get("role", "") for node in file.xml.xpath("//table[1]/row")]


def _field_delimiters(file: FakeCSVFile, row_number: int) -> list[str]:
    """Return the field delimiter text for a single 1-based row number."""
    return values(file, f"//table[1]/row[{row_number}]/field_delimiter")


def test_insert_value_cell_replaces_existing_children():
    """insert_value_cell should keep only a single value child with new text."""
    file = make_csv_file()
    noisy_cell = cell("old value")
    noisy_cell.append(etree.Element("extra"))

    pb.insert_value_cell(file, noisy_cell, "new value")

    assert [child.tag for child in noisy_cell] == ["value"]
    assert noisy_cell.find("value").text == "new value"
    assert noisy_cell.text is None


def test_get_cell_value_reads_the_text_inside_value_nodes():
    """get_cell_value should return the text stored in the cell value node."""
    file = make_csv_file()
    first_data_cell = file.xml.xpath("//table[1]/row[2]/cell")[0]

    assert pb.get_cell_value(first_data_cell) == "Alice"


def test_change_cell_updates_one_cell_without_changing_the_row_shape():
    """changeCell should replace one cell value and leave the other cells alone."""
    file = make_csv_file()

    pb.changeCell(file, row=2, col=2, new_content="Oslo")

    assert _row_values(file, 2) == ["Alice", "Oslo", "10"]
    assert _field_delimiters(file, 2) == [",", ","]


def test_get_cell_returns_none_when_the_cell_does_not_exist():
    """getCell should return None when the requested location is out of range."""
    file = make_csv_file()

    assert pb.getCell(file, row=20, col=20) is None


def test_get_row_returns_a_copy_and_can_detach_the_original_row():
    """getRow should return a copy and optionally remove the original row."""
    file = make_csv_file()

    row_copy = pb.getRow(file, row=1, detach=True)

    assert _row_values(file, 1) == ["name", "city", "amount"]
    assert _row_values(file, 2) == ["Bob", "Munich", "20"]
    assert len(file.xml.xpath("//table[1]/row")) == 2
    assert [value.text for value in row_copy.xpath("./cell/value")] == ["Alice", "Berlin", "10"]


def test_insert_row_places_a_row_at_the_requested_position():
    """insertRow should place an existing row node at the chosen position."""
    file = make_csv_file()
    new_row = row(["Carla", "Hamburg", "30"], role="data")

    pb.insertRow(file, new_row, position=1)

    assert _row_values(file, 1) == ["name", "city", "amount"]
    assert _row_values(file, 2) == ["Carla", "Hamburg", "30"]
    assert _row_values(file, 3) == ["Alice", "Berlin", "10"]


def test_move_row_reorders_an_existing_row():
    """moveRow should move one row to a new position in the table."""
    file = make_csv_file()

    pb.moveRow(file, src=2, dst=1)

    assert _row_values(file, 1) == ["name", "city", "amount"]
    assert _row_values(file, 2) == ["Bob", "Munich", "20"]
    assert _row_values(file, 3) == ["Alice", "Berlin", "10"]


def test_add_rows_inserts_a_new_row_with_the_requested_content():
    """addRows should create a new row with the provided cell content."""
    file = make_csv_file()

    pb.addRows(file, cell_content="PAD", n_rows=1, position=1, role="spurious")

    assert _row_roles(file) == ["header", "spurious", "data", "data"]
    assert _row_values(file, 2) == ["PAD", "PAD", "PAD"]


def test_delete_rows_removes_the_requested_rows():
    """deleteRows should remove each row listed in rows_to_delete."""
    file = make_csv_file()

    pb.deleteRows(file, rows_to_delete=[1])

    assert _row_values(file, 1) == ["name", "city", "amount"]
    assert _row_values(file, 2) == ["Bob", "Munich", "20"]
    assert len(file.xml.xpath("//table[1]/row")) == 2


def test_delete_cell_and_delimiter_removes_one_cell_cleanly():
    """deleteCellAndDelimiter should remove the chosen cell and one separator."""
    file = make_csv_file()

    pb.deleteCellAndDelimiter(file, row=1, col=1)

    assert _row_values(file, 2) == ["Alice", "10"]
    assert _field_delimiters(file, 2) == [","]


def test_delete_cells_with_star_removes_every_cell_in_the_row():
    """deleteCells should be able to remove every cell in a selected row."""
    file = make_csv_file()

    pb.deleteCells(file, row=2, col="*")

    assert values(file, "//table[1]/row[2]/cell/value") == []
    assert _field_delimiters(file, 2) == [",", ","]


def test_delete_columns_removes_a_column_from_every_row():
    """deleteColumns should remove the same column from the full table."""
    file = make_csv_file()

    pb.deleteColumns(file, col=[1])

    assert _row_values(file, 1) == ["name", "amount"]
    assert _row_values(file, 2) == ["Alice", "10"]
    assert _row_values(file, 3) == ["Bob", "20"]


def test_change_delimiter_updates_one_separator():
    """changeDelimiter should update only one chosen field delimiter."""
    file = make_csv_file()

    pb.changeDelimiter(file, row=2, col=1, new_delimiter=";")

    assert _field_delimiters(file, 1) == [",", ","]
    assert _field_delimiters(file, 2) == [";", ","]
    assert _field_delimiters(file, 3) == [",", ","]


def test_change_column_delimiters_updates_the_same_separator_in_every_row():
    """changeColumnDelimiters should update the requested column for all rows."""
    file = make_csv_file()

    pb.changeColumnDelimiters(file, col=1, new_delimiter=";")

    assert _field_delimiters(file, 1) == [";", ","]
    assert _field_delimiters(file, 2) == [";", ","]
    assert _field_delimiters(file, 3) == [";", ","]


def test_find_matching_cells_returns_row_and_column_indexes():
    """findMatchingCells should report row and column indexes for matching cells."""
    file = make_csv_file()

    matches = pb.findMatchingCells(file, lambda value, row_idx, col_idx: value == "20")

    assert matches == {(2, 2, "20")}


def test_get_row_cells_returns_only_cell_nodes():
    """getRowCells should return the cell elements from a row in order."""
    file = make_csv_file()

    row_cells = pb.getRowCells(file, row=1)

    assert [node.tag for node in row_cells] == ["cell", "cell", "cell"]
    assert [pb.get_cell_value(node) for node in row_cells] == ["Alice", "Berlin", "10"]
