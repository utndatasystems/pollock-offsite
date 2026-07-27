import random

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from lxml import etree

from . import polluters_base as pb
from .CSVFile import CSVFile
from .data_types import CellType, parse_cell

# Pollution Utils

def manually_verified(func):
    func.manually_verified = True
    return func

def todo(func):
    func.todo = True
    return func

def _set_polluted_filename(file: CSVFile, filename: str):
    """Keep the CSVFile metadata and XML root filename in sync."""
    file.filename = filename
    file.xml.getroot().attrib["filename"] = filename


def _row_values(file: CSVFile, row=1, table=0):
    """Return value text for every cell in a row. Row uses XPath-style 1-based indexing."""
    root = file.xml.getroot()
    cells = root.xpath(f"//table[{table + 1}]/row[{row}]/cell")
    return ["".join(v.text or "" for v in c if v.tag == "value") for c in cells]


def _safe_row_count(file: CSVFile, table=0):
    return len(file.xml.getroot().xpath(f"//table[{table + 1}]/row"))


def _safe_col_count(file: CSVFile, table=0):
    first_row = file.xml.getroot().xpath(f"//table[{table + 1}]/row[1]")
    return len(first_row[0].xpath("./cell")) if first_row else 0


def _last_data_row(file: CSVFile):
    return max(2, _safe_row_count(file))


def _cell_text(cell) -> str:
    return "".join(v.text or "" for v in cell if v.tag == "value")


def _cell_type(cell) -> str:
    return cell.attrib.get("type") or parse_cell(_cell_text(cell))


def _has_quote_metadata(cell) -> bool:
    return any(child.tag == "quotation_char" for child in cell)


def _quoted_string_cell(file: CSVFile, row: int | None = None, col: int | None = None):
    root = file.xml.getroot()
    row_query = "row[@role='data']" if row is None else f"row[{row}]"
    candidate_rows = root.xpath(f"/*/table[1]/{row_query}")

    for row_node in candidate_rows:
        row_pos = row_node.getparent().index(row_node) + 1
        cells = row_node.xpath("./cell")
        col_range = list(range(1, len(cells) + 1))
        if col is not None and 1 <= col <= len(cells):
            col_range.remove(col)
            col_range.insert(0, col)
        for col_pos in col_range:
            cell = cells[col_pos - 1]
            if (
                _cell_type(cell) == CellType.STRING
                and _cell_text(cell)
                and _has_quote_metadata(cell)
            ):
                return row_pos, col_pos, cell

    raise ValueError("Cannot find a quoted string cell")


def _replace_with_double_escaped_content(file: CSVFile, cell, escaping: str) -> None:
    text = _cell_text(cell)
    role = cell.attrib.get("role")
    for child in list(cell):
        cell.remove(child)
    cell.text = None
    cell.attrib["type"] = CellType.STRING
    if role is not None:
        cell.attrib["role"] = role

    quote = file.quotation_char or '"'
    outer_open = etree.SubElement(cell, "quotation_char")
    outer_open.text = quote

    if escaping == "double_quote":
        escape = quote
    elif escaping == "backslash":
        escape = "\\"
    else:
        raise ValueError("escaping must be 'double_quote' or 'backslash'")

    first_escape = etree.SubElement(cell, "escape_char")
    first_escape.text = escape
    first_value = etree.SubElement(cell, "value")
    first_value.text = quote + text
    second_escape = etree.SubElement(cell, "escape_char")
    second_escape.text = escape
    second_value = etree.SubElement(cell, "value")
    second_value.text = quote

    outer_close = etree.SubElement(cell, "quotation_char")
    outer_close.text = quote


def _variable_column_target(file: CSVFile, row: int | None) -> tuple[int, int]:
    if row is None:
        row = random.randint(1, max(1, _safe_row_count(file) - 1))
    col = random.randrange(_safe_col_count(file))
    return row, col


def _unquoted_list_items(
    file: CSVFile,
    col: int,
    list_delimiter: str,
) -> list[str]:
    """Return distinct, list-safe values observed in a one-based data column."""
    items = []
    unsafe_chars = (
        list_delimiter,
        file.field_delimiter,
        "\r",
        "\n",
        "[",
        "]",
        file.quotation_char,
    )

    for row in range(2, _safe_row_count(file) + 1):
        values = _row_values(file, row=row)
        if col > len(values):
            continue

        value = values[col - 1].strip()
        if (
            value
            and len(value) <= 80
            and not any(char and char in value for char in unsafe_chars)
            and value not in items
        ):
            items.append(value)

    return items


def _unquoted_list_column(file: CSVFile, list_delimiter: str) -> int:
    """Choose a text column whose values make plausible list members."""
    headers = _row_values(file, row=1)
    list_like_hints = (
        "tag",
        "category",
        "type",
        "label",
        "name",
        "color",
        "size",
        "option",
        "code",
        "id",
    )
    free_text_hints = ("comment", "note", "description")
    candidates = []

    for col in range(1, _safe_col_count(file) + 1):
        items = _unquoted_list_items(file, col, list_delimiter)
        if not items:
            continue

        string_ratio = sum(
            parse_cell(item) == CellType.STRING for item in items
        ) / len(items)
        if string_ratio < 0.8:
            continue

        header = headers[col - 1].casefold() if col <= len(headers) else ""
        if any(hint in header for hint in list_like_hints):
            score = 2
        elif any(hint in header for hint in free_text_hints):
            score = 1
        else:
            score = 0
        candidates.append((score, col))

    if not candidates:
        raise ValueError("Cannot create an unquoted list: no suitable text column found")

    best_score = max(score for score, _ in candidates)
    return random.choice([col for score, col in candidates if score == best_score])



# Helpers for categorizing pollutions 

F = TypeVar("F", bound=Callable[..., Any])

def pollution(
    category: str,
    *,
    name: str | None = None,
    version: str | None = None,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        func.pollution_category = category
        func.pollution_name = name
        return func

    return decorator
