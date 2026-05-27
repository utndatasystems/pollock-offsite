import random
import string
import time
from tokenize import group
from lxml import etree
from . import constants
from . import polluters_base as pb
from .CSVFile import CSVFile
from lxml.builder import E

def dummyPolluter(file: CSVFile):
    pass

def changeFilename(file: CSVFile, target_name):
    file.filename = target_name
    file.xml.getroot().attrib["filename"] = target_name


def changeDimension(file: CSVFile, target_dimension=-1):
    content = []
    for i in range(file.row_count):
        texts = [x.text or "" for x in file.xml.xpath(f"//row[{i + 1}]//*[not(*)]")]
        content.append("".join(texts))
    textcontent = "".join(content)
    cur_size = len(textcontent)

    last_row_cells = [x for x in file.xml.xpath("//row[last()]//cell")]
    last_row_content = ["".join(v.text or "") for c in last_row_cells for v in c if v.tag == "value"]

    size_last_row = len("".join(content[-1]))
    n_rows = int((target_dimension - cur_size) / size_last_row)

    if target_dimension > cur_size:
        pb.addRows(file, cell_content=last_row_content, n_rows=n_rows, position=-1, role="data")
    elif 0 <= target_dimension < cur_size:
        n_rows_to_keep = textcontent.count("\r\n", target_dimension)
        if target_dimension:
            n_rows_to_keep -= 1  # exclude the current if dimension breaks one in half (if not exactly 0)
        remove_rows = list(range(file.row_count - n_rows_to_keep, file.row_count + 1))
        pb.deleteRows(file, rows_to_delete=remove_rows)

    file.filename = "file_size_" + str(target_dimension) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename

    return


def changeEncoding(file: CSVFile, target_encoding: constants.Encoding):
    target = target_encoding.value if type(target_encoding) == constants.Encoding else target_encoding
    assert (target in constants.Encoding.supported_encodings.value)

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
                "".join([val.text for val in file.xml.xpath(f"//row[{i + 2}]/cell[last()]/value")])]  # xpath is 1-indexed plus row 1 is header
        pb.addColumns(file, -1, col_names=["col" + str(i + 1) for i in rn], n_cols=len(rn), cell_content=content, role=roles)
        print("took", time.time() - t, "seconds")

    file.filename = "file_num_columns_" + str(target_number_cols) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def changeNumberRows(file: CSVFile, target_number_rows: int, remove_header=False):
    last_row_cells = [x for x in file.xml.xpath("//row[last()]//cell")]
    last_row_content = ["".join(v.text or "") for c in last_row_cells for v in c if v.tag == "value"]

    if remove_header:
        pb.deleteRows(file, [0])

    if target_number_rows < file.row_count:
        rows_delete = list(range(target_number_rows, file.row_count))
        pb.deleteRows(file, rows_to_delete=rows_delete)

    if target_number_rows > file.row_count:
        n_rows = target_number_rows - file.row_count
        t = time.time()
        pb.addRows(file, cell_content=last_row_content, n_rows=n_rows, position=-1, role="data")
        print("took", time.time() - t, "seconds")

    file.filename = f"file_num_rows_{str(target_number_rows)}{'_no_header' if remove_header else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return

def expandColumnHeader(file: CSVFile, extra_rows=1):
    header = [x for x in file.xml.xpath(f"//row[{1}]//value//node()[not(node())]")]
    pb.addRows(file, cell_content=header, n_rows=extra_rows, position=0, role="header")

    file.filename = "file_multirow_header_" + str(extra_rows) + ".csv"
    file.xml.getroot().attrib["filename"] = file.filename

def addPreamble(file: CSVFile, n_rows=1, delimiters=False, emptyrow=False, cell_content="PREAMBLE"):
    """
    :param file:
    :param n_rows: number of rows for the preamble
    :param delimiters: if True, creates a row with as many delimited cells as the other rows
    :param emptyrow:  if True, leaves an empty row between the preamble and the data
    :param cell_content: the content of the preamble cell(s). Either list or single value
    """
    if emptyrow:
        if not delimiters:
            pb.addRows(file, n_rows=1, position=0, col_count=file.col_count, role="preamble")
        if delimiters:
            pb.addRows(file, n_rows=1, position=0, cell_content=[""] * file.col_count, col_count=file.col_count, role="preamble")

    if delimiters:
        cell_content = [cell_content] + [''] * (file.col_count - 1) if type(cell_content) == str else cell_content
        pb.addRows(file, n_rows=n_rows, cell_content=cell_content, position=0, col_count=file.col_count, role="preamble")

    else:
        pb.addRows(file, n_rows=n_rows, cell_content=cell_content, position=0, col_count=1, role="preamble")

    file.filename = f"file_preamble_{n_rows}_{'not_' if not delimiters else ''}delimited{'_empty_row' if emptyrow else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def addFootnote(file: CSVFile, n_rows=1, delimiters=False, emptyrow=False, cell_content="FOOTNOTE"):
    """
    :param file:
    :param n_rows: number of rows for the preamble
    :param delimiters: if True, creates a row with as many delimited cells as the other rows
    :param emptyrow:  if True, leaves an empty row between the preamble and the data
    :param cell_content: the content of the preamble cell(s). Either list or single value
    """
    if emptyrow:
        pb.addRows(file, n_rows=1, position=-1, col_count=file.col_count, role="footnote")

    if delimiters:
        cell_content = [cell_content] + [''] * (file.col_count - 1) if type(cell_content) == str else cell_content
        pb.addRows(file, n_rows=n_rows, cell_content=cell_content, position=-1, col_count=file.col_count, role="footnote")

    else:
        pb.addRows(file, n_rows=n_rows, cell_content=cell_content, position=-1, col_count=1, role="footnote")

    file.filename = f"file_footnote_{n_rows}_{'not_' if not delimiters else ''}delimited{'_empty_row' if emptyrow else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename
    return


def changeRecordDelimiter(file: CSVFile, target_delimiter="\r\n"):
    file.record_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//record_delimiter")
    for r in query:
        r.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = ''.join([f'_0x{v:X}' for v in vals])
    file.filename = f"file_record_delimiter{del_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeFieldDelimiter(file: CSVFile, target_delimiter=";"):
    file.field_delimiter = target_delimiter
    root = file.xml.getroot()
    query = root.xpath(f"//field_delimiter")
    for fd in query:
        fd.text = target_delimiter

    vals = [ord(x) for x in target_delimiter]
    del_string = ''.join([f'_0x{v:X}' for v in vals])
    file.filename = f"file_field_delimiter{del_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def changeEscapeCharacter(file: CSVFile, target_escape="\\"):
    file.escape_char = target_escape
    root = file.xml.getroot()
    query = root.xpath(f"//escape_char")
    for e in query:
        e.text = target_escape

    if target_escape != '':
        vals = [ord(x) for x in target_escape]
        e_string = ''.join([f'_0x{v:X}' for v in vals])
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
    quote_string = ''.join([f'_0x{v:X}' for v in vals])
    file.filename = f"file_quotation_char{quote_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename


def addSynthethicRowID(file: CSVFile):
    root = file.xml.getroot()
    n_rows = len(root.xpath("//row"))
    pb.addCells(file, row=1, position=0, content="row_id", n_cells=1, role="row_id_header")

    for row in range(2, n_rows + 1):
        pb.addCells(file, row=row, position=0, content=str(row - 1), n_cells=1, role="row_id")


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
        content = "".join([v.text for v in root.xpath(f"//row[{row}]/cell[last()]")[0] if v.tag == "value"])
        pb.addCells(file, row=row, position=-1, content=content, n_cells=target_n_cells - file.col_count)

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
        index = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"][col - 1]
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
        index = [i for i, x in enumerate(row_xml) if x.tag == "field_delimiter"][col - 1]
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
    del_string = ''.join([f'_0x{v:X}' for v in vals])
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
    del_string = ''.join([f'_0x{v:X}' for v in vals])
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
    quote_string = ''.join([f'_0x{v:X}' for v in vals])
    file.filename = f"row_quotation_mark_{row}{quote_string}.csv"
    file.xml.getroot().attrib["filename"] = file.filename

def changeColumnHeader(file: CSVFile, col: int = None, target_header=None, extra_rows=0):
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
        [pb.changeCell(file, row=1, col=c, new_content=target_header) for c in range(file.col_count)]

    if extra_rows > 0:
        if type(target_header) == str:
            cell_content = [''] * (file.col_count)
            if type(col) == list:
                for c in cell_content:
                    cell_content[c] = target_header
            else:
                cell_content[colint] = target_header
        else:
            cell_content = target_header
        pb.addRows(file, n_rows=extra_rows, cell_content=cell_content, position=0, col_count=file.col_count)

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
        pb.addRows(file, cell_content=row_cells, n_rows=1, position=file.row_count + 1, table=1)

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
            content += [file.xml.xpath(f"//table[1]//row[{i + 1}]/cell[last()]/value")[0].text]

        pb.addColumns(file, position=file.col_count + 1, n_cols=cols_add, col_names=col_names, cell_content=content, table=1)

    if empty_boundary:
        pb.addRows(file, cell_content="", n_rows=1, position=0, table=1)

    file.filename = f"file_multitable_rows_{n_rows}_{strtype}_cols{'_separated' if empty_boundary else ''}.csv"
    file.xml.getroot().attrib["filename"] = file.filename

# --- New Pollutions for Pollock 2.0 below ---
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


def addTableSideways(file: CSVFile, n_rows, n_cols):
    """Adds a second table whose source rows are transposed into columns."""
    random.seed(constants.RAND_SEED)
    root = file.xml.getroot()
    old_table = root.xpath("//table")[0]
    new_table = etree.SubElement(root, "table")

    source = []
    for i in range(n_rows):
        values = [x.text or "" for x in old_table.xpath(f"./row[{i + 1}]//value")]
        if len(values) < n_cols:
            values += [""] * (n_cols - len(values))
        source.append(values[:n_cols])

    # Transpose source rows into rows of the new table. This produces a sideways table
    # without relying on addColumns(), which expects rows to already exist.
    for c in range(n_cols):
        row_cells = [source[r][c] for r in range(n_rows)]
        pb.addRows(file, cell_content=row_cells, n_rows=1, position=len(new_table),
                   col_count=n_rows, role="data", table=1)

    _set_polluted_filename(file, f"file_multitable_sideways_rows_{n_rows}_cols_{n_cols}.csv")


def multilineHeader(file: CSVFile, col=1, new_content="Line1\nLine2\nLine3"):
    """Adds line breaks inside one header cell."""
    pb.changeCell(file, row=1, col=col, new_content=new_content)
    _set_polluted_filename(file, f"file_multiline_header_col_{col}.csv")


def duplicateHeaderAsDataRow(file: CSVFile):
    """Duplicates the header row as the first data row."""
    header = _row_values(file, row=1)
    pb.addRows(file, cell_content=header, n_rows=1, position=1,
               col_count=len(header) or file.col_count, role="data")
    _set_polluted_filename(file, "file_duplicate_header_as_data.csv")


def extremelyLongFields(file: CSVFile, row=1, col=1, length=10000):
    """Replaces a cell with an extremely long random alphanumeric field."""
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    random.seed(constants.RAND_SEED)
    long_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    pb.changeCell(file, row=row, col=col, new_content=long_string)
    _set_polluted_filename(file, f"file_extremely_long_field_row_{row}_col_{col}_len_{length}.csv")


def addGroupSectionHeader(file: CSVFile, group_name="Region: North", position=-1):
    """Adds a bare section/group label row with content only in the first column."""
    if position < 0:
        position = _last_data_row(file) - 1
    row = [group_name] + [""] * max(file.col_count - 1, 0)
    pb.addRows(file, cell_content=row, n_rows=1, position=position,
               col_count=file.col_count, role="section_header")
    _set_polluted_filename(file, f"file_group_section_header_{position}.csv")


def addCommentToFile(file: CSVFile, comment="This is a comment."):
    """Adds a comment-like trailing field to the last row."""
    row = _last_data_row(file)
    pb.addCells(file, row=row, position=file.col_count, n_cells=1,
                content="# " + comment, role="comment")
    _set_polluted_filename(file, "file_trailing_comment.csv")


def mixedDelimiters(file: CSVFile, row=1, delimiters=None):
    """Uses different field delimiters within one row."""
    if delimiters is None:
        delimiters = [",", ";", "|"]
    root = file.xml.getroot()
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    fds = root.xpath(f"//row[{row}]/field_delimiter")
    for idx, fd in enumerate(fds):
        fd.text = delimiters[idx % len(delimiters)]
    encoded = "_".join(str(ord(d[0])) for d in delimiters if d)
    _set_polluted_filename(file, f"file_mixed_delimiters_row_{row}_{encoded}.csv")


def unescaped(file: CSVFile, row=1, col=1, content="This is a \"quote\" and a comma, and a newline\nin the same cell."):
    """Places quote, delimiter, and newline characters in a cell without adding escaping metadata."""
    pb.changeCell(file, row=row, col=col, new_content=content)
    _set_polluted_filename(file, f"file_unescaped_row_{row}_col_{col}.csv")


def doubleEscaping(file: CSVFile, row1=2, row2=3, col=1):
    """Mixes doubled-quote escaping and backslash escaping in the same column."""
    row_count = _safe_row_count(file)
    if row_count < row2:
        last = _row_values(file, row=row_count) or [""] * file.col_count
        pb.addRows(file, cell_content=last, n_rows=row2 - row_count, position=row_count,
                   col_count=file.col_count, role="data")
    pb.changeCell(file, row=row1, col=col, new_content='""hi""')
    pb.changeCell(file, row=row2, col=col, new_content='\\"hi\\"')
    _set_polluted_filename(file, f"file_double_escaping_col_{col}.csv")


def variableColumnCount(file: CSVFile):
    """Creates rows with fewer and more fields than the header."""
    row_count = _safe_row_count(file)
    if row_count < 3:
        last = _row_values(file, row=row_count) or [""] * file.col_count
        pb.addRows(file, cell_content=last, n_rows=3 - row_count, position=row_count,
                   col_count=file.col_count, role="data")
    if file.col_count > 1:
        pb.deleteCells(file, row=2, col=[file.col_count - 1])
    pb.addCells(file, row=3, position=file.col_count, n_cells=1,
                content="EXTRA_FIELD", role="data")
    _set_polluted_filename(file, "file_variable_column_count.csv")


def excelExportAutoformat(file: CSVFile):
    """Adds values commonly autoformatted by Excel: leading-zero IDs and date-like strings."""
    rows = [
        ["00123", "03/04/05", "1-2", "1E10"],
        ["00001", "2026-05-27", "12-13", "3.14E2"],
    ]
    for values in rows:
        padded = values[:file.col_count] + [""] * max(file.col_count - len(values), 0)
        pb.addRows(file, cell_content=padded, n_rows=1, position=_safe_row_count(file),
                   col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_excel_autoformat.csv")


def exelExportFormulas(file: CSVFile):
    """Adds spreadsheet formulas as literal CSV cell contents."""
    formulas = ["=SUM(A1:A10)", "=A2+B2", "=HYPERLINK(\"https://example.com\",\"link\")"]
    row = formulas[:file.col_count] + [""] * max(file.col_count - len(formulas), 0)
    pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
               col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_excel_formulas.csv")


def typeAmbiguity(file: CSVFile):
    """Adds rows containing ambiguous nulls, booleans, decimals, dates, and currencies."""
    rows = [
        ["NULL", "N/A", "NaN", ""],
        ["true", "false", "1", "0"],
        ["1.5", "1,5", "2026-05-27", "27.05.2026"],
        ["$20", "20 EUR", "unknown", "zero"],
    ]
    for values in rows:
        padded = values[:file.col_count] + [""] * max(file.col_count - len(values), 0)
        pb.addRows(file, cell_content=padded, n_rows=1, position=_safe_row_count(file),
                   col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_type_ambiguity.csv")


def superheader(file: CSVFile):
    """Adds a grouping row above the normal header."""
    groups = []
    for i in range(file.col_count):
        groups.append("Region" if i < max(1, file.col_count // 2) else "Metrics")
    pb.addRows(file, cell_content=groups, n_rows=1, position=0,
               col_count=file.col_count, role="superheader")
    _set_polluted_filename(file, "file_superheader.csv")


def embeddedFiles(file: CSVFile):
    """Embeds JSON-like file content inside a single cell."""
    payload = '{"name":"example.json","rows":[{"id":1,"value":"alpha"},{"id":2,"value":"beta"}]}'
    pb.changeCell(file, row=2 if _safe_row_count(file) >= 2 else 1, col=1, new_content=payload)
    _set_polluted_filename(file, "file_embedded_json_cell.csv")


def encoding(file: CSVFile, target_encoding: constants.Encoding):
    """Changes the declared file encoding.

    This wrapper is intentionally a little more permissive than
    changeEncoding(): tests and callers may pass plain strings such as
    "utf-8" instead of a constants.Encoding enum member.
    """
    target = target_encoding.value if type(target_encoding) == constants.Encoding else str(target_encoding)

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
    """Adds a UTF-8 BOM marker to the first header cell."""
    first = _row_values(file, row=1)[0] if _row_values(file, row=1) else ""
    pb.changeCell(file, row=1, col=1, new_content="\ufeff" + first)
    file.xml.getroot().attrib["bom"] = "utf-8"
    _set_polluted_filename(file, "file_utf8_bom.csv")


def weirdUnicode(file: CSVFile):
    """Adds mojibake and non-ASCII strings."""
    row = ["FranÃ§ois", "MÃ¼nchen", "SÃ£o Paulo", "â‚¬"]
    row = row[:file.col_count] + [""] * max(file.col_count - len(row), 0)
    pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
               col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_weird_unicode_mojibake.csv")


def invisibleCharacters(file: CSVFile):
    """Adds zero-width and non-breaking characters to cells."""
    values = ["zero\u200bwidth", "non\u00a0breaking", "left\u200emark", "word\ufeffjoiner"]
    row = values[:file.col_count] + [""] * max(file.col_count - len(values), 0)
    pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
               col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_invisible_characters.csv")


def collations(file: CSVFile):
    """Adds strings whose sort order differs by locale/collation."""
    for value in ["ä", "z", "å", "a", "Á", "á", "ß", "ss"]:
        row = [value] + [""] * max(file.col_count - 1, 0)
        pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
                   col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_collation_edge_cases.csv")


def mixedTypes(file: CSVFile):
    """Adds values with incompatible types in the same logical column."""
    for value in ["3.1415", "N/A", "unknown", "0", "zero", "$20"]:
        row = [value] + [""] * max(file.col_count - 1, 0)
        pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
                   col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_mixed_types.csv")


def mixedTimeformats(file: CSVFile):
    """Adds multiple date/time formats, with and without time zones."""
    values = ["05/27", "27th of May", "2026-05-27", "2026-05-27T10:30:00+02:00"]
    row = values[:file.col_count] + [""] * max(file.col_count - len(values), 0)
    pb.addRows(file, cell_content=row, n_rows=1, position=_safe_row_count(file),
               col_count=file.col_count, role="data")
    _set_polluted_filename(file, "file_mixed_time_formats.csv")
