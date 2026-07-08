import random
import unicodedata
import string
import time
from lxml import etree
from .CSVFile import CSVFile
from lxml.builder import E
from .randdata import (
    randomString,
    randomDateStr,
    randomType,
    randomInt,
    randomJsonStr,
)
from dateutil.parser import parse

from . import constants
from . import polluters_base as pb
from pollock.polluters_utils import (
    _set_polluted_filename,
    _row_values,
    _safe_row_count,
    _safe_col_count,
    _last_data_row,
    manually_verified,
    todo
)


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


@manually_verified
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

    _set_polluted_filename(
        file,
        f"file_multiline_header_rows_{header_rows}.csv",
    )


def duplicateHeaderAsDataRow(file: CSVFile, n_duplicates: int = 1):  # checked manually
    # OPEN QUESTION: does this pollution really make sense or is it just a special case of the multiline header?
    """Duplicates the header row as data rows directly below the header.

    Args:
        file: CSVFile to mutate.
        n_duplicates: Number of duplicated header rows to insert.
    """
    if n_duplicates < 1:
        raise ValueError("n_duplicates must be at least 1")

    header = _row_values(file, row=1)
    if not header:
        raise ValueError("Cannot duplicate header: first row is empty or missing")

    for _ in range(n_duplicates):
        pb.addRows(
            file,
            cell_content=header,
            n_rows=1,
            position=1,
            col_count=len(header) or file.col_count,
            role="data",
        )

    suffix = "" if n_duplicates == 1 else f"_{n_duplicates}x"
    _set_polluted_filename(file, f"file_duplicate_header_as_data{suffix}.csv")


def extremelyLongFields(
    file: CSVFile, row=1, col=1, length=50 * 1024 * 1024
):  # checked manually
    """Replaces a cell with an extremely long random alphanumeric field."""
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    pb.changeCell(
        file,
        row=row,
        col=col,
        new_content=randomString(min_length=length, max_length=length),
    )
    _set_polluted_filename(
        file, f"file_extremely_long_field_row_{row}_col_{col}_len_{length}.csv"
    )


def addGroupSectionHeader(file: CSVFile, group_name="Region: North", position=1):
    """Adds a bare section/group label row with content only in the first column."""
    print(
        "USE WITH CAUTION: only add this to files where such grouping structure would make sense, e.g. a sales file with regional groups."
    )
    # has to be added to right files only. This is only meaningful if the file has some kind of grouping structure.
    if position < 0:
        position = _last_data_row(file) - 1
    row = [group_name] + [""] * max(file.col_count - 1, 0)
    pb.addRows(
        file,
        cell_content=row,
        n_rows=1,
        position=position,
        col_count=file.col_count,
        role="section_header",
    )
    _set_polluted_filename(file, f"file_group_section_header_{position}.csv")


def addCommentToFile(
    file: CSVFile,
    comment="This is a comment.",
    row: int | None = None,
    comment_marker: str = "#",
    space=" ",
):
    """Backward-compatible alias for addTrailingCommentToFile."""
    return addTrailingCommentToFile(
        file,
        comment=comment,
        row=row,
        comment_marker=comment_marker,
        space=space,
    )


def addTrailingCommentToFile(
    file: CSVFile,
    comment="This is a comment.",
    row: int | None = None,
    comment_marker: str = "#",
    space=" ",
):  # checked manually
    """Adds a comment-like trailing field to a row without a delimiter before it."""
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

    _set_polluted_filename(file, "file_trailing_comment.csv")


def commentRow(
    file: CSVFile, row: int | None = None, comment_marker: str = "#", space=" "
):
    """
    Simulate a commented-out CSV row by prefixing the first cell with a comment
    marker (e.g. '#', '//', ';').

    Args:
        file: CSVFile to modify.
        row: Zero-based row index to comment out. If None, a random row is chosen.
        comment_marker: Marker used to indicate a comment.
        space: Optional separator between the marker and the original value.
    """
    if row is None:
        row = random.randint(1, _safe_row_count(file))

    old_value = pb.getCell(file, row, col=0)
    pb.changeCell(
        file,
        row=row + 1,  # XPath indexing
        col=1,
        new_content=f"{comment_marker}{space}{old_value}",
    )
    _set_polluted_filename(file, f"file_commented_row_{row}.csv")


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


def unescaped(
    file: CSVFile,
    row=1,
    col=1,
    content='This is a "quote" and a comma, and a newline\nin the same cell.',
):  # checked manually
    """Places quote, delimiter, and newline characters in a cell without adding escaping metadata."""
    print(
        "USE WITH CAUTION: only insert in field with same data type for fair pollution"
    )
    pb.changeCell(file, row=row, col=col, new_content=content)
    _set_polluted_filename(file, f"file_unescaped_row_{row}_col_{col}.csv")


def doubleEscaping(file: CSVFile, row1=2, row2=3, col=1):  # checked manually
    """Mixes doubled-quote escaping and backslash escaping in the same column. Example content: ""hi"" and \"hi\"."""
    print(
        "USE WITH CAUTION: only insert in field with same data type for fair pollution"
    )
    row_count = _safe_row_count(file)
    if row_count < row2:
        last = _row_values(file, row=row_count) or [""] * file.col_count
        pb.addRows(
            file,
            cell_content=last,
            n_rows=row2 - row_count,
            position=row_count,
            col_count=file.col_count,
            role="data",
        )
    pb.changeCell(file, row=row1, col=col, new_content='""hi""')
    pb.changeCell(file, row=row2, col=col, new_content='\\"hi\\"')
    _set_polluted_filename(file, f"file_double_escaping_col_{col}.csv")


def variableColumnCount(file: CSVFile, row: int | None = None):
    """Creates rows with fewer and more fields than the header."""
    if row is None:
        # Pick a data row that both the add and delete paths can address.
        row = random.randint(1, max(1, _safe_row_count(file) - 1))
    col = random.randrange(_safe_col_count(file))

    if random.randint(0, 1) == 1:
        pb.deleteCellAndDelimiter(file, row, col)
    else:
        pb.addCells(file, row + 1, col, n_cells=1, content=randomType(), role="data")

    _set_polluted_filename(file, f"file_variable_column_count_row_{row}_col_{col}.csv")


def excelExportAutoformat(file: CSVFile, rows=None):  # checked manually
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


def typeAmbiguity(file: CSVFile):  # checked manually
    """Adds rows containing ambiguous nulls, booleans, decimals, dates, and currencies."""
    print(
        "USE WITH CAUTION: this may break csv. Maybe create new csv altogether to test this?"
    )
    rows = [
        ["NULL", "N/A", "NaN", ""],
        ["true", "false", "1", "0"],
        ["1.5", "1,5", "2026-05-27", "27.05.2026"],
        ["$20", "20 EUR", "unknown", "zero"],
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
    _set_polluted_filename(file, "file_type_ambiguity.csv")


def superheader(file: CSVFile):
    """Adds a grouping row above the normal header."""
    print(
        "USE WITH CAUTION: only add this to files where such grouping structure would make sense, e.g. a sales file with regional groups."
    )
    groups = []
    for i in range(file.col_count):
        groups.append("Region" if i < max(1, file.col_count // 2) else "Metrics")
    pb.addRows(
        file,
        cell_content=groups,
        n_rows=1,
        position=0,
        col_count=file.col_count,
        role="superheader",
    )
    _set_polluted_filename(file, "file_superheader.csv")


def embeddedFiles(file: CSVFile, row: int | None = None, col: int | None = None):
    """Backward-compatible alias for embeddedJSON."""
    return embeddedJSON(file, row=row, col=col)


def embeddedJSON(file: CSVFile, row: int | None = None, col: int | None = None):
    """Embeds JSON-like file content inside a single cell."""
    if row is None:
        row = random.randint(1, _safe_row_count(file))
    if col is None:
        col = random.randint(0, _safe_col_count(file))
    pb.changeCell(file, row=row + 1, col=col + 1, new_content=randomJsonStr())
    _set_polluted_filename(file, "file_embedded_json_cell.csv")


def embeddedCSV(file: CSVFile):
    """Embeds CSV-like file content inside a single cell."""
    payload = "id,name\n1,alpha\n2,beta"
    pb.changeCell(
        file, row=2 if _safe_row_count(file) >= 2 else 1, col=1, new_content=payload
    )
    _set_polluted_filename(file, "file_embedded_csv_cell.csv")


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


def bomMarker(file: CSVFile):
    """Adds a UTF-8 BOM marker to the serialized CSV output."""
    file.xml.getroot().attrib["bom"] = "utf-8"
    _set_polluted_filename(file, "file_utf8_bom.csv")


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
        row = random.randint(1, _safe_row_count(file))
    if col is None:
        col = random.randint(0, _safe_col_count(file))

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
        row=row + 1,  # XPath indexing
        col=col + 1,
        new_content=new_value,
    )

    _set_polluted_filename(file, f"file_weird_unicode_row_{row}_col_{col}.csv")


def invisibleCharacters(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
):
    """Injects invisible Unicode characters into an existing cell."""
    if row is None:
        row = random.randint(1, _safe_row_count(file))
    if col is None:
        col = random.randint(0, _safe_col_count(file))

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
        row=row + 1,
        col=col + 1,
        new_content=new_value,
    )
    _set_polluted_filename(
        file,
        f"file_invisible_characters_row_{row}_col_{col}.csv",
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


def mixedTypes(file: CSVFile, row: int | None = None):
    """Adds values with incompatible types in the same logical column."""
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

    matching_cells = list(pb.findMatchingCells(file, matching=is_datetime))
    random.shuffle(matching_cells)

    for entry in matching_cells[:max_num_to_change]:
        row_idx, col_idx, _ = entry
        # Change cells with random date strings in various formats
        # pd.ChangeCell uses 1-based indexing for rows and columns, so we need to add 1 to both indices
        pb.changeCell(file, row=row_idx + 1, col=col_idx + 1, new_content=randomDateStr())

    _set_polluted_filename(file, f"file_mixed_time_formats.csv")


def unquotedLists(
    file: CSVFile,
    row: int | None = None,
    col: int | None = None,
    delimiter: str = ",",
    min_list_len=2,
    max_list_len=10,
):
    """
    This polluter will replace a cell content with an unqoted list.
    """
    if row is None:
        row = random.randint(1, _safe_row_count(file))
    if col is None:
        col = random.randint(0, _safe_col_count(file))

    payload = delimiter.join(
        str(randomInt(min=-100, max=1000))
        for _ in range(random.randint(min_list_len, max_list_len))
    )
    pb.changeCell(file, row=row, col=col, new_content=payload)
    _set_polluted_filename(file, f"file_unquoted_lists_row_{row}_col_{col}.csv")


def moveHeaderRow(file: CSVFile, row: int | None = None):
    """
    This polluter will move the header row down to 'row' index (0 based).
    """
    if row is None:
        row = random.randint(1, min(10, _safe_row_count(file)))

    pb.moveRow(file, 0, row)
    _set_polluted_filename(file, f"file_move_header_row{row}.csv")


@manually_verified
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


@manually_verified
def tableToWhitespaceFormattedTable(
    file: CSVFile, pad_cells=True, quote_strings=True
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

    This function also allows quoting string cells because the might contain spaces.
    Not quoting strings only makes sense if `pad_cells` is True. A human can still dinguish columns in this case.
    """
    root = file.xml.getroot()
    rows = list(root.iter("row"))
    quote_char = file.quotation_char or '"'
    doubled_quote = quote_char * 2

    pb.changeColumnDelimiters(file, col="*", new_delimiter=" ")

    if quote_strings:
        # Quote string cells first so delimiter padding can be computed from the
        # quoted width, not the raw cell value.
        for row in rows:
            for cell in row.xpath("./cell[@type='TYPE_STRING']"):
                if len(cell) == 0 or cell[0].tag != "quotation_char":
                    cell.insert(0, E.quotation_char(quote_char))
                if cell[-1].tag != "quotation_char":
                    cell.append(E.quotation_char(quote_char))
                for value in cell.xpath("./value"):
                    if value.text and quote_char in value.text:
                        value.text = value.text.replace(quote_char, doubled_quote)

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
        f"{'padded' if pad_cells else 'unpadded'}.csv",
    )


@manually_verified
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

    _set_polluted_filename(file, f"file_different_null_values_row_{row}_col_{col}.csv")




