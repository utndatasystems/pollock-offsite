"""
Pollock 2.0 polluter tests.

Run with:
    pytest

Or override the module under test:
    POLLUTERS_MODULE=pollock.polluters_stdlib_v2 pytest
"""

from __future__ import annotations

import json

import pytest
from lxml import etree

from tests._helpers import FakeCSVFile, assert_filename_synced, load_polluters_module, row, values

p = load_polluters_module()


def test_multiline_header(csv_file):
    p.multilineHeader(csv_file, header_rows=3, content="Line")

    assert csv_file.row_count == 6
    assert values(csv_file, "//table[1]/row[1]/cell[1]/value") == ["Line1"]
    assert values(csv_file, "//table[1]/row[2]/cell[1]/value") == ["Line2"]
    assert values(csv_file, "//table[1]/row[3]/cell[1]/value") == ["Line3"]
    assert_filename_synced(csv_file, "file_multiline_header")


def test_duplicate_header_as_data_row(csv_file):
    p.duplicateHeaderAsDataRow(csv_file)

    first_data_row = values(csv_file, "//table[1]/row[2]/cell/value")
    assert first_data_row == ["name", "city", "amount"]
    assert csv_file.xml.xpath("//table[1]/row[2]")[0].attrib.get("role") == "data"
    assert_filename_synced(csv_file, "file_duplicate_header_as_data")


def test_extremely_long_fields(csv_file):
    p.extremelyLongFields(csv_file, row=2, col=1, length=128)

    new_value = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    assert len(new_value) == 128
    assert new_value.isalnum()
    assert_filename_synced(csv_file, "file_extremely_long_field")


def test_add_group_section_header(csv_file):
    p.addGroupSectionHeader(csv_file, group_name="Region: North", position=2)

    row_values = values(csv_file, "//table[1]/row[3]/cell/value")
    assert row_values == ["Region: North", "", ""]
    assert csv_file.xml.xpath("//table[1]/row[3]")[0].attrib.get("role") == "section_header"
    assert_filename_synced(csv_file, "file_group_section_header")


def test_add_comment_to_file(csv_file):
    p.addCommentToFile(csv_file, comment="manual note", row=2)

    last_row_values = values(csv_file, "//table[1]/row[2]/cell/value")
    assert last_row_values[-1] == "# manual note"
    assert len(last_row_values) == 4
    assert_filename_synced(csv_file, "file_trailing_comment")


def test_mixed_delimiters(csv_file):
    p.mixedDelimiters(csv_file, row=2, delimiters=[";"], mode="whole_row")

    delimiters = values(csv_file, "//table[1]/row[2]/field_delimiter")
    assert delimiters == [";", ";"]
    assert_filename_synced(csv_file, "file_mixed_delimiters")


def test_unescaped(csv_file):
    content = 'O"Brien, has comma\nand newline'
    p.unescaped(csv_file, row=2, col=2, content=content)

    assert values(csv_file, "//table[1]/row[2]/cell[2]/value") == [content]
    assert_filename_synced(csv_file, "file_unescaped")


def test_double_escaping(csv_file):
    p.doubleEscaping(csv_file, row1=2, row2=3, col=1)

    assert values(csv_file, "//table[1]/row[2]/cell[1]/value") == ['""hi""']
    assert values(csv_file, "//table[1]/row[3]/cell[1]/value") == ['\\"hi\\"']
    assert_filename_synced(csv_file, "file_double_escaping")


def test_variable_column_count(csv_file):
    before_rows = csv_file.row_count
    before_cols = csv_file.col_count

    p.variableColumnCount(csv_file)

    assert csv_file.row_count == before_rows
    assert_filename_synced(csv_file, "file_variable_column_count")
    assert any(
        len(csv_file.xml.xpath(f"//table[1]/row[{i + 1}]/cell")) != before_cols
        for i in range(csv_file.row_count)
    )


@pytest.mark.parametrize(
    "func_name, expected_filename, expected_values",
    [
        ("excelExportAutoformat", "file_excel_autoformat", ["00123", "03/04/05", "1-2"]),
        ("exelExportFormulas", "file_excel_formulas", ["=SUM(A1:A10)", "=A2+B2"]),
        ("typeAmbiguity", "file_type_ambiguity", ["NULL", "N/A", "NaN"]),
    ],
)
def test_row_appending_polluters(csv_file, func_name, expected_filename, expected_values):
    func = getattr(p, func_name)
    before = csv_file.row_count

    func(csv_file)

    expected_delta = {"excelExportAutoformat": 2, "exelExportFormulas": 1, "typeAmbiguity": 4}[func_name]
    assert csv_file.row_count == before + expected_delta
    all_values = values(csv_file, "//table[1]/row/cell/value")
    for expected in expected_values:
        assert expected in all_values
    assert_filename_synced(csv_file, expected_filename)


def test_weird_unicode(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "choice", lambda seq: seq[0])

    before = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    p.weirdUnicode(csv_file, row=1, col=0)
    after = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    assert after != before
    assert after == "FranÃ§ois"
    assert_filename_synced(csv_file, "file_weird_unicode")


def test_invisible_characters(csv_file, monkeypatch):
    monkeypatch.setattr(p.random, "choice", lambda seq: seq[0])

    before = values(csv_file, "//table[1]/row[2]/cell[2]/value")[0]
    p.invisibleCharacters(csv_file, row=1, col=1)
    after = values(csv_file, "//table[1]/row[2]/cell[2]/value")[0]
    assert after != before
    assert after.startswith("\u200b")
    assert_filename_synced(csv_file, "file_invisible_characters")


def test_mixed_timeformats():
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(row(["date", "amount", "note"], role="header"))
    table.append(row(["2024-05-27", "100", "meeting"], role="data"))
    table.append(row(["2024-05-28", "200", "followup"], role="data"))
    file = FakeCSVFile(xml=etree.ElementTree(root))

    before = values(file, "//table[1]/row/cell/value")
    p.mixedTimeformats(file, max_num_to_change=10)
    after = values(file, "//table[1]/row/cell/value")

    assert after != before
    assert_filename_synced(file, "file_mixed_time_formats")


def test_superheader(csv_file):
    p.superheader(csv_file)

    first_row = csv_file.xml.xpath("//table[1]/row[1]")[0]
    assert first_row.attrib.get("role") == "superheader"
    assert values(csv_file, "//table[1]/row[1]/cell/value") == ["Region", "Metrics", "Metrics"]
    assert_filename_synced(csv_file, "file_superheader")


def test_embedded_files(csv_file):
    p.embeddedFiles(csv_file, row=1, col=0)

    payload = values(csv_file, "//table[1]/row[2]/cell[1]/value")[0]
    assert payload
    assert json.loads(payload) is not None
    assert_filename_synced(csv_file, "file_embedded_json_cell")


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
