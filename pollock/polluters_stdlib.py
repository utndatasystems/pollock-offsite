import random
import string
import time
from lxml import etree
from .CSVFile import CSVFile
from lxml.builder import E
from .randdata import randomString, randomDateStr, randomType, randomInt
from dateutil.parser import parse

from . import constants
from . import polluters_base as pb
from pollock.polluters_utils import _set_polluted_filename, _row_values, _safe_row_count, _safe_col_count


def dummyPolluter(file: CSVFile):
    pass


# --- Pollock1.0 Pollutions ---

def changeDimension(file: CSVFile, target_dimension=-1):
    content = []
    for i in range(file.row_count):
        texts = [x.text or "" for x in file.xml.xpath(f"//row[{i + 1}]//*[not(*)]")]
        content.append("".join(texts))
    textcontent = "".join(content)
    cur_size = len(textcontent)

    last_row_cells = [x for x in file.xml.xpath("//row[last()]//cell")]
    last_row_content = [
        "".join(v.text or "") for c in last_row_cells for v in c if v.tag == "value"
    ]

    size_last_row = len("".join(content[-1]))
    n_rows = int((target_dimension - cur_size) / size_last_row)

    if target_dimension > cur_size:
        pb.addRows(
            file, cell_content=last_row_content, n_rows=n_rows, position=-1, role="data"
        )
    elif 0 <= target_dimension < cur_size:
        n_rows_to_keep = textcontent.count("\r\n", target_dimension)
        if target_dimension:
            n_rows_to_keep -= 1  # exclude the current if dimension breaks one in half (if not exactly 0)
        remove_rows = list(range(file.row_count - n_rows_to_keep, file.row_count + 1))
        pb.deleteRows(file, rows_to_delete=remove_rows)

    # TODO: use utils function here
    file.filename = "file_size_" + str(target_dimension) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def changeEncoding(file: CSVFile, target_encoding: constants.Encoding):
    target = (
        target_encoding.value
        if type(target_encoding) == constants.Encoding
        else target_encoding
    )
    assert target in constants.Encoding.supported_encodings.value

    file.encoding = target
    file.filename = "file_encoding_" + target + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename
    file.xml.getroot().attrib["encoding"] = target


def changeNumberColumns(file: CSVFile, target_number_cols: int):
    if target_number_cols < file.col_count:
        cols_delete = list(range(target_number_cols, file.col_count))
        pb.deleteColumns(file, col=cols_delete)

    if target_number_cols > file.col_count:
        rn = range(file.col_count, target_number_cols)
        t = time.time()
        roles = ["header"] + ["data"] * (file.row_count - 1)
        content = []

        for i in range(file.row_count):
            content += [
                "".join(
                    [
                        val.text
                        for val in file.xml.xpath(f"//row[{i + 2}]/cell[last()]/value")
                    ]
                )
            ]  # xpath is 1-indexed plus row 1 is header
        pb.addColumns(
            file,
            -1,
            col_names=["col" + str(i + 1) for i in rn],
            n_cols=len(rn),
            cell_content=content,
            role=roles,
        )
        print("took", time.time() - t, "seconds")

    file.filename = "file_num_columns_" + str(target_number_cols) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def changeNumberRows(file: CSVFile, target_number_rows: int, remove_header=False):
    last_row_cells = [x for x in file.xml.xpath("//row[last()]//cell")]
    last_row_content = [
        "".join(v.text or "") for c in last_row_cells for v in c if v.tag == "value"
    ]

    if remove_header:
        pb.deleteRows(file, [0])

    if target_number_rows < file.row_count:
        rows_delete = list(range(target_number_rows, file.row_count))
        pb.deleteRows(file, rows_to_delete=rows_delete)

    if target_number_rows > file.row_count:
        n_rows = target_number_rows - file.row_count
        t = time.time()
        pb.addRows(
            file, cell_content=last_row_content, n_rows=n_rows, position=-1, role="data"
        )
        print("took", time.time() - t, "seconds")

    file.filename = f"file_num_rows_{str(target_number_rows)}{'_no_header' if remove_header else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def expandColumnHeader(file: CSVFile, extra_rows=1):
    header = [x for x in file.xml.xpath(f"//row[{1}]//value//node()[not(node())]")]
    pb.addRows(file, cell_content=header, n_rows=extra_rows, position=0, role="header")

    file.filename = "file_multirow_header_" + str(extra_rows) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addPreamble(
    file: CSVFile, n_rows=1, delimiters=False, emptyrow=False, cell_content="PREAMBLE"
):
    """
    :param file:
    :param n_rows: number of rows for the preamble
    :param delimiters: if True, creates a row with as many delimited cells as the other rows
    :param emptyrow:  if True, leaves an empty row between the preamble and the data
    :param cell_content: the content of the preamble cell(s). Either list or single value
    """
    if emptyrow:
        if not delimiters:
            pb.addRows(
                file, n_rows=1, position=0, col_count=file.col_count, role="preamble"
            )
        if delimiters:
            pb.addRows(
                file,
                n_rows=1,
                position=0,
                cell_content=[""] * file.col_count,
                col_count=file.col_count,
                role="preamble",
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
            position=0,
            col_count=file.col_count,
            role="preamble",
        )

    else:
        pb.addRows(
            file,
            n_rows=n_rows,
            cell_content=cell_content,
            position=0,
            col_count=1,
            role="preamble",
        )

    file.filename = f"file_preamble_{n_rows}_{'not_' if not delimiters else ''}delimited{'_empty_row' if emptyrow else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def addFootnote(
    file: CSVFile, n_rows=1, delimiters=False, emptyrow=False, cell_content="FOOTNOTE"
):
    """
    :param file:
    :param n_rows: number of rows for the preamble
    :param delimiters: if True, creates a row with as many delimited cells as the other rows
    :param emptyrow:  if True, leaves an empty row between the preamble and the data
    :param cell_content: the content of the preamble cell(s). Either list or single value
    """
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
    return


def changeRecordDelimiter(file: CSVFile, target_delimiter="\r\n"):
    file.record_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//record_delimiter")
    for r in query:
        r.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])

    _set_polluted_filename(file, f"file_record_delimiter{del_string}.csv")
    return


def changeFieldDelimiter(file: CSVFile, target_delimiter=";"):
    file.field_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//field_delimiter")
    for fd in query:
        fd.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])

    # TODO: use utils function here
    file.filename = f"file_field_delimiter{del_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeEscapeCharacter(file: CSVFile, target_escape="\\"):
    file.escape_char = target_escape
    root = file.xml.getroot()
    query = root.xpath(f"//escape_char")
    for e in query:
        e.text = target_escape

    if target_escape != "":
        vals = [ord(x) for x in target_escape]
        e_string = "".join([f"_0x{v:X}" for v in vals])
        file.filename = f"file_escape_char{e_string}.csv"
    else:
        file.filename = f"file_escape_char_0x00.csv"

    file.xml.getroot().attrib["filename"] = file.filename


def changeQuotationChar(file: CSVFile, target_char="\u0022"):
    file.quotation_char = target_char
    root = file.xml.getroot()
    query = root.xpath(f"//quotation_char")
    for idx, qc in enumerate(query):
        if not idx % 2:
            qc.text = target_char
        else:
            qc.text = target_char[::-1]  # reverse it for multi-line

    index = [i for i, x in enumerate(root) if x.tag == "escape_char"]
    for i in index:
        del root[i]  # TODO

    vals = [ord(x) for x in target_char]
    quote_string = "".join([f"_0x{v:X}" for v in vals])
    file.filename = f"file_quotation_char{quote_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addSynthethicRowID(file: CSVFile):
    root = file.xml.getroot()
    n_rows = len(root.xpath("//row"))
    pb.addCells(
        file, row=1, position=0, content="row_id", n_cells=1, role="row_id_header"
    )

    for row in range(2, n_rows + 1):
        pb.addCells(
            file, row=row, position=0, content=str(row - 1), n_cells=1, role="row_id"
        )


def changeRowNumberFields(file: CSVFile, row=1, target_n_cells=1):
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

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

    file.filename = f"row_n_fields_{row}_{strtype}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addRowFieldDelimiter(file: CSVFile, row, col, n_separators=1):
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

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

    file.filename = f"row_add_separator_{row}_{col}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def deleteRowFieldDelimiter(file: CSVFile, row, col):
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    root = file.xml.getroot()

    row_xml = root.xpath(f"//row[{row + 1}]")[0]
    if col == 0:
        pass
    else:
        index = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"][
            col - 1
        ]
        del row_xml[index]

    file.filename = f"row_n_separator_{file.col_count - 1}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addRowQuoteMark(file: CSVFile, row, col):
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    root = file.xml.getroot()
    row_xml = root.xpath(f"//row[{row + 1}]")[0]
    index = [i for i, x in enumerate(row_xml) if x.tag == "cell"][col]
    for c in row_xml[index]:
        if c.tag == "value":
            old = c.text or ""
            c.text = file.quotation_char + old
            break

    file.filename = f"row_n_separator_{file.col_count - 1}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeRowRecordDelimiter(file: CSVFile, row=1, target_delimiter="\r\n"):
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    root = file.xml.getroot()
    root.xpath(f"//row[{row}]/record_delimiter")[0].text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])
    file.filename = f"row_record_delimiter_{row}{del_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeRowFieldDelimiter(file: CSVFile, row=1, target_delimiter=";"):
    """
    Row indexing is 1-based! Follows xquery
    """
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    root = file.xml.getroot()
    query = root.xpath(f"//row[{row + 1}]/field_delimiter")
    for r in query:
        r.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = "".join([f"_0x{v:X}" for v in vals])
    file.filename = f"row_field_delimiter_{row}{del_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeRowQuotationMark(file: CSVFile, row=1, target_quotation="'"):
    """
    Row indexing is 1-based! Follows xquery
    """
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    root = file.xml.getroot()
    query = root.xpath(f"//row[{row}]//quotation_char")
    for r in query:
        r.text = target_quotation

    vals = [ord(x) for x in target_quotation]
    quote_string = "".join([f"_0x{v:X}" for v in vals])
    _set_polluted_filename(file, f"row_quotation_mark_{row}{quote_string}.csv")


def changeColumnHeader(
    file: CSVFile, col: int = None, target_header=None, extra_rows=0
):
    """
    If col is none, apply to all of them-
    If >0, extra rows expands the header on X many rows
    """
    colint = col
    if type(col) == int and col < 0:
        col = "last()-" + str(col + 1)

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

    file.filename = f"column_header_{col}_{strtype}{'_multiple' if extra_rows > 0 else ''}{'_nonunique' if type(col) == list else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addTable(file: CSVFile, n_rows, n_cols, empty_boundary=True):
    """Adds a table after the first one with n_rows and n_cols.
    Additionally, can be specified if the two are separated by empty delimited rows or not.
    """

    random.seed(constants.RAND_SEED)
    root = file.xml.getroot()
    old_table = root.xpath("//table")[0]
    new_table = etree.SubElement(root, "table")

    content = []
    for i in range(n_rows):
        content += [[x.text for x in old_table.xpath(f"//row[{i + 1}]//value")]]

    for i in range(n_rows):
        row_cells = content[i]
        pb.addRows(
            file, cell_content=row_cells, n_rows=1, position=file.row_count + 1, table=1
        )

    if n_cols == file.col_count:
        strtype = "same"
    elif n_cols < file.col_count:
        strtype = "less"
        cols_delete = list(range(n_cols, file.col_count))
        pb.deleteColumns(file, col=cols_delete, table=1)
    elif n_cols > file.col_count:
        strtype = "more"
        cols_add = len(range(file.col_count, n_cols))
        col_names = ["col" + str(i + 1) for i in range(cols_add)]
        content = []
        for i in range(1, n_rows):
            content += [
                file.xml.xpath(f"//table[1]//row[{i + 1}]/cell[last()]/value")[0].text
            ]

        pb.addColumns(
            file,
            position=file.col_count + 1,
            n_cols=cols_add,
            col_names=col_names,
            cell_content=content,
            table=1,
        )

    if empty_boundary:
        pb.addRows(file, cell_content="", n_rows=1, position=0, table=1)

    file.filename = f"file_multitable_rows_{n_rows}_{strtype}_cols{'_separated' if empty_boundary else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    # TODO: use _set_polluted_filename for all of these

# --- New Pollutions for Pollock 2.0 below ---

def addTableSideways(
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
    rnd = random_content

    # TODO: fix this function. As of now, the table is inserted correctly, but the 'padding cells' are filled with empty quotation marks

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

    if rnd:
        new_table = [
            [
                "".join(random.choices(string.ascii_letters + string.digits, k=8))
                for _ in range(n_cols)
            ]
            for _ in range(n_rows)
        ]
    else:
        new_table = []
        for r_idx in range(n_rows):
            values = [
                "".join(v.text or "" for v in cell if v.tag == "value")
                for cell in source_rows[r_idx].xpath("./cell")
            ]

            if len(values) < n_cols:
                values += [""] * (n_cols - len(values))

            new_table.append(values[:n_cols])

    total_rows = len(file.xml.getroot().xpath("//table[1]/row"))

    # boundary column
    if empty_boundary:
        pb.addColumns(
            file,
            position=file.col_count,
            n_cols=1,
            col_names=[""],
            cell_content=[""] * (total_rows - 1),
            role=["spurious"] * total_rows,
            table=0,
        )

    for c_idx in range(n_cols):
        col_content = [new_table[r_idx][c_idx] for r_idx in range(n_rows)]

        padded_data_content = col_content[1:] + [""] * (total_rows - n_rows)

        pb.addColumns(
            file,
            position=file.col_count,
            n_cols=1,
            col_names=[col_content[0]],
            cell_content=padded_data_content,
            role=["header"] + ["data"] * (total_rows - 1),
            table=0,
        )

    _set_polluted_filename(
        file,
        f"file_multitable_sideways_rows_{n_rows}_cols_{n_cols}"
        f"{'_random' if rnd else ''}"
        f"{'_separated' if empty_boundary else ''}.csv",
    )


def multilineHeader(  # checked manually
    file: CSVFile,
    header_col=5,
    header_rows=3,
    content="ExampleLineHeader",
):
    """
    Adds multiline header rows ABOVE the original table.

    Each inserted row contains only a single cell:
        Line1
        Line2
        Line3

    No extra delimiters are inserted.
    """
    for i in reversed(range(header_rows)):
        pb.addRows(
            file,
            cell_content=f"{content}{i + 1}",
            n_rows=1,
            position=0,
            col_count=1,  # IMPORTANT: only one cell
            role="header",
        )

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
    pass
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
    Simulates commented-out CSV rows by prefixing the first cell with a comment marker.
    """
    if row is None:
        row = random.randint(1, _safe_row_count(file))

    cells = pb.getRowCells(file, row)
    if not cells or len(cells) == 0:
        return

    value = pb.get_cell_value(cells[0])
    pb.changeCell(
        file,
        row=row + 1,  # XPath indexing
        col=1,
        new_content=f"{comment_marker}{space}{value}",
    )
    _set_polluted_filename(file, f"file_commented_row_{row}.csv")


def metadataAsHeader(  # checked manually
    file: CSVFile,
    content="This is a superheader with metadata info.\nInstrument 3AdF\nExperiment Number 3",
):
    """
    Adds several metadata-like rows above the real header.
    Each line in `content` becomes its own CSV row.
    """

    lines = content.splitlines()

    # insert in reverse so final order is preserved
    for line in reversed(lines):
        pb.addRows(
            file,
            cell_content=line,
            n_rows=1,
            position=0,
            col_count=1,
            role="superheader",
        )

    _set_polluted_filename(file, "file_metadata_as_header.csv")


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
        row = random.randint(1, _safe_row_count(file))

    rowCells = pb.getRowCells(file, row)
    col = random.randint(0, len(rowCells))

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


def embeddedJSON(file: CSVFile):
    """Embeds JSON-like file content inside a single cell."""
    payload = '{"name":"example.json","rows":[{"id":1,"value":"alpha"},{"id":2,"value":"beta"}]}'
    pb.changeCell(
        file, row=2 if _safe_row_count(file) >= 2 else 1, col=1, new_content=payload
    )
    _set_polluted_filename(file, "file_embedded_json_cell.csv")


def embeddedCSV(file: CSVFile):
    """Embeds CSV-like file content inside a single cell."""
    payload = "id,name\n1,alpha\n2,beta"
    pb.changeCell(
        file, row=2 if _safe_row_count(file) >= 2 else 1, col=1, new_content=payload
    )
    _set_polluted_filename(file, "file_embedded_csv_cell.csv")
    pass


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
    pass
    # TODO: fix
    """Adds a UTF-8 BOM marker to the first header cell."""
    first = _row_values(file, row=1)[0] if _row_values(file, row=1) else ""
    pb.changeCell(file, row=1, col=1, new_content="\ufeff" + first)
    file.xml.getroot().attrib["bom"] = "utf-8"
    _set_polluted_filename(file, "file_utf8_bom.csv")


def weirdUnicode(file: CSVFile):
    # TODO: inject in middle of CSV not end of CSV
    """Adds mojibake and non-ASCII strings."""
    row = ["FranÃ§ois", "MÃ¼nchen", "SÃ£o Paulo", "â‚¬", "👍🏼"]
    row = row[: file.col_count] + [""] * max(file.col_count - len(row), 0)
    pb.addRows(
        file,
        cell_content=row,
        n_rows=1,
        position=_safe_row_count(file),
        col_count=file.col_count,
        role="data",
    )
    _set_polluted_filename(file, "file_weird_unicode_mojibake.csv")


def invisibleCharacters(file: CSVFile):
    # TODO: inject in middle of CSV not end of CSV
    """Adds zero-width and non-breaking characters to cells."""
    values = [
        "zero\u200bwidth",
        "non\u00a0breaking",
        "left\u200emark",
        "word\ufeffjoiner",
    ]
    row = values[: file.col_count] + [""] * max(file.col_count - len(values), 0)
    pb.addRows(
        file,
        cell_content=row,
        n_rows=1,
        position=_safe_row_count(file),
        col_count=file.col_count,
        role="data",
    )
    _set_polluted_filename(file, "file_invisible_characters.csv")


def collations(file: CSVFile):
    """Adds strings whose sort order differs by locale/collation."""
    # TODO: insert in middle of file, not end of file
    # TODO: make value a parameter in function and iterate over them in pollute_main
    for value in ["ä", "z", "å", "a", "Á", "á", "ß", "ss"]:
        row = [value] + [""] * max(file.col_count - 1, 0)
        pb.addRows(
            file,
            cell_content=row,
            n_rows=1,
            position=_safe_row_count(file),
            col_count=file.col_count,
            role="data",
        )
    _set_polluted_filename(file, "file_collation_edge_cases.csv")


def mixedTypes(file: CSVFile, row: int | None = None):
    """Adds values with incompatible types in the same logical column."""
    if row is None:
        row = random.randint(1, _safe_row_count(file))

    for row in range(5):
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
        pb.changeCell(file, row=row_idx, col=col_idx, new_content=randomDateStr())

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
