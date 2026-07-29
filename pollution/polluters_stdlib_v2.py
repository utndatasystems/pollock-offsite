import random
import unicodedata
import string
import json
import time
import warnings
from copy import deepcopy
from lxml import etree
from .CSVFile import CSVFile
from .ground_truth import (
    GroundTruthAlternative,
    GroundTruthBundle,
    GroundTruthTable,
)
from lxml.builder import E
from .randdata import (
    randomString,
    randomDateStr,
    randomType,
    randomInt,
    randomLongOfType,
)
from .data_types import CellType, parse_cell
from dateutil.parser import parse

from . import constants
from . import polluters_base as pb
from pollution.polluters_utils import (
    _set_polluted_filename,
    _row_values,
    _safe_row_count,
    _safe_col_count,
    _last_data_row,
    _quoted_string_cell,
    _replace_with_double_escaped_content,
    _variable_column_target,
    _unquoted_list_items,
    _unquoted_list_column,
    pollution
)

@pollution(
    category="File Segmentation and Table-Boundary", name="Side-by-Side Tables")
def addTableSideways( # this is wrong
    file: CSVFile, n_rows, n_cols, random_content=False, empty_boundary=True
):
    """
    Adds a second table sideways, i.e. as additional columns to the existing rows.

    The added block has n_rows rows and n_cols columns.
    If random_content is False, values are copied from the top-left n_rows x n_cols
    area of the original table. If random_content is True, random strings are used.

    If empty_boundary is True, one empty separator column is inserted between the
    original table and the sideways table.
    """
    root = file.xml.getroot()
    old_table = root.xpath("//table[1]")[0]

    source_rows = old_table.xpath("./row")
    available_rows = len(source_rows)

    if available_rows == 0:
        _set_polluted_filename(
            file, f"file_multitable_sideways_rows_{n_rows}_cols_{n_cols}.csv"
        )
        return

    n_rows = min(n_rows, available_rows)
    n_cols = min(n_cols, file.col_count)

    if empty_boundary:
        pb.addColumns(
            file,
            position=file.col_count,
            n_cols=1,
            col_names=[""],
            cell_content=[""] * (len(source_rows) - 1),
            role=["spurious"] * len(source_rows),
            table=0,
        )

    new_table = etree.SubElement(root, "table")
    for c_idx in range(n_cols):
        if random_content:
            row_values = [
                "".join(random.choices(string.ascii_letters + string.digits, k=8))
                for _ in range(n_rows)
            ]
        else:
            row_values = []
            for r_idx in range(n_rows):
                cells = source_rows[r_idx].xpath("./cell")
                if c_idx < len(cells):
                    value = "".join(v.text or "" for v in cells[c_idx] if v.tag == "value")
                else:
                    value = ""
                row_values.append(value)

        pb.addRows(
            file,
            cell_content=row_values,
            n_rows=1,
            position=len(new_table),
            col_count=len(row_values),
            role="data" if c_idx else "header",
            table=1,
        )

    _set_polluted_filename(
        file,
        f"file_multitable_sideways_rows_{n_rows}_cols_{n_cols}"
        f"{'_random' if random_content else ''}"
        f"{'_separated' if empty_boundary else ''}.csv",
    )


@pollution(category="Header and Schema-Layout", name="Super-Headers")
def multilineHeader(
    file: CSVFile,
    header_rows: int = 3,
    **kwargs,
):
    """Split the original header row across multiple header rows.

    Quoted source header cells keep their quotation markers in the output.
    """
    if header_rows < 1:
        raise ValueError("header_rows must be at least 1")

    root = file.xml.getroot()
    table = root.xpath("//table[1]")[0]
    header_rows_nodes = root.xpath("//table[1]/row[1]")
    if not header_rows_nodes:
        raise ValueError("Cannot create multiline header: first row is empty or missing")

    header_cells = header_rows_nodes[0].xpath("./cell")
    if not header_cells:
        raise ValueError("Cannot create multiline header: first row has no cells")

    col_count = len(header_cells)
    base, remainder = divmod(col_count, header_rows)
    start = 0
    split_rows = []

    for i in range(header_rows):
        chunk_size = base + (1 if i < remainder else 0)
        chunk = header_cells[start : start + chunk_size]
        start += chunk_size
        split_rows.append(chunk)

    pb.deleteRows(file, rows_to_delete=[0])

    for chunk in reversed(split_rows):
        row = etree.Element("row", role="header")
        for j, cell in enumerate(chunk):
            text = "".join(v.text or "" for v in cell if v.tag == "value")
            quoted = bool(cell.xpath("./quotation_char"))
            row.append(
                pb.create_cell(
                    field_delimiter=file.field_delimiter,
                    quotation_char=file.quotation_char,
                    escape_char=file.escape_char,
                    text=text,
                    role="header",
                    should_quote=quoted,
                )
            )
            if j < len(chunk) - 1:
                row.append(E.field_delimiter(file.field_delimiter))

        row.append(E.record_delimiter(file.record_delimiter))
        table.insert(0, row)

    file.ground_truth_bundle = GroundTruthBundle.single(
            CSVFile.clean_rows(file),
            accept_origin=True,)
    _set_polluted_filename(file, f"file_multiline_header_rows_{header_rows}.csv",)


@pollution(category="Undefined", name="duplicateHeaderIntoRows")
def duplicateHeaderIntoRows(file: CSVFile, n_duplicates: int = 1):  # checked manually
    """Duplicates the header row as data rows directly below the header.

    The duplicate preserves the header row's concrete CSV syntax, including
    quotation markers, while changing row/cell roles so it is treated as data.
    """
    if n_duplicates < 1:
        raise ValueError("n_duplicates must be at least 1")

    root = file.xml.getroot()
    table_nodes = root.xpath("/*/table[1]")
    header_nodes = root.xpath("/*/table[1]/row[1]")
    if not table_nodes or not header_nodes or not header_nodes[0].xpath("./cell"):
        raise ValueError("Cannot duplicate header: first row is empty or missing")

    table = table_nodes[0]
    header = header_nodes[0]
    for _ in range(n_duplicates):
        duplicate = deepcopy(header)
        duplicate.attrib["role"] = "data"
        for cell in duplicate.xpath("./cell"):
            cell.attrib["role"] = "data"
        table.insert(1, duplicate)

    suffix = "" if n_duplicates == 1 else f"_{n_duplicates}x"

    file.ground_truth_bundle = GroundTruthBundle.single(CSVFile.clean_rows(file), accept_origin=True,)
    _set_polluted_filename(file, f"file_duplicate_header_as_data{suffix}.csv")

@pollution(category="Operational Scale Stressor", name="Extreme Field Length")
def extremelyLongFields(
    file: CSVFile, row=1, col=1, length=50 * 1024 * 1024):
    """Replaces a cell with an extremely long random alphanumeric field."""
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    #Instead of creating a new random string, take the original content and repeat it until it reaches the desired length
    original_content = pb.getCell(file, row, col)

    #TODO: Strip original content such that we don't run into escaping problems.
    new_content = (original_content * (length // len(original_content) + 1))[:length]
    
    pb.changeCell(
        file,
        row=row,
        col=col,
        new_content=new_content,
        
    )
    file.ground_truth_bundle = GroundTruthBundle.single(
            CSVFile.clean_rows(file),
            accept_origin=False,)
    _set_polluted_filename(
        file, f"file_extremely_long_field_row_{row}_col_{col}_len_{length}.csv")


@pollution(category="File Segmentation and Table-Boundary", name="Inline-End Comments")
def addTrailingCommentToFile(
    file: CSVFile,
    comment="This is a comment.",
    row: int | None = None,
    comment_marker: str = "#",
    space=" ",
):  # checked manually
    """Adds a comment-like trailing field to a row."""
    if row is None:
        row = random.randint(1, _safe_row_count(file))

    pb.addCells(
        file,
        row=row,
        position=file.col_count,
        n_cells=1,
        content=f"{comment_marker}{space}{comment}",
        role="comment",
    )

    # Remove the delimiter before the newly inserted comment cell
    root = file.xml.getroot()
    row_xml = root.xpath(f"//row[{row}]")[0]

    delimiters = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"]
    if delimiters:
        del row_xml[delimiters[-1]]

    _set_polluted_filename(file, f"file_trailing_comment_{row}.csv")


@pollution(category="Undefined", name="commentRow")
def commentRow(
    file: CSVFile, row: int | None = None, comment_marker: str = "#", space=" "
):
    """
    Simulate a commented-out CSV row by prefixing the first cell with a comment
    marker (e.g. '#', '//', ';').

    Args:
        file: CSVFile to modify.
        row: One-based row index to comment out. If None, a random non-header row is chosen.
        comment_marker: Marker used to indicate a comment.
        space: Optional separator between the marker and the original value.
    """
    if row is None:
        row = random.randint(2, _safe_row_count(file))  # skip header (row 1)

    old_value = pb.getCell(file, row, col=1)
    pb.changeCell(
        file,
        row=row,
        col=1,
        new_content=f"{comment_marker}{space}{old_value}",
    )

    file.ground_truth_bundle = GroundTruthBundle.single(CSVFile.clean_rows(file),accept_origin=False,)
    _set_polluted_filename(file, f"file_commented_row_{row}.csv")


@pollution(category="Dialect and Lexical-Syntax", name="Mixed Delimiters")
def mixedDelimiters(  # checked manually
    file: CSVFile,
    row=1,
    delimiters=None,
    mode="within_row",
    range_within_row=1,
):
    """Uses alternative field delimiters.

    Args:
        file: CSVFile to mutate.
        row: Row to modify. Supports negative indexing.
        delimiters: Delimiters to use.
        mode:
            "whole_row" changes all delimiters in one row to the same delimiter.
            "within_row" changes a centered range of delimiters within one row.
        range_within_row:
            Number of middle delimiters to change in "within_row" mode.
    """

    if delimiters is None:  # default to semicolon if no insert-delimiters provided
        delimiters = [";"]

    if not delimiters:
        raise ValueError("delimiters must contain at least one delimiter")

    if mode not in {"whole_row", "within_row"}:
        raise ValueError("mode must be either 'whole_row' or 'within_row'")

    if range_within_row < 1:
        raise ValueError("range_within_row must be at least 1")

    row_label = row
    if type(row) == int and row < 0:
        row = "last()-" + str(abs(row) - 1)

    root = file.xml.getroot()
    fds = root.xpath(f"//row[{row}]/field_delimiter")

    if not fds:
        raise ValueError(f"Row {row_label} has no field delimiters to modify")

    if mode == "whole_row":
        target_delimiter = delimiters[0]
        for fd in fds:
            fd.text = target_delimiter

    elif mode == "within_row":
        n_fds = len(fds)
        n_change = min(range_within_row, n_fds)

        start = (n_fds - n_change) // 2
        end = start + n_change

        target_fds = fds[start:end]

        for idx, fd in enumerate(target_fds):
            fd.text = delimiters[idx % len(delimiters)]

    encoded = "_".join(
        "".join(f"0x{ord(ch):X}" for ch in delimiter)
        for delimiter in delimiters
        if delimiter
    )

    if mode == "within_row":
        _set_polluted_filename(
            file,
            f"file_mixed_delimiters_{mode}_row_{row_label}_range_{range_within_row}_{encoded}.csv",
        )
    elif mode == "whole_row":
        _set_polluted_filename(
            file,
            f"file_mixed_delimiters_{mode}_row_{row_label}_{encoded}.csv",
        )


@pollution(category="Dialect and Lexical-Syntax", name="Multiline Strings")
def unescapedMultiLineString(file: CSVFile, row=2, col=7):
    """Insert an unescaped newline into an existing string cell."""
    cells = file.xml.getroot().xpath(f"//table[1]/row[{row}]/cell[{col}]")
    if not cells:
        raise IndexError(f"Cell ({row}, {col}) not found")

    cell = cells[0]
    if cell.attrib.get("type") != "TYPE_STRING":
        raise ValueError(f"Cell ({row}, {col}) must contain a string")

    content = "".join(value.text or "" for value in cell.xpath("./value"))
    insertion_point = content.find(" ", len(content) // 2)
    if insertion_point == -1:
        insertion_point = len(content) // 2
    else:
        insertion_point += 1

    polluted_content = content[:insertion_point] + "\n" + content[insertion_point:]
    pb.changeCell(file, row=row, col=col, new_content=polluted_content)
    _set_polluted_filename(
        file,
        f"file_unescaped_multiline_string_row_{row}_col_{col}.csv",
    )


@pollution(
    category="Dialect and Lexical-Syntax", name="Mixed Escaping Strategies"
)
def doubleEscaping(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
    escaping: str = "double_quote",
    **legacy_kwargs,
):
    """Double-escape one existing quoted string cell using one escaping style."""
    row = legacy_kwargs.pop("row1", row)
    legacy_kwargs.pop("row2", None)
    if legacy_kwargs:
        unexpected = ", ".join(sorted(legacy_kwargs))
        raise TypeError(f"Unexpected doubleEscaping arguments: {unexpected}")

    row, col, cell = _quoted_string_cell(file, row=row, col=col)
    _replace_with_double_escaped_content(file, cell, escaping=escaping)
    file.ground_truth_bundle = GroundTruthBundle.single(
        CSVFile.clean_rows(file),
        accept_origin=True,)
    _set_polluted_filename(file, f"file_double_escaping_{escaping}_row_{row}_col_{col}.csv")



@pollution(category="Undefined", name="moreColumns")
def moreColumns(file: CSVFile, row: int | None = None):
    """Creates one data row with one more field than the header."""
    row, col = _variable_column_target(file, row)
    pb.addCells(file, row + 1, col, n_cells=1, content=randomType(), role="data")
    _set_polluted_filename(file, f"file_more_columns_row_{row}_col_{col}.csv")


@pollution(category="Undefined", name="lessColumnsDeletedValues")
def lessColumnsDeletedValues(file: CSVFile, row: int | None = None):
    """Creates one data row with one deleted field.

    The polluted CSV stays jagged. The clean target is rectangularized by
    CSVFile.write_clean_csv using these root attributes: the deleted value is
    unrecoverable, but its column position is known from the source structure.
    """
    row, col = _variable_column_target(file, row)
    pb.deleteCellAndDelimiter(file, row, col)
    root = file.xml.getroot()
    root.attrib["ground_truth_insert_empty_row"] = str(row)
    root.attrib["ground_truth_insert_empty_col"] = str(col)
    _set_polluted_filename(file, f"file_less_columns_deleted_value_row_{row}_col_{col}.csv")


@pollution(category="Record-Shape and Alignment", name="Variable Column Counts")
def variableColumnCount(file: CSVFile, row: int | None = None):
    """Compatibility wrapper that creates either a wider or narrower row."""
    warnings.warn(
        "variableColumnCount is deprecated; use moreColumns or "
        "lessColumnsDeletedValues instead",
        DeprecationWarning,
        stacklevel=2,
    )

    if random.randint(0, 1) == 1:
        lessColumnsDeletedValues(file, row=row)
    else:
        moreColumns(file, row=row)


@pollution(
    category="Value & Semantic Interpretation", name="Excel Autoformat Damage"
)
def excelExportAutoformat(file: CSVFile, rows=None):
    """Adds values commonly autoformatted by Excel to end of CSV: leading-zero IDs and date-like strings."""
    if rows is None:
        print(
            "USE WITH CAUTION: only insert fields with same data type for fair pollution"
        )
        rows = [
            ["00123", "03/04/05", "1-2", "1E10"],
            ["00001", "2026-05-27", "12-13", "3.14E2"],
        ]

    for values in rows:
        padded = values[: file.col_count] + [""] * max(file.col_count - len(values), 0)
        pb.addRows(
            file,
            cell_content=padded,
            n_rows=1,
            position=_safe_row_count(file),
            col_count=file.col_count,
            role="data",
        )
    _set_polluted_filename(file, "file_excel_autoformat.csv")


@pollution(
    category="Value & Semantic Interpretation", name="Excel Formulas as Strings"
)
def exelExportFormulas(file: CSVFile):  # checked manually
    """Adds spreadsheet formulas as literal CSV cell contents to end of CSV."""
    print("USE WITH CAUTION: only insert fields with same data type for fair pollution")

    formulas = ["=SUM(A1:A10)", "=A2+B2", '=HYPERLINK("https://example.com","link")']
    row = formulas[: file.col_count] + [""] * max(file.col_count - len(formulas), 0)
    pb.addRows(
        file,
        cell_content=row,
        n_rows=1,
        position=_safe_row_count(file),
        col_count=file.col_count,
        role="data",
    )
    _set_polluted_filename(file, "file_excel_formulas.csv")


@pollution(category="Value & Semantic Interpretation", name="Boolean / Null Variants")
def typeAmbiguity(file: CSVFile):  
    """
    Adds rows containing ambiguous nulls, booleans, decimals, dates, and currencies. Examples include:["$20", "20 EUR", "unknown", "zero"],
    """
    print("USE WITH CAUTION: this may break csv. Maybe create new csv altogether to test this?")

    #TODO in column price in source.csv, use 25.55 Dollars instead of $25.55 

    _set_polluted_filename(file, "file_type_ambiguity_row.csv")



@pollution(category="Header and Schema-Layout", name="Super-Headers")
def superheader(
    file: CSVFile,
    groups: dict[str, list[int]],
    sparse: bool = True,
    position: int = 0,
):
    """
    Adds a superheader row above the normal header.

    Parameters:
    - groups:
        Dictionary mapping superheader labels to 0-based column ids.

        Example:
            {
                "Transaction Info": [0, 1],
                "Product Info": [2, 3, 4, 5, 6, 7],
                "Notes": [8],
            }

    - sparse:
        If True, only the first column of each group gets the label.
        Other columns in the group are empty, imitating merged spreadsheet cells.

        Example:
            Transaction Info,,Product Info,,,,,,Notes

        If False, the label is repeated across all grouped columns.

        Example:
            Transaction Info,Transaction Info,Product Info,Product Info,...

    - position:
        Row insertion position. In your setup, position=1 likely means
        insert before the first row.
    """

    if not isinstance(groups, dict):
        raise ValueError("groups must be a dictionary: dict[str, list[int]]")

    source_rows = CSVFile.clean_rows(file)
    if not source_rows:
        raise ValueError("Cannot add a superheader to an empty file")

    col_count = file.col_count
    superheader_row = [""] * col_count
    used_columns = set()
    column_groups = {}

    for label, columns in groups.items():
        if not isinstance(label, str):
            raise ValueError("All superheader labels must be strings")

        if not isinstance(columns, list):
            raise ValueError(
                f"Columns for superheader group '{label}' must be a list of integers"
            )

        if not columns:
            raise ValueError(f"Superheader group '{label}' has no columns")

        for col in columns:
            if not isinstance(col, int):
                raise ValueError(
                    f"Column id '{col}' in group '{label}' is not an integer"
                )

            if col < 0 or col >= col_count:
                raise ValueError(
                    f"Column {col} in group '{label}' is out of range for file with {col_count} columns"
                )

            if col in used_columns:
                raise ValueError(
                    f"Column {col} is assigned to more than one superheader group"
                )

            used_columns.add(col)
            column_groups[col] = label

        sorted_columns = sorted(columns)

        if sparse:
            superheader_row[sorted_columns[0]] = label
        else:
            for col in sorted_columns:
                superheader_row[col] = label

    pb.addRows(
        file,
        cell_content=superheader_row,
        n_rows=1,
        position=position,
        col_count=col_count,
        role="superheader",)

    flattened_header = [
        " ".join(part for part in (column_groups.get(index), header) if part)
        for index, header in enumerate(source_rows[0])
    ]
    flattened_rows = [flattened_header, *source_rows[1:]]
    file.clean_rows_override = flattened_rows
    file.ground_truth_bundle = GroundTruthBundle(
        tables=(
            GroundTruthTable.from_rows("primary", flattened_rows),
            GroundTruthTable.from_rows("without_superheader", source_rows),
        ),
        alternatives=(
            GroundTruthAlternative(
                id="canonical",
                table_ids=("primary",),
                comparison="single_table",
            ),
            GroundTruthAlternative(
                id="without_superheader",
                table_ids=("without_superheader",),
                comparison="single_table",
            ),
        ),
        canonical="canonical",
        accept_origin=True,
    )
    mode = "sparse" if sparse else "repeated"
    encoded_groups = []
    for label, columns in groups.items():
        encoded_label = "_".join(
            part for part in "".join(
                char.lower() if char.isalnum() else " " for char in label
            ).split()
        )
        encoded_columns = "-".join(str(column) for column in sorted(columns))
        encoded_groups.append(f"{encoded_label}_cols_{encoded_columns}")
    _set_polluted_filename(
        file,
        f"file_superheader_{mode}_{'_group_'.join(encoded_groups)}.csv",
    )



@pollution(
    category="Header and Schema-Layout",
    name="Whitespace-Aligned Super-Headers",
)
def whitespaceAlignedSuperheader(
    file: CSVFile,
    groups: dict[str, list[int]],
    position: int = 0,
):
    """Add a left-aligned superheader to a padded whitespace table."""
    superheader(file, groups=groups, sparse=True, position=position)
    superheader_filename = file.filename

    tableToWhitespaceFormattedTable(
        file,
        pad_cells=True,
        quote_strings=False,
    )

    filename = superheader_filename.replace(
        "file_superheader_sparse_",
        "file_superheader_whitespace_aligned_columns_",
        1,
    )
    _set_polluted_filename(file, filename)


@pollution(
    category="Value & Semantic Interpretation", name="Embedded JSON Structures"
)
def embeddedJSON(
    file: CSVFile,
    row: int | None = None,
    start_col: int | None = None,
    l_col: int | None = None,
):
    """Collapse a row extract in place into one embedded JSON cell.

    All positions are 0-based. row selects the row to mutate, start_col
    selects the first source column, and l_col selects how many consecutive
    source columns are moved into the JSON payload. The JSON cell is inserted
    at start_col after the original source cells are removed.
    """
    row_count = _safe_row_count(file)
    col_count = _safe_col_count(file)

    if row_count == 0 or col_count == 0:
        raise ValueError("Cannot embed JSON in an empty file")

    if row is None:
        row = random.randint(1, row_count - 1) if row_count > 1 else 0

    if row < 0 or row >= row_count:
        raise ValueError(f"Row {row} is out of range for file with {row_count} rows")

    row_values = _row_values(file, row=row + 1)
    header_values = _row_values(file, row=1)
    source_width = min(len(row_values), len(header_values))

    if source_width == 0:
        raise ValueError(f"Row {row} has no values to embed")

    if l_col is None:
        l_col = random.randint(1, min(3, source_width))
    elif l_col < 1:
        raise ValueError(f"l_col must be at least 1, got {l_col}")

    if l_col > source_width:
        raise ValueError(
            f"l_col={l_col} is too large for row {row} with {source_width} source cells"
        )

    if start_col is None:
        start_col = random.randint(0, source_width - l_col)

    end_col = start_col + l_col - 1
    if start_col < 0 or end_col >= source_width:
        raise ValueError(
            f"Invalid source extract: start_col={start_col}, l_col={l_col}, "
            f"valid source range is 0..{source_width - 1}"
        )

    payload = {}
    for idx in range(start_col, end_col + 1):
        key = header_values[idx] or f"column_{idx + 1}"
        if key in payload:
            key = f"{key}_{idx + 1}"
        payload[key] = row_values[idx]

    pb.deleteCells(file, row=row + 1, col=list(range(start_col, end_col + 1)))
    pb.addCells(
        file,
        row=row + 1,
        position=start_col,
        content=json.dumps(payload, ensure_ascii=False),
        role="data",
    )

    file.ground_truth_bundle = GroundTruthBundle.single(
        CSVFile.clean_rows(file),
        accept_origin=False,)
    _set_polluted_filename(
        file,
        f"file_embedded_json_cell_{row}_{start_col}_len_{l_col}.csv",)


@pollution(
    category="Value & Semantic Interpretation",
    name="Embedded Sub-CSV Structures",
)
def embeddedCSV(file: CSVFile):
    """Embeds CSV-like file content inside a single cell."""
    payload = "id,name\n1,alpha\n2,beta"
    pb.changeCell(
        file, row=2 if _safe_row_count(file) >= 2 else 1, col=1, new_content=payload)
    file.ground_truth_bundle = GroundTruthBundle.single(
        CSVFile.clean_rows(file),
        accept_origin=False,)
    _set_polluted_filename(file, "file_embedded_csv_cell.csv")


@pollution(
    category="Encoding and Text-Representation", name="Encoding Mismatches"
)
def encoding(file: CSVFile, target_encoding: constants.Encoding):
    """Changes the declared file encoding.

    This wrapper is intentionally a little more permissive than
    changeEncoding(): tests and callers may pass plain strings such as
    "utf-8" instead of a constants.Encoding enum member.
    """
    target = (
        target_encoding.value
        if type(target_encoding) == constants.Encoding
        else str(target_encoding)
    )

    aliases = {
        "utf8": "utf-8",
        "utf_8": "utf-8",
        "cp1252": "windows-1252",
        "windows_1252": "windows-1252",
    }
    target = aliases.get(target.lower(), target)

    file.encoding = target
    root = file.xml.getroot()
    root.attrib["encoding"] = target
    _set_polluted_filename(file, f"file_encoding_{target}.csv")


@pollution(category="Encoding and Text-Representation", name="BOM Issues")
def bomMarker(file: CSVFile):
    """Adds a UTF-8 BOM marker to the serialized CSV output."""
    file.xml.getroot().attrib["bom"] = "utf-8"
    _set_polluted_filename(file, "file_utf8_bom.csv")


@pollution(
    category="Encoding and Text-Representation", name="Mojibake / Corrupted Text"
)
def weirdUnicode(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
    weird_values=[
        "FranÃ§ois",
        "MÃ¼nchen",
        "SÃ£o Paulo",
        "â‚¬",
        "👍🏼",
        "cafÃ©",
        "naÃ¯ve",
        "PokÃ©mon",
    ],
):
    """
    Injects unicode-related corruption into a random cell.

    Includes:
    - mojibake
    - unicode normalization changes
    - non-ASCII characters
    """
    if row is None:
        row = random.randint(2, _safe_row_count(file))  # skip header (row 1)
    if col is None:
        col = random.randint(1, _safe_col_count(file))

    old_value = pb.getCell(file, row, col)
    mode = random.choice(
        [
            "mojibake",
            "nfc",
            "nfd",
            "append_unicode",
        ]
    )
    if mode == "mojibake":
        new_value = random.choice(weird_values)
    elif mode == "nfc":
        new_value = unicodedata.normalize("NFC", old_value or "")
    elif mode == "nfd":
        new_value = unicodedata.normalize("NFD", old_value or "")
    else:
        suffix = random.choice(
            [
                " 👍🏼",
                " café",
                " München",
                " €",
                " ß",
            ]
        )

        new_value = (old_value or "") + suffix

    pb.changeCell(
        file,
        row=row,
        col=col,
        new_content=new_value,
    )

    _set_polluted_filename(file, f"file_weird_unicode_row_{row}_col_{col}.csv")


@pollution(
    category="Encoding and Text-Representation", name="Hidden Characters"
)
def invisibleCharacters(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
):
    """Injects invisible Unicode characters into an existing cell."""
    if row is None:
        row = random.randint(2, _safe_row_count(file))  # skip header (row 1)
    if col is None:
        col = random.randint(1, _safe_col_count(file))

    invisible_chars = [
        "\u200b",  # zero-width space
        "\u00a0",  # non-breaking space
        "\u200e",  # left-to-right mark
        "\ufeff",  # zero-width no-break space / BOM char
        "\u2060",  # word joiner
    ]

    old_value = pb.getCell(file, row, col) or ""
    mode = random.choice(
        [
            "prefix",
            "suffix",
            "middle",
            "replace_space",
        ]
    )

    char = random.choice(invisible_chars)
    if mode == "prefix":
        new_value = char + old_value
    elif mode == "suffix":
        new_value = old_value + char
    elif mode == "middle":
        midpoint = len(old_value) // 2
        new_value = old_value[:midpoint] + char + old_value[midpoint:]
    else:  # replace_space
        if " " in old_value:
            new_value = old_value.replace(" ", char, 1)
        else:
            midpoint = len(old_value) // 2
            new_value = old_value[:midpoint] + char + old_value[midpoint:]

    pb.changeCell(
        file,
        row=row,
        col=col,
        new_content=new_value,
    )
    _set_polluted_filename(
        file,
        f"file_invisible_characters_row_{row}_col_{col}.csv",
    )


@pollution(
    category="Encoding and Text-Representation",
    name="Collation Problems (ä, ö, ü, ß)",
)
def collations(file: CSVFile, row: int | None = None):
    """
    Inserts rows containing strings whose ordering/equality differs between collations/locales.
    """
    examples = [
        ["straße", "strasse"],
        ["Müller", "Mueller"],
        ["ä", "ae"],
        ["Ångström", "Angstrom"],
        ["é", "e"],
        ["İstanbul", "Istanbul"],
        ["ß", "ss"],
        ["Özil", "Oezil"],
        ["Æ", "AE"],
    ]

    if row is None:
        row = random.randint(1, _safe_row_count(file))

    for values in examples:
        content = values + [""] * max(file.col_count - len(values), 0)

        pb.addRows(
            file,
            cell_content=content,
            n_rows=1,
            position=row,
            col_count=file.col_count,
            role="data",
        )

        row += 1

    _set_polluted_filename(file, "file_collation_edge_cases.csv")

# unclear if this makes sense
@pollution(category="Value & Semantic Interpretation", name="Muddled Types")
def mixedTypes(file: CSVFile, row: int | None = None):
    """Adds values with incompatible types (str, Bool, int) in the same logical column."""
    if row is None:
        row = random.randint(1, _safe_row_count(file))

    for _ in range(5):
        randomRow = [randomType() for _ in range(file.col_count)]
        pb.addRows(
            file,
            cell_content=randomRow,
            n_rows=1,
            position=row,
            col_count=file.col_count,
            role="data",
        )
    _set_polluted_filename(file, f"file_mixed_types_row_{row}.csv")


@pollution(
    category="Value & Semantic Interpretation", name="Temporal Format Drift"
)
def mixedTimeformats(file: CSVFile, max_num_to_change=100):
    """Replaces some random date time cells from the CSV with random values in random formats"""

    def is_datetime(value, row_idx, col_idx):
        if value is None or row_idx == 0 or str.isdigit(value):
            return False

        try:
            parse(value, fuzzy=False)
            return True
        except Exception:
            return False

    # sorted() for deterministic order: set iteration depends on the per-process
    # hash seed, which would defeat the seeded shuffle
    matching_cells = sorted(pb.findMatchingCells(file, matching=is_datetime))
    random.shuffle(matching_cells)

    for entry in matching_cells[:max_num_to_change]:
        row_idx, col_idx, _ = entry
        # Change cells with random date strings in various formats
        # pd.ChangeCell uses 1-based indexing for rows and columns, so we need to add 1 to both indices
        pb.changeCell(file, row=row_idx + 1, col=col_idx + 1, new_content=randomDateStr())

    _set_polluted_filename(file, f"file_mixed_time_formats.csv")



@pollution(category="Dialect and Lexical-Syntax", name="Unquoted Lists")
def unquotedList(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
    list_delimiter: str = ",",
    list_len: int = 4,
):
    """Replace a cell with an unquoted list built from values in its column.

    When ``col`` is omitted, a text-oriented column is selected using its header
    and observed values. Reusing values from that column keeps the generated list
    plausible for the source data, for example ``[Boots,Jacket,Shoes]``.
    """
    if row is None:
        row = random.randint(2, _safe_row_count(file))  # skip header
    if col is None:
        col = _unquoted_list_column(file, list_delimiter)
    if list_len < 1:
        raise ValueError("list_len must be at least 1")

    items = _unquoted_list_items(file, col, list_delimiter)
    if not items:
        raise ValueError(f"Cannot create an unquoted list: column {col} has no suitable values")

    if list_len <= len(items):
        selected_items = random.sample(items, k=list_len)
    else:
        selected_items = items + random.choices(items, k=list_len - len(items))
        random.shuffle(selected_items)

    payload = "[" + list_delimiter.join(selected_items) + "]"
    pb.changeCell(file, row=row, col=col, new_content=payload)
    _set_polluted_filename(file, f"file_unquoted_lists_row_{row}_col_{col}.csv")

@pollution(category="Header and Schema-Layout", name="Header Not in First Row")
def moveHeaderRow(file: CSVFile, row: int | None = None):
    """
    This polluter will move the header row down to 'row' index (0 based).
    """
    if row is None:
        row = random.randint(1, min(10, _safe_row_count(file)))

    pb.moveRow(file, 0, row)
    _set_polluted_filename(file, f"file_move_header_row{row}.csv")


@pollution(
    category="File Segmentation and Table-Boundary", name="Footers / Footnotes"
)
def addFootnote(
    file: CSVFile, n_rows=1, blank_line=False, cell_content="FOOTNOTE"
):
    """
    :param file:
    :param n_rows: number of rows for the footnote
    :param blank_line: if True, inserts a truly blank line (just a newline) between the data and the footnote
    :param cell_content: the content of the footnote cell(s). Either list or single value
    """
    if blank_line:
        # col_count=0 produces a row with no cells — just the record delimiter,
        # i.e. a truly empty line rather than a row of empty cells.
        pb.addRows(
            file,
            n_rows=1,
            position=_safe_row_count(file),
            col_count=0,
            role="footnote",
        )

    pb.addRows(
        file,
        n_rows=n_rows,
        cell_content=cell_content,
        position=_safe_row_count(file),
        col_count=1,
        role="footnote",
    )

    _set_polluted_filename(
        file,
        f"file_footnote_{n_rows}{'_blank_line' if blank_line else ''}.csv",
    )


@pollution(
    category="Record-Shape and Alignment",
    name="No Real Delimiter (Whitespace Columns)",
)
def tableToWhitespaceFormattedTable(
    file: CSVFile,
    pad_cells=True,
    quote_strings=True,
    quote_empty_last_column=False,
):
    """
    Converts a CSV table to a whitespace-formatted table by replacing the field delimiters with spaces.

    Example:
    ```
    head1,head2,head3
    1,somestring,3.14
    ```

    Becomes (if pad_cells=True):
    ```
    head1 head2      head3
    1     somestring 3.14
    ```

    Padding cells creates a "visually aligned" table, which is easy for humans, but difficult for machines.
    It is guaranteed that columns are separated by at least one space.

    This function also allows quoting string cells because they might contain spaces.
    Not quoting strings only makes sense if `pad_cells` is True. A human can still distinguish columns in this case.

    If `quote_empty_last_column` is true, empty cells in the final column are
    retyped as strings in the XML so that the regular string-quoting pass emits
    them as `""`. This keeps an otherwise empty trailing column explicit.
    """
    root = file.xml.getroot()
    rows = list(root.iter("row"))
    quote_char = file.quotation_char or '"'

    if quote_empty_last_column and not quote_strings:
        raise ValueError("quote_empty_last_column requires quote_strings=True")

    if quote_empty_last_column:
        for row in rows:
            cells = row.xpath("./cell")
            if cells and cells[-1].attrib.get("type") == "TYPE_EMPTY":
                cells[-1].attrib["type"] = "TYPE_STRING"

    pb.changeColumnDelimiters(file, col="*", new_delimiter=" ")

    if quote_strings:
        # Embedded quotes are already represented by the cell's value and
        # escape nodes. Only add the surrounding quotation marks here.
        for row in rows:
            for cell in row.xpath("./cell[@type='TYPE_STRING']"):
                if len(cell) == 0 or cell[0].tag != "quotation_char":
                    cell.insert(0, E.quotation_char(quote_char))
                if cell[-1].tag != "quotation_char":
                    cell.append(E.quotation_char(quote_char))
    else:
        # Remove cell quoting inherited from the source while preserving the
        # logical field payload used to generate the clean ground truth.
        for row in rows:
            for cell in row.xpath("./cell"):
                payload = "".join(
                    value.text or "" for value in cell.xpath("./value")
                )
                for child in list(cell):
                    cell.remove(child)
                cell.append(E.value(payload))

    if pad_cells:
        column_widths: list[int] = []
        # Count maximum width of the current cell content in each column.
        for row in rows:
            for col_idx, cell in enumerate(row.xpath("./cell")):
                cell_text_len = sum(len(node.text or "") for node in cell)

                if col_idx == len(column_widths):
                    column_widths.append(cell_text_len)
                elif cell_text_len > column_widths[col_idx]:
                    column_widths[col_idx] = cell_text_len

        for row in rows:
            cells = row.xpath("./cell")
            delimiters = row.xpath("./field_delimiter")
            for col_idx, delimiter in enumerate(delimiters):
                cell_text_len = sum(len(node.text or "") for node in cells[col_idx])
                pad = column_widths[col_idx] - cell_text_len
                delimiter.text = " " * (pad + 1 if pad > 0 else 1)

    _set_polluted_filename(
        file,
        "file_whitespace_delimiter_cells_"
        f"{'quoted' if quote_strings else 'unquoted'}_"
        f"{'empty_last_column_' if quote_empty_last_column else ''}"
        f"{'padded' if pad_cells else 'unpadded'}.csv",
    )


@pollution(
    category="Value & Semantic Interpretation", name="Different Null Values"
)
def differentNullValues(file: CSVFile,
    row: int | None = None,
    col: int | None = None,
    null_values = ["NULL", "N/A", "", "None", "undefined"]):
    """
    This polluter will create a CSV file with different null values in the same column.
    It replaces consecutive cells in one column with different null markers such as
    "NULL", "N/A", "", "None", and "undefined".

    Args:
        file: CSVFile to modify.
        row: Row index to start inserting null values. If None, a random row is chosen
        col: Column index to insert null values. If None, a random column is chosen.
        null_values: List of null values to use.
        n_values: Number of null values to insert. 
    """
        
    if null_values is None:
        null_values = ["NULL", "N/A", "", "None", "undefined"]
    

    row_count = _safe_row_count(file)
    col_count = _safe_col_count(file)
    if row_count <= 0 or col_count <= 0:
        raise ValueError("Cannot apply differentNullValues to an empty file.")

    if row is None:
        row = random.randint(1, _safe_row_count(file)-len(null_values)) # Ensure enough rows are available for the null values
    if col is None:
        col = random.randint(0, _safe_col_count(file))


    for offset, null_value in enumerate(null_values):
        target_row = row + offset

        pb.changeCell(
            file,
            row=target_row + 1,  # XPath indexing
            col=col + 1,
            new_content=null_value,
        )

    # source.csv should not be accepted as ground truth 
    file.ground_truth_bundle = GroundTruthBundle.single(CSVFile.clean_rows(file), accept_origin=False,)
    _set_polluted_filename(file, f"file_different_null_values_row_{row}_col_{col}.csv")
