"""
Pytest tests for the Pollock 2.0 polluter functions.

Usage:
    # From the project root:
    pytest pollock/test_new_polluters.py

    # Or override the module path explicitly:
    POLLUTERS_MODULE=pollock.polluters_stdlib_v2 pytest pollock/test_new_polluters.py

These tests use a minimal CSVFile-like object with an lxml XML tree. The existing
polluters_base helpers operate on duck-typed attributes, so a full CSVFile parser
fixture is not required for structural tests.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from lxml import etree
from lxml.builder import E

# Make `import pollock.polluters_stdlib_v2` work whether pytest is started from
# the project root or from inside the `pollock/` package directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

POLLUTERS_MODULE = os.environ.get("POLLUTERS_MODULE", "pollock.polluters_stdlib_v2")
p = importlib.import_module(POLLUTERS_MODULE)

#TODO: add tests for pollock 1.0 pollutions functions as well

#TODO: add tests for metrics/eval functions as well


@dataclass
class FakeCSVFile:
    xml: etree._ElementTree
    filename: str = "base.csv"
    encoding: str = "utf-8"
    field_delimiter: str = ","
    record_delimiter: str = "\r\n"
    quotation_char: str = '"'
    escape_char: str = "\\"

    @property
    def row_count(self) -> int:
        return len(self.xml.xpath("//table[1]/row"))

    @property
    def col_count(self) -> int:
        first = self.xml.xpath("//table[1]/row[1]")
        return len(first[0].xpath("./cell")) if first else 0


def _cell(value: str, role: str = "data"):
    cell = etree.Element("cell", role=role)
    cell.append(E.value(value))
    return cell


def _row(values: list[str], role: str, field_delimiter=",", record_delimiter="\r\n"):
    row = etree.Element("row", role=role)
    for i, value in enumerate(values):
        row.append(_cell(value, role=role))
        if i < len(values) - 1:
            row.append(E.field_delimiter(field_delimiter))
    row.append(E.record_delimiter(record_delimiter))
    return row


@pytest.fixture
def csv_file() -> FakeCSVFile:
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(_row(["name", "city", "amount"], role="header"))
    table.append(_row(["Alice", "Berlin", "10"], role="data"))
    table.append(_row(["Bob", "Munich", "20"], role="data"))
    return FakeCSVFile(xml=etree.ElementTree(root))


def values(file: FakeCSVFile, xpath: str) -> list[str]:
    return [x.text or "" for x in file.xml.xpath(xpath)]


def assert_filename_synced(file: FakeCSVFile, expected_prefix: str | None = None):
    assert file.filename == file.xml.getroot().attrib["filename"]
    if expected_prefix is not None:
        assert file.filename.startswith(expected_prefix)


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
    assert values(csv_file, "//table[1]/row[3]/cell[1]/value") == ['\\\"hi\\\"']
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
    assert after.startswith("​")
    assert_filename_synced(csv_file, "file_invisible_characters")


def test_mixed_timeformats():
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(_row(["date", "amount", "note"], role="header"))
    table.append(_row(["2024-05-27", "100", "meeting"], role="data"))
    table.append(_row(["2024-05-28", "200", "followup"], role="data"))
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
    # This checks the wrapper works with a plain supported encoding string.
    p.encoding(csv_file, "utf-8")

    assert csv_file.encoding == "utf-8"
    assert csv_file.xml.getroot().attrib["encoding"] == "utf-8"
    assert_filename_synced(csv_file, "file_encoding_utf-8")
