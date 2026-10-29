"""
Pollock 2.0 polluter tests.

Run with:
    pytest

Or override the module under test:
    POLLUTERS_MODULE=pollution.polluters_stdlib_v2 pytest
"""

from __future__ import annotations

import csv
import json

import pytest
from lxml import etree

from pollution.CSVFile import CSVFile
from pollution.polluters_utils import _row_values
from tests._helpers import FakeCSVFile, assert_filename_synced, load_polluters_module, row, values

p = load_polluters_module()


def test_multiline_header():
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    header = row(["name", "city", "amount", "date", "code", "state"], role="header")
    for idx in (3, 4):
        etree.SubElement(header.xpath("./cell")[idx], "quotation_char").text = '"'
    table.append(header)
    table.append(row(["Alice", "Berlin", "10", "2024-01-01", "A1", "DE"], role="data"))
    table.append(row(["Bob", "Munich", "20", "2024-01-02", "B2", "DE"], role="data"))
    csv_file = FakeCSVFile(xml=etree.ElementTree(root))

    p.multilineHeader(csv_file, header_rows=2)

    assert csv_file.row_count == 4
    assert values(csv_file, "//table[1]/row[1]/cell/value") == ["name", "city", "amount"]
    assert values(csv_file, "//table[1]/row[2]/cell/value") == ["date", "code", "state"]
    assert csv_file.xml.xpath("//table[1]/row[2]/cell[1]/quotation_char")
    assert csv_file.xml.xpath("//table[1]/row[2]/cell[2]/quotation_char")
    assert not csv_file.xml.xpath("//table[1]/row[2]/cell[3]/quotation_char")
    assert csv_file.xml.xpath("//table[1]/row[1]")[0].attrib.get("role") == "header"
    assert csv_file.xml.xpath("//table[1]/row[2]")[0].attrib.get("role") == "header"
    assert_filename_synced(csv_file, "file_multiline_header_rows_2")


def test_duplicate_header_as_data_row(csv_file):
    quoted_header_cell = csv_file.xml.xpath("//table[1]/row[1]/cell[2]")[0]
    etree.SubElement(quoted_header_cell, "quotation_char").text = '"'
    etree.SubElement(quoted_header_cell, "quotation_char").text = '"'

    p.duplicateHeaderIntoRows(csv_file)

    first_data_row = values(csv_file, "//table[1]/row[2]/cell/value")
    assert first_data_row == ["name", "city", "amount"]
    assert csv_file.xml.xpath("//table[1]/row[2]")[0].attrib.get("role") == "data"
    assert csv_file.xml.xpath("//table[1]/row[2]/cell[2]")[0].attrib.get("role") == "data"
    assert values(csv_file, "//table[1]/row[2]/cell[2]/quotation_char") == ['"', '"']
    assert values(csv_file, "//table[1]/row[1]/cell[2]/quotation_char") == ['"', '"']
    assert_filename_synced(csv_file, "file_duplicate_header_as_data")


def test_extremely_long_fields(csv_file):
    p.extremelyLongFields(csv_file, row=2, col=1, length=128)

    new_value = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    assert len(new_value) == 128
    assert new_value.isalnum()
    assert_filename_synced(csv_file, "file_extremely_long_field")


def test_add_comment_to_file(csv_file):
    p.addTrailingCommentToFile(csv_file, comment="manual note", row=2)

    last_row_values = values(csv_file, "//table[1]/row[2]/cell/value")
    assert last_row_values[-1] == "# manual note"
    assert len(last_row_values) == 4
    assert_filename_synced(csv_file, "file_trailing_comment_2")


def test_mixed_delimiters(csv_file, monkeypatch):
    expected_rows = [
        ["name", "city", "amount"],
        ["Alice", "Berlin", "10"],
        ["Bob", "Munich", "20"],
    ]
    monkeypatch.setattr(CSVFile, "clean_rows", lambda file: expected_rows)

    p.mixedDelimiters(csv_file, row=2, delimiters=[";"], mode="whole_row")

    delimiters = values(csv_file, "//table[1]/row[2]/field_delimiter")
    assert delimiters == [";", ";"]
    bundle = csv_file.ground_truth_bundle
    assert bundle.canonical == "recovered_original_table"
    assert bundle.accept_origin is True
    assert bundle.tables[0].id == "recovered_original_table"
    assert bundle.tables[0].rows == (
        ("name", "city", "amount"),
        ("Alice", "Berlin", "10"),
        ("Bob", "Munich", "20"),
    )
    assert_filename_synced(csv_file, "file_mixed_delimiters")


def test_unescaped(csv_file):
    csv_file.xml.xpath("//table[1]/row[2]/cell[2]")[0].attrib["type"] = "TYPE_STRING"
    p.unescapedMultiLineString(csv_file, row=2, col=2)

    assert values(csv_file, "//table[1]/row[2]/cell[2]/value") == ["Ber\nlin"]
    assert_filename_synced(csv_file, "file_unescaped_multiline_string_row_2_col_2")


def _quote_cell(cell, quote='"'):
    text = cell.xpath("./value")[0].text or ""
    for child in list(cell):
        cell.remove(child)
    open_quote = etree.SubElement(cell, "quotation_char")
    open_quote.text = quote
    value = etree.SubElement(cell, "value")
    value.text = text
    close_quote = etree.SubElement(cell, "quotation_char")
    close_quote.text = quote


def _cell_output(file, xpath: str) -> str:
    cell = file.xml.xpath(xpath)[0]
    return "".join(child.text or "" for child in cell)


def test_double_escaping_uses_one_quoted_string_cell(csv_file):
    _quote_cell(csv_file.xml.xpath("//table[1]/row[2]/cell[1]")[0])

    p.doubleEscaping(csv_file, row=2, col=1, escaping="double_quote")

    assert _cell_output(csv_file, "//table[1]/row[2]/cell[1]") == '"""Alice"""'
    assert values(csv_file, "//table[1]/row[3]/cell[1]/value") == ["Bob"]
    assert_filename_synced(csv_file, "file_double_escaping_double_quote_row_2_col_1")


def test_double_escaping_falls_back_to_quoted_string_cell(csv_file):
    _quote_cell(csv_file.xml.xpath("//table[1]/row[2]/cell[1]")[0])

    p.doubleEscaping(csv_file, row=2, col=3, escaping="backslash")

    assert _cell_output(csv_file, "//table[1]/row[2]/cell[1]") == '"\\"Alice\\""'
    assert values(csv_file, "//table[1]/row[2]/cell[3]/value") == ["10"]
    assert values(csv_file, "//table[1]/row[3]/cell[1]/value") == ["Bob"]
    assert_filename_synced(csv_file, "file_double_escaping_backslash_row_2_col_1")


def test_more_columns(csv_file):
    before_rows = csv_file.row_count
    before_cols = csv_file.col_count

    p.moreColumns(csv_file, row=1)

    assert csv_file.row_count == before_rows
    assert_filename_synced(csv_file, "file_more_columns")
    assert len(csv_file.xml.xpath("//table[1]/row[2]/cell")) == before_cols + 1


def test_less_columns_deleted_values(csv_file):
    before_rows = csv_file.row_count
    before_cols = csv_file.col_count

    p.lessColumnsDeletedValues(csv_file, row=1)

    assert csv_file.row_count == before_rows
    assert_filename_synced(csv_file, "file_less_columns_deleted_value")
    assert len(csv_file.xml.xpath("//table[1]/row[2]/cell")) == before_cols - 1
    assert csv_file.xml.getroot().attrib["ground_truth_insert_empty_row"] == "1"
    assert "ground_truth_insert_empty_col" in csv_file.xml.getroot().attrib


def test_less_columns_deleted_values_clean_gt_is_rectangular(tmp_path, monkeypatch):
    monkeypatch.setattr(p.random, "randrange", lambda stop: 1)
    root = etree.Element("file", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(row(["name", "city", "amount"], role="header"))
    table.append(row(["Alice", "Berlin", "10"], role="data"))
    csv_file = FakeCSVFile(xml=etree.ElementTree(root))

    p.lessColumnsDeletedValues(csv_file, row=1)
    CSVFile.write_clean_csv(csv_file, str(tmp_path) + "/")

    with (tmp_path / csv_file.filename).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    assert rows == [["name", "city", "amount"], ["Alice", "", "10"]]

    bundle = csv_file.ground_truth_bundle
    assert bundle.canonical == "rectangular_missing_value"
    assert bundle.accept_origin is False
    assert [alternative.id for alternative in bundle.alternatives] == [
        "rectangular_missing_value",
        "jagged_deleted_value",
    ]
    assert bundle.tables[0].rows == (
        ("name", "city", "amount"),
        ("Alice", "", "10"),
    )
    assert bundle.tables[1].rows == (
        ("name", "city", "amount"),
        ("Alice", "10"),
    )


def test_variable_column_count_compatibility_wrapper(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "randint", lambda start, stop: 1)
    monkeypatch.setattr(p.random, "randrange", lambda stop: 1)

    p.variableColumnCount(csv_file)

    assert_filename_synced(csv_file, "file_less_columns_deleted_value")


@pytest.mark.parametrize(
    "func_name, expected_filename, expected_values",
    [
        ("excelExportAutoformat", "file_excel_autoformat", ["00123", "03/04/05", "1-2"]),
        ("spreadsheetFormulasInCSV", "file_excel_formulas", ["=SUM(A1:A10)", "=A2+B2"]),
        pytest.param(
            "typeAmbiguity",
            "file_type_ambiguity",
            ["NULL", "N/A", "NaN"],
            marks=pytest.mark.xfail(reason="typeAmbiguity is unfinished", strict=True),
        ),
    ],
)
def test_row_appending_polluters(csv_file, func_name, expected_filename, expected_values):
    func = getattr(p, func_name)
    before = csv_file.row_count

    func(csv_file)

    expected_delta = {"excelExportAutoformat": 2, "spreadsheetFormulasInCSV": 1, "typeAmbiguity": 4}[func_name]
    assert csv_file.row_count == before + expected_delta
    all_values = values(csv_file, "//table[1]/row/cell/value")
    for expected in expected_values:
        assert expected in all_values
    assert_filename_synced(csv_file, expected_filename)


def test_weird_unicode(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "choice", lambda seq: seq[0])

    before = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    p.weirdUnicode(csv_file, row=2, col=1)
    after = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    assert after != before
    assert after == "FranÃ§ois"
    assert_filename_synced(csv_file, "file_weird_unicode")


def test_invisible_characters(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "choice", lambda seq: seq[0])

    before = values(csv_file, "//table[1]/row[2]/cell[2]/value")[0]
    p.invisibleCharacters(csv_file, row=2, col=2)
    after = values(csv_file, "//table[1]/row[2]/cell[2]/value")[0]
    assert after != before
    assert after.startswith("\u200b")
    assert_filename_synced(csv_file, "file_invisible_characters")


@pytest.mark.parametrize(
    ("temporal_format", "strftime_format"),
    list(p.COMMON_ALTERNATIVE_TEMPORAL_FORMATS.items()),
)
def test_mixed_timeformats(temporal_format, strftime_format):
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(row(["date", "time", "amount", "note"], role="header"))
    table.append(row(["27/05/2024", "00:15", "100", "meeting"], role="data"))
    table.append(row(["28/05/2024", "00:30", "200", "followup"], role="data"))
    file = FakeCSVFile(xml=etree.ElementTree(root))
    before = values(file, "//table[1]/row/cell/value")
    times_before = values(file, "//table[1]/row/cell[2]/value")
    p.mixedTimeformats(
        file,
        temporal_format=temporal_format,
        max_num_to_change=10,
    )
    after = values(file, "//table[1]/row/cell/value")

    assert after != before
    assert values(file, "//table[1]/row/cell[2]/value") == times_before
    changed_dates = [
        (old, new)
        for old, new in zip(before[4::4], after[4::4])
        if old != new
    ]
    assert len(changed_dates) == 1
    old, new = changed_dates[0]
    assert new == p.parse(old, fuzzy=False, dayfirst=True).strftime(strftime_format)
    assert file.ground_truth_bundle.accept_origin is True
    assert file.ground_truth_bundle.canonical == "temporal_values_as_strings"
    quoted_cells = file.xml.xpath(
        "//table[1]/row/cell[quotation_char]"
    )
    if temporal_format == "long_month_name":
        assert len(quoted_cells) == 1
    else:
        assert quoted_cells == []
    assert_filename_synced(file, f"file_mixed_time_formats_{temporal_format}")


def test_mixed_timeformats_rejects_unknown_format(csv_file):
    with pytest.raises(ValueError, match="Unknown temporal_format"):
        p.mixedTimeformats(csv_file, temporal_format="not_a_format")


def test_superheader(csv_file, monkeypatch):
    monkeypatch.setattr(
        CSVFile,
        "clean_rows",
        lambda file: [
            ["name", "city", "amount"],
            ["Alice", "Berlin", "10"],
            ["Bob", "Munich", "20"],
        ],
    )
    p.superheader(csv_file, groups={"Region": [0], "Metrics": [1, 2]}, sparse=False)

    first_row = csv_file.xml.xpath("//table[1]/row[1]")[0]
    assert first_row.attrib.get("role") == "superheader"
    assert values(csv_file, "//table[1]/row[1]/cell/value") == ["Region", "Metrics", "Metrics"]
    assert_filename_synced(csv_file, "file_superheader_repeated_region_cols_0_group_metrics_cols_1-2")


def test_embedded_json_extract_collapses_in_place_by_default(csv_file):
    p.embeddedJSON(csv_file, row=1, start_col=1, l_col=2)

    row_values = _row_values(csv_file, row=2)
    assert row_values[0] == "Alice"
    assert json.loads(row_values[1]) == {"city": "Berlin", "amount": "10"}
    assert_filename_synced(csv_file, "file_embedded_json_cell_1_1_len_2")


def test_bom_marker(csv_file):
    p.bomMarker(csv_file)

    assert csv_file.xml.getroot().attrib["bom"] == "utf-8"
    assert_filename_synced(csv_file, "file_utf8_bom")


def test_collations(csv_file):
    p.collations(csv_file)

    all_values = values(csv_file, "//table[1]/row/cell[1]/value")
    for expected in ["straße", "Müller", "ä", "Ångström", "é", "İstanbul", "ß", "Özil", "Æ"]:
        assert expected in all_values
    assert_filename_synced(csv_file, "file_collation_edge_cases")


def test_mixed_types(csv_file):
    before = csv_file.row_count
    p.mixedTypes(csv_file)

    assert csv_file.row_count == before + 5
    assert_filename_synced(csv_file, "file_mixed_types")


def test_unquoted_list_uses_values_from_explicit_column(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "sample", lambda items, k: items[:k])

    p.unquotedList(csv_file, row=2, col=2, list_len=2)

    assert values(csv_file, "//table[1]/row[2]/cell[2]/value") == [
        "[Berlin,Munich]"
    ]
    assert_filename_synced(csv_file, "file_unquoted_lists_row_2_col_2")

    p.unquotedList(csv_file, row=2, col=3, list_len=2)

    assert values(csv_file, "//table[1]/row[2]/cell[3]/value") == ["[10,20]"]
    assert_filename_synced(csv_file, "file_unquoted_lists_row_2_col_3")


def test_unquoted_list_prefers_list_like_text_column(monkeypatch):
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(row(["date", "quantity", "category", "description"], role="header"))
    table.append(row(["2024-05-27", "10", "shoes", "Waterproof trail shoes"], role="data"))
    table.append(row(["2024-05-28", "20", "jackets", "Lightweight running jacket"], role="data"))
    file = FakeCSVFile(xml=etree.ElementTree(root))
    monkeypatch.setattr(p.random, "choice", lambda items: items[0])
    monkeypatch.setattr(p.random, "sample", lambda items, k: items[:k])

    p.unquotedList(file, row=2, list_len=2)

    assert values(file, "//table[1]/row[2]/cell[3]/value") == [
        "[shoes,jackets]"
    ]
    assert values(file, "//table[1]/row[2]/cell[2]/value") == ["10"]
    assert_filename_synced(file, "file_unquoted_lists_row_2_col_3")


def test_add_table_sideways(csv_file):
    p.addTableSideways(csv_file, n_rows=2, n_cols=3)

    tables = csv_file.xml.xpath("//table")
    assert len(tables) == 2
    sideways_rows = csv_file.xml.xpath("//table[2]/row")
    assert len(sideways_rows) == 3
    assert values(csv_file, "//table[2]/row[1]/cell/value") == ["name", "Alice"]
    assert values(csv_file, "//table[2]/row[2]/cell/value") == ["city", "Berlin"]
    assert values(csv_file, "//table[2]/row[3]/cell/value") == ["amount", "10"]
    assert_filename_synced(csv_file, "file_multitable_sideways")


def test_encoding_alias(csv_file):
    p.encoding(csv_file, "utf-8")

    assert csv_file.encoding == "utf-8"
    assert csv_file.xml.getroot().attrib["encoding"] == "utf-8"
    assert_filename_synced(csv_file, "file_encoding_utf-8")


@pytest.mark.parametrize(
    "blank_line, expected_new_rows, expected_prefix",
    [
        (False, 1, "file_footnote_1"),
        (True, 2, "file_footnote_1_blank_line"),
    ],
)
def test_add_footnote(csv_file, blank_line, expected_new_rows, expected_prefix):
    before = csv_file.row_count

    p.addFootnote(csv_file, blank_line=blank_line, cell_content="FOOTNOTE")

    assert csv_file.row_count == before + expected_new_rows

    # The last row is always the footnote content row
    last_row_index = csv_file.row_count
    last_row_values = values(csv_file, f"//table[1]/row[{last_row_index}]/cell/value")

    # Single-cell footnote
    assert last_row_values == ["FOOTNOTE"]

    if blank_line:
        # The second-to-last row is a truly blank line — no cells at all
        separator_index = csv_file.row_count - 1
        separator_values = values(csv_file, f"//table[1]/row[{separator_index}]/cell/value")
        assert separator_values == []

    assert_filename_synced(csv_file, expected_prefix)


def test_whitespace_table_can_quote_empty_last_column():
    root = etree.Element("file", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    header = row(["Name", "Comments"], role="header")
    data = row(["Alice", ""], role="data")
    header.xpath("./cell")[0].attrib["type"] = "TYPE_STRING"
    header.xpath("./cell")[1].attrib["type"] = "TYPE_STRING"
    data.xpath("./cell")[0].attrib["type"] = "TYPE_STRING"
    data.xpath("./cell")[1].attrib["type"] = "TYPE_EMPTY"
    table.append(header)
    table.append(data)
    csv_file = FakeCSVFile(xml=etree.ElementTree(root))

    p.tableToWhitespaceFormattedTable(
        csv_file,
        pad_cells=True,
        quote_strings=True,
        quote_empty_last_column=True,
    )

    comments_cell = csv_file.xml.xpath("//table[1]/row[2]/cell[2]")[0]
    assert comments_cell.attrib["type"] == "TYPE_STRING"
    assert _cell_output(csv_file, "//table[1]/row[2]/cell[2]") == '""'
    assert_filename_synced(
        csv_file,
        "file_whitespace_delimiter_cells_quoted_empty_last_column_padded.csv",
    )
