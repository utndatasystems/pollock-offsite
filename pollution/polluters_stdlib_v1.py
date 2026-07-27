"""CSV pollution helpers used to generate Pollock benchmark variants.

Each function tweaks one part of a CSV file, such as delimiters, headers,
row counts, or table structure.
"""

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
from .ground_truth import (
    GroundTruthAlternative,
    GroundTruthBundle,
    GroundTruthTable,
)
from pollution.polluters_utils import (
    _set_polluted_filename,
    _row_values,
    _safe_row_count,
    _safe_col_count,
    _last_data_row,
    manually_verified,
    todo,
    pollution,
)


@pollution(category="Undefined", name="dummyPolluter")
def dummyPolluter(file: CSVFile):
    """Dummy Polluter - does nothing"""
    pass


# --- Pollock1.0 Pollutions ---

@pollution(category="Operational Scale Stressor", name="No Payload")
@manually_verified
def changeDimension(file: CSVFile, target_dimension=-1):
    """Resize the file to a target text length."""
    content = []
    for i in range(file.row_count):
        texts = [x.text or "" for x in file.xml.xpath(f"//row[{i + 1}]//*[not(*)]")]
        content.append("".join(texts))
    textcontent = "".join(content)
    cur_size = len(textcontent)

    last_row_cells = [x for x in file.xml.xpath("//row[last()]//cell")]
    # join per cell, a cell with embedded quotes is stored as multiple <value> elements
    last_row_content = [
        "".join(v.text or "" for v in c if v.tag == "value") for c in last_row_cells
    ]

    size_last_row = len("".join(content[-1]))
    n_rows = int((target_dimension - cur_size) / size_last_row)

    if target_dimension > cur_size:
        pb.addRows(
            file, cell_content=last_row_content, n_rows=n_rows, position=file.row_count, role="data"
        )
    elif 0 <= target_dimension < cur_size:
        n_rows_to_keep = textcontent.count("\r\n", target_dimension)
        if target_dimension:
            n_rows_to_keep -= 1  # exclude the current if dimension breaks one in half (if not exactly 0)
        remove_rows = list(range(file.row_count - n_rows_to_keep, file.row_count + 1))
        pb.deleteRows(file, rows_to_delete=remove_rows)

    _set_polluted_filename(file, f"file_size_{str(target_dimension)}.csv")


@pollution(
    category="Encoding and Text-Representation", name="Encoding Mismatches"
)
def changeEncoding(file: CSVFile, target_encoding: constants.Encoding):
    """Change the declared file encoding."""
    target = (
        target_encoding.value
        if type(target_encoding) == constants.Encoding
        else target_encoding
    )
    assert target in constants.Encoding.supported_encodings.value

    file.encoding = target
    file.xml.getroot().attrib["encoding"] = target
    _set_polluted_filename(file, f"file_encoding_{target}.csv")

@pollution(category="Operational Scale Stressor", name="Extreme Width")
@manually_verified
def changeNumberColumns(file: CSVFile, target_number_cols: int, pad_with_random_ints:bool):
    """
        Add or remove columns until the file has the requested width.
        Repeats the last column if the new number of columns is larger unless pad_with_random_ints is set 
    """
    if target_number_cols < file.col_count:
        cols_delete = list(range(target_number_cols, file.col_count))
        pb.deleteColumns(file, col=cols_delete)

    if target_number_cols > file.col_count:
        rn = range(file.col_count, target_number_cols)
        t = time.time()
        roles = ["header"] + ["data"] * (file.row_count - 1)
        content = []

        for i in range(file.row_count-1):
            if pad_with_random_ints:
                content += [[str(random.randint(0, 1_000_000)) for _ in rn]]
            else:
                content += [
                    "".join(
                        [
                            val.text or ""
                            for val in file.xml.xpath(f"//row[{i + 2}]/cell[last()]/value")
                        ]
                    )
                ]  # xpath is 1-indexed plus row 1 is header
        pb.addColumns(
            file,
            file.col_count,  # append after the last existing column
            col_names=["col" + str(i + 1) for i in rn],
            n_cols=len(rn),
            cell_content=content,
            role=roles,
        )
        print("took", time.time() - t, "seconds")

    _set_polluted_filename(file, f"file_num_columns_{'pad_randints_' if pad_with_random_ints else ''}{str(target_number_cols)}.csv")

@pollution(category="Operational Scale Stressor", name="Extreme Volume")
@manually_verified
def changeNumberRows(file: CSVFile, target_number_rows: int, remove_header=False, repeat_file=False):
    """Add or remove rows until the file has the requested height.

    When growing, repeats the last row, or cycles through all data rows if repeat_file is set.
    """
    # join per cell, a cell with embedded quotes is stored as multiple <value> elements
    def row_content(row):
        return [
            "".join(v.text or "" for v in c if v.tag == "value")
            for c in row
            if c.tag == "cell"
        ]

    if repeat_file:
        # all data rows (skip the header at row 1)
        fill_rows = [row_content(r) for r in file.xml.xpath("//table[1]/row")[1:]]
    else:
        fill_rows = [row_content(file.xml.xpath("//row[last()]")[0])]

    if remove_header:
        pb.deleteRows(file, [0])

    if target_number_rows < file.row_count:
        rows_delete = list(range(target_number_rows, file.row_count))
        pb.deleteRows(file, rows_to_delete=rows_delete)

    if target_number_rows > file.row_count:
        n_rows = target_number_rows - file.row_count
        t = time.time()
        for j in range(n_rows):
            pb.addRows(
                file,
                cell_content=fill_rows[j % len(fill_rows)],
                n_rows=1,
                position=file.row_count + j,
                role="data",
            )
        print("took", time.time() - t, "seconds")

    _set_polluted_filename(
        file,
        f"file_num_rows_{str(target_number_rows)}"
        f"{'_no_header' if remove_header else ''}"
        f"{'_repeat_file' if repeat_file else ''}.csv",
    )


@pollution(category="Header and Schema-Layout", name="Super-Headers")
def expandColumnHeader(file: CSVFile, extra_rows=1):
    """Repeat the header across extra header rows. Turns the header into a multi-row header."""
    header = [x for x in file.xml.xpath(f"//row[{1}]//value//node()[not(node())]")]
    pb.addRows(file, cell_content=header, n_rows=extra_rows, position=0, role="header")

    _set_polluted_filename(file, f"file_multirow_header_{str(extra_rows)}.csv")

@pollution(
    category="File Segmentation and Table-Boundary",
    name="Preambles / Metadata Blocks",
)
@manually_verified
def addPreamble(
    file: CSVFile,
    n_rows=1,
    delimiters=False,
    emptyrow=False,
    cell_content="PREAMBLE",
):
    """Insert raw-text preamble rows before the table."""

    if isinstance(cell_content, str):
        preamble_rows = cell_content.splitlines()
    elif isinstance(cell_content, list):
        preamble_rows = cell_content
    else:
        preamble_rows = [cell_content]

    if len(preamble_rows) < n_rows:
        preamble_rows.extend([""] * (n_rows - len(preamble_rows)))

    if emptyrow:
        pb.addRows(
            file,
            n_rows=1,
            position=0,
            cell_content="",
            col_count=1,
            role="preamble",
        )

    for row_content in reversed(preamble_rows):
        pb.addRows(
            file,
            n_rows=1,
            position=0,
            cell_content=row_content,
            col_count=1,
            role="preamble",
        )

    _set_polluted_filename(
        file,
        f"file_preamble_{len(preamble_rows)}_raw"
        f"{'_empty_row' if emptyrow else ''}.csv",
    )


@pollution(
    category="File Segmentation and Table-Boundary", name="Footers / Footnotes"
)
def addFootnote(
    file: CSVFile, n_rows=1, delimiters=False, emptyrow=False, cell_content="FOOTNOTE"
):
    """Insert rows after the table as a footnote.
    :param file:
    :param n_rows: number of rows for the preamble
    :param delimiters: if True, creates a row with as many delimited cells as the other rows
    :param emptyrow:  if True, leaves an empty row between the preamble and the data
    :param cell_content: the content of the preamble cell(s). Either list or single value"""
    if emptyrow:
        pb.addRows(
            file, n_rows=1, position=-1, col_count=file.col_count, role="footnote"
        )

    if delimiters:
        cell_content = (
            [cell_content] + [""] * (file.col_count - 1)
            if type(cell_content) == str
            else cell_content
        )
        pb.addRows(
            file,
            n_rows=n_rows,
            cell_content=cell_content,
            position=-1,
            col_count=file.col_count,
            role="footnote",
        )

    else:
        pb.addRows(
            file,
            n_rows=n_rows,
            cell_content=cell_content,
            position=-1,
            col_count=1,
            role="footnote",
        )

    _set_polluted_filename(
        file,
        f"file_footnote_{n_rows}_{'not_' if not delimiters else ''}delimited{'_empty_row' if emptyrow else ''}.csv",
    )


@pollution(
    category="Dialect and Lexical-Syntax", name="Mixed Record Terminators"
)
def changeRecordDelimiter(file: CSVFile, target_delimiter="\r\n"):
    """Change the record delimiter used between rows."""
    file.record_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//record_delimiter")
    for r in query:
        r.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])

    _set_polluted_filename(file, f"file_record_delimiter{del_string}.csv")


@pollution(
    category="Dialect and Lexical-Syntax", name="Gloabl Delimiter Change"
)
def changeFieldDelimiter(file: CSVFile, target_delimiter=";"):
    """Change the field delimiter used between columns."""
    file.field_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//field_delimiter")
    for fd in query:
        fd.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])

    _set_polluted_filename(file, f"file_field_delimiter{del_string}.csv")

@pollution(
    category="Dialect and Lexical-Syntax",
    name="Global Change of Escaping Strategy",
)
@manually_verified
def changeEscapeCharacter(file: CSVFile, target_escape="\\"):
    """Changes the escape character used for quoted content.
    Replaces the CSV escape character used to escape quotation marks and other
    special characters (everywhere in the file).
    """
    file.escape_char = target_escape
    root = file.xml.getroot()

    # Literal occurrences of the new escape character already present in the cell
    # data must themselves be escaped, otherwise a parser using this escape
    # character would consume them (e.g. a literal "\" before a quote/delimiter
    # would be read as an escape sequence, dropping the backslash or breaking the
    # field boundary). We represent the escape structurally, by splitting the
    # <value> on the escape char and inserting <escape_char> elements between the
    # fragments, exactly as escaped quotes are stored. This way the serialized
    # CSV shows the doubled character while write_clean_csv (which reads only
    # <value> text) still recovers the original single character. The quotation
    # character is left untouched; its escaping is handled by the existing
    # <escape_char> elements rewritten below.
    if target_escape and target_escape != file.quotation_char:
        for cell in root.xpath("//cell"):
            for value in list(cell):
                if (
                    value.tag != "value"
                    or not value.text
                    or target_escape not in value.text
                ):
                    continue
                parts = value.text.split(target_escape)
                value.text = parts[0]
                insert_at = cell.index(value) + 1
                for part in parts[1:]:
                    cell.insert(insert_at, E.escape_char(target_escape))
                    cell.insert(insert_at + 1, E.value(target_escape + part))
                    insert_at += 2

    query = root.xpath(f"//escape_char")
    for e in query:
        e.text = target_escape

    if target_escape != "":
        vals = [ord(x) for x in target_escape]
        e_string = "".join([f"_0x{v:X}" for v in vals])
        _set_polluted_filename(file, f"file_escape_char{e_string}.csv")
    else:
        _set_polluted_filename(file, f"file_escape_char_0x00.csv")


@pollution(
    category="Dialect and Lexical-Syntax",
    name="Gloabl Quote Character Change",
)
@manually_verified
def changeQuotationChar(file: CSVFile, target_char="\u0022"):

    old_char = file.quotation_char
    file.quotation_char = target_char
    root = file.xml.getroot()

    # Remove the escapes that guarded literal *old* quote chars (only if they're not still escape char)
    if old_char and old_char not in (file.escape_char, target_char):
        for cell in root.xpath("//cell"):
            for esc in [c for c in cell if c.tag == "escape_char"]:
                nxt = esc.getnext()
                if nxt is None or nxt.tag != "value" or not (nxt.text or "").startswith(old_char):
                    # skips everything but escape chars followed by old quote chars
                    continue
                prev = esc.getprevious()
                if prev is not None and prev.tag == "value":
                    prev.text = (prev.text or "") + (nxt.text or "")
                    cell.remove(nxt)
                cell.remove(esc)
        
    # Point every structural quote at the new character.
    for qc in root.xpath("//quotation_char"):
        qc.text = target_char

    # Escape literal *new* quote chars now sitting in the content
    # (Skip when the new quote char equals the old quote char (no-op)
    # or the escape char as any literal copies are already escaped and re-escaping would
    # double them up
    if target_char and file.escape_char and target_char not in (old_char, file.escape_char):
        for cell in root.xpath("//cell"):
            for value in list(cell):
                if value.tag != "value" or not value.text or target_char not in value.text:
                    continue
                parts = value.text.split(target_char)
                value.text = parts[0]
                insert_at = cell.index(value) + 1
                for part in parts[1:]:
                    cell.insert(insert_at, E.escape_char(file.escape_char))
                    cell.insert(insert_at + 1, E.value(target_char + part))
                    insert_at += 2

    if target_char:
        vals = [ord(x) for x in target_char]
        quote_string = "".join([f"_0x{v:X}" for v in vals])
    else:
        quote_string = "_none"

    _set_polluted_filename(file, f"file_quotation_char{quote_string}.csv")

@pollution(category="Header and Schema-Layout", name="Synthetic Row Identifier")
def addSynthethicRowID(file: CSVFile):
    """
    Adds a synthetic row identifier column as the first column of the table.

    The new column contains a header ('row_id') and sequential row numbers for
    all data rows.

    Before:
        +-------+--------+--------+
        | name  | city   | amount |
        +-------+--------+--------+
        | Alice | Berlin | 10     |
        | Bob   | Munich | 20     |
        +-------+--------+--------+

    After:
        +--------+-------+--------+--------+
        | row_id | name  | city   | amount |
        +--------+-------+--------+--------+
        | 1      | Alice | Berlin | 10     |
        | 2      | Bob   | Munich | 20     |
        +--------+-------+--------+--------+
    """
    root = file.xml.getroot()
    n_rows = len(root.xpath("//row"))
    pb.addCells(
        file, row=1, position=0, content="row_id", n_cells=1, role="row_id_header"
    )

    for row in range(2, n_rows + 1):
        pb.addCells(
            file, row=row, position=0, content=str(row - 1), n_cells=1, role="row_id"
        )


@pollution(category="Record-Shape and Alignment", name="Truncated Columns")
def changeRowNumberFields(file: CSVFile, row=1, target_n_cells=1):
    """Change how many fields a single row contains."""
    if target_n_cells == -1 or target_n_cells == file.col_count:
        strtype = "homogeneous"
    if target_n_cells == 0:
        strtype = "empty"
        pb.deleteCells(file, row=row, col=list(range(target_n_cells, file.col_count)))
    elif target_n_cells < file.col_count:
        strtype = "less"
        pb.deleteCells(file, row=row, col=list(range(target_n_cells, file.col_count)))
    elif target_n_cells > file.col_count:
        strtype = "more"
        root = file.xml.getroot()
        content = "".join(
            [
                v.text
                for v in root.xpath(f"//row[{row}]/cell[last()]")[0]
                if v.tag == "value"
            ]
        )
        pb.addCells(
            file,
            row=row,
            position=-1,
            content=content,
            n_cells=target_n_cells - file.col_count,
        )

    _set_polluted_filename(file, f"row_n_fields_{row}_{strtype}.csv")


@pollution(category="Dialect and Lexical-Syntax", name="Trailing Delimiters")
def addRowFieldDelimiter(file: CSVFile, row, col, n_separators=1):
    """Insert an extra field delimiter into one row."""
    root = file.xml.getroot()
    row_xml = root.xpath(f"//row[{row + 1}]")[0]
    delimiter = E.field_delimiter(file.field_delimiter)
    if col == 0:
        index = 0
    else:
        index = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"][
            col - 1
        ]
    row_xml.insert(index, delimiter)

    _set_polluted_filename(file, f"row_add_separator_{row}_{col}.csv")


@pollution(category="Undefined", name="deleteRowFieldDelimiter")
def deleteRowFieldDelimiter(file: CSVFile, row, col):
    """Remove a field delimiter from one row."""
    root = file.xml.getroot()

    row_xml = root.xpath(f"//row[{row + 1}]")[0]
    if col == 0:
        pass
    else:
        index = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"][
            col - 1
        ]
        del row_xml[index]

    _set_polluted_filename(file, f"row_n_separator_{file.col_count - 1}.csv")

@pollution(
    category="Dialect and Lexical-Syntax", name="Extra Quote at start of cell"
)
@manually_verified
def addRowQuoteMark(file: CSVFile, row, col):
    """Add an opening quote to one cell in a row."""
    if type(row) == int and row < 0:
        row_query = "last()-" + str(-row - 1)  # row is 0-based: -1 -> last()
    else:
        row_query = row + 1  # xpath is 1-based
    root = file.xml.getroot()
    row_xml = root.xpath(f"//row[{row_query}]")[0]
    index = [i for i, x in enumerate(row_xml) if x.tag == "cell"][col]
    for c in row_xml[index]:
        if c.tag == "value":
            old = c.text or ""
            c.text = file.quotation_char + old
            break

    _set_polluted_filename(file, f"row_extra_quote{row}_col{col}.csv")


@pollution(
    category="Dialect and Lexical-Syntax", name="Mixed Record Terminators"
)
def changeRowRecordDelimiter(file: CSVFile, row=1, target_delimiter="\r\n"):
    """Change the record delimiter used by one row."""
    if type(row) == int and row < 0:
        row = "last()-" + str(-row - 1)  # -1 -> last(), -2 -> last()-1

    root = file.xml.getroot()
    root.xpath(f"//row[{row}]/record_delimiter")[0].text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])
    _set_polluted_filename(file, f"row_record_delimiter_{row}{del_string}.csv")


# obsolete due to function in mixedDelimiter function in v2 
@pollution(category="Dialect and Lexical-Syntax", name="Mixed Delimiters")
def changeRowFieldDelimiter(file: CSVFile, row=1, target_delimiter=";"):
    """Change the field delimiter used by one row."""
    root = file.xml.getroot()
    query = root.xpath(f"//row[{row + 1}]/field_delimiter")
    for r in query:
        r.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])
    _set_polluted_filename(file, f"row_field_delimiter_{row}{del_string}.csv")


@pollution(
    category="Dialect and Lexical-Syntax",
    name="Row-Wise Quote Character Ambiguity",
)
def changeRowQuotationMark(file: CSVFile, row=1, target_quotation="'"):
    """Change the quotation mark used by one row. Row indexing is 1-based. Follows xquery."""
    old_char = file.quotation_char
    root = file.xml.getroot()
    row_cells = f"//row[{row}]//cell"

    # unescape instances of the old quotation char if they are not part of the grammar anymore
    if old_char and old_char not in (file.escape_char, target_quotation):
        for cell in root.xpath(row_cells):
            for esc in [c for c in cell if c.tag == "escape_char"]:
                nxt = esc.getnext()
                if nxt is None or nxt.tag != "value" or not (nxt.text or "").startswith(old_char):
                    continue
                prev = esc.getprevious()
                if prev is not None and prev.tag == "value":
                    prev.text = (prev.text or "") + (nxt.text or "")
                    cell.remove(nxt)
                cell.remove(esc)

    # swap quotation char instances
    for r in root.xpath(f"//row[{row}]//quotation_char"):
        r.text = target_quotation

    # escape literal instances of the new quotation char that appear in cell text
    if target_quotation and file.escape_char and target_quotation not in (old_char, file.escape_char):
        for cell in root.xpath(row_cells):
            for value in list(cell):
                if value.tag != "value" or not value.text or target_quotation not in value.text:
                    continue
                parts = value.text.split(target_quotation)
                value.text = parts[0]
                insert_at = cell.index(value) + 1
                for part in parts[1:]:
                    cell.insert(insert_at, E.escape_char(file.escape_char))
                    cell.insert(insert_at + 1, E.value(target_quotation + part))
                    insert_at += 2

    vals = [ord(x) for x in target_quotation]
    quote_string = "".join([f"_0x{v:X}" for v in vals])
    _set_polluted_filename(file, f"row_quotation_mark_{row}{quote_string}.csv")


@pollution(category="Undefined", name="changeColumnHeader")
def changeColumnHeader(
    file: CSVFile, col: int = None, target_header=None, extra_rows=0
):
    """Change one or more header cells, optionally across extra header rows.
    If col is none, apply to all of them-
    If >0, extra rows expands the header on X many rows"""
    colint = col
    if type(col) == list:
        [pb.changeCell(file, row=1, col=c, new_content=target_header) for c in col]
    elif col is not None:
        pb.changeCell(file, row=1, col=col, new_content=target_header)
    elif col is None:
        [
            pb.changeCell(file, row=1, col=c, new_content=target_header)
            for c in range(file.col_count)
        ]

    if extra_rows > 0:
        if type(target_header) == str:
            cell_content = [""] * (file.col_count)
            if type(col) == list:
                for c in cell_content:
                    cell_content[c] = target_header
            else:
                cell_content[colint] = target_header
        else:
            cell_content = target_header
        pb.addRows(
            file,
            n_rows=extra_rows,
            cell_content=cell_content,
            position=0,
            col_count=file.col_count,
        )

    if len(target_header) in range(1, 255):
        strtype = "regular"
    elif not len(target_header):
        strtype = "empty"
    else:
        strtype = "large"
    if not target_header.isalnum():
        strtype += "_nonalnum"

    _set_polluted_filename(
        file, f"column_header_{col}_{strtype}{'_multiple' if extra_rows > 0 else ''}{'_nonunique' if type(col) == list else ''}.csv")

@pollution(
    category="File Segmentation and Table-Boundary", name="Stacked Tables"
)
@manually_verified
def addTable(file: CSVFile, n_rows, n_cols, empty_boundary=True):
    """Append a second, vertically stacked table with the requested shape.

    The secondary table is derived from the first rows of the primary table.
    Narrower variants drop trailing columns. Wider variants add source-derived
    Related <column> fields so additional columns contain plausible data instead
    of empty padding.

    Args:
        file: CSVFile object to modify
        n_rows: maximum number of rows in the new table, including its header
        n_cols: number of columns in the new table
        empty_boundary: if True, adds a genuinely blank row between the tables
    """
    if n_rows < 1:
        raise ValueError("n_rows must be at least 1")
    if n_cols < 1:
        raise ValueError("n_cols must be at least 1")

    root = file.xml.getroot()

    # Extracting rows for second table
    primary_rows = root.xpath("//table[1]/row")
    if not primary_rows:
        raise ValueError("Cannot add a table to a file without source rows")

    n_rows = min(n_rows, len(primary_rows))
    source_rows = [
        [
            "".join(v.text or "" for v in cell if v.tag == "value")
            for cell in row.xpath("./cell")
        ]
        for row in primary_rows[:n_rows]
    ]
    source_width = max(len(row) for row in source_rows)
    if source_width == 0:
        raise ValueError("Cannot add a table from rows without cells")

    if n_cols == source_width:
        strtype = "same"
    elif n_cols < source_width:
        strtype = "less"
    else:
        strtype = "more"

    secondary_table = etree.SubElement(root, "table")
    if empty_boundary:
        pb.addRows(
            file,
            cell_content="",
            n_rows=1,
            position=0,
            col_count=0,
            role="secondary_boundary",
            table=1,
        )

    usable_source_cols = [
        col
        for col in range(source_width)
        if any(col < len(row) and row[col].strip() for row in source_rows[1:])
    ]
    if not usable_source_cols:
        usable_source_cols = list(range(source_width))

    extra_cols = max(0, n_cols - source_width)
    secondary_ground_truth = []
    for row_idx, source_row in enumerate(source_rows):
        row_values = (source_row + [""] * source_width)[: min(n_cols, source_width)]

        for extra_idx in range(extra_cols):
            source_col = usable_source_cols[extra_idx % len(usable_source_cols)]
            source_value = source_row[source_col] if source_col < len(source_row) else ""
            if row_idx == 0:
                source_name = source_value or f"Column {source_col + 1}"
                repetition = extra_idx // len(usable_source_cols) + 1
                suffix = f" {repetition}" if repetition > 1 else ""
                row_values.append(f"Related {source_name}{suffix}")
            else:
                row_values.append(source_value)

        secondary_ground_truth.append(row_values)
        pb.addRows(
            file,
            cell_content=row_values,
            n_rows=1,
            position=len(secondary_table),
            col_count=n_cols,
            role="secondary_header" if row_idx == 0 else "secondary_data",
            table=1,
        )

    file.ground_truth_bundle = GroundTruthBundle(
        tables=(
            GroundTruthTable.from_rows(
                "primary", CSVFile.clean_rows(file), role="primary"
            ),
            GroundTruthTable.from_rows(
                "secondary",
                secondary_ground_truth,
                role="secondary",
            ),
        ),
        alternatives=(
            GroundTruthAlternative(
                id="primary_only",
                table_ids=("primary",),
                comparison="single_table",
            ),
            GroundTruthAlternative(
                id="secondary_only",
                table_ids=("secondary",),
                comparison="single_table",
            ),
            GroundTruthAlternative(
                id="all_tables",
                table_ids=("primary", "secondary"),
                comparison="ordered_tables",
            ),
        ),
        canonical="all_tables",
    )

    suffix = "_separated" if empty_boundary else ""
    _set_polluted_filename(
        file,
        f"file_multitable_rows_{n_rows}_{strtype}_cols{suffix}.csv",
    )
