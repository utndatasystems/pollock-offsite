from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from . import polluters_base as pb
from .CSVFile import CSVFile

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
