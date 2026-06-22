from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from lxml.builder import E

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_polluters_module(default: str = "pollock.polluters_stdlib_v2"):
    """Import the polluters module selected for the current test run."""
    module_name = os.environ.get("POLLUTERS_MODULE", default)
    return importlib.import_module(module_name)


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
        """Return the number of rows currently stored in the fake CSV."""
        return len(self.xml.xpath("//table[1]/row"))

    @property
    def col_count(self) -> int:
        """Return the number of cells in the first row of the fake CSV."""
        first = self.xml.xpath("//table[1]/row[1]")
        return len(first[0].xpath("./cell")) if first else 0


def cell(value: str, role: str = "data"):
    """Create a CSV cell element that stores the given value."""
    node = etree.Element("cell", role=role)
    node.append(E.value(value))
    return node


def row(values: list[str], role: str, field_delimiter=",", record_delimiter="\r\n"):
    """Create a CSV row element with delimiters between cells."""
    node = etree.Element("row", role=role)
    for i, value in enumerate(values):
        node.append(cell(value, role=role))
        if i < len(values) - 1:
            node.append(E.field_delimiter(field_delimiter))
    node.append(E.record_delimiter(record_delimiter))
    return node


def make_csv_file() -> FakeCSVFile:
    """Create a small in-memory CSV document for tests."""
    root = etree.Element("csv", filename="base.csv", encoding="utf-8")
    table = etree.SubElement(root, "table")
    table.append(row(["name", "city", "amount"], role="header"))
    table.append(row(["Alice", "Berlin", "10"], role="data"))
    table.append(row(["Bob", "Munich", "20"], role="data"))
    return FakeCSVFile(xml=etree.ElementTree(root))


def values(file: FakeCSVFile, xpath: str) -> list[str]:
    """Return text values from the XML nodes matched by an XPath expression."""
    return [x.text or "" for x in file.xml.xpath(xpath)]


def assert_filename_synced(file: FakeCSVFile, expected_prefix: str | None = None):
    """Assert that the cached filename matches the XML filename attribute."""
    assert file.filename == file.xml.getroot().attrib["filename"]
    if expected_prefix is not None:
        assert file.filename.startswith(expected_prefix)
