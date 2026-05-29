from copy import deepcopy
from .CSVFile import CSVFile, create_cell
from lxml import etree
from lxml.builder import E


def insert_value_cell(file, cell, value):  # NEW
    """
    Safely inserts content into a CSV XML cell.

    CSVFile.create_cell stores the actual field payload in a child
    <value> element. Keep that structure when replacing cell content;
    otherwise XPath queries such as //cell/value will stop finding the
    changed values.
    """

    for child in list(cell):
        cell.remove(child)
    cell.text = None
    cell.append(E.value("" if value is None else str(value)))


def addCells(file: CSVFile, row, position, n_cells=1, content="", role="", table=0):
    """
    Inserts a cell in a row in the given position (with the corresponding delimiter)
    Position has to be a positive integer X it adds a delimiter at new position X (0-based)
    Role can either be one of data, header or spurious
    """
    assert position >= 0, "Position has to be a positive integer!"
    root = file.xml.getroot()
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)

    query = root.xpath(f"//table[{table + 1}]/row[{row}]")

    for r in query:
        cell_list = [x for x in r if x.tag == "cell"]
        pos = position(cell_list) if callable(position) else position

        if pos >= len(cell_list):
            row_pos = len(r) - 1
        elif pos > 0:
            tmp = cell_list[pos]
            row_pos = r.index(tmp) - 1
        else:
            row_pos = 0

        for i in range(n_cells):
            cell = create_cell(
                field_delimiter=file.field_delimiter,
                quotation_char=file.quotation_char,
                escape_char=file.escape_char,
                text=content or "",
                role=role,
            )
            delimiter = E.field_delimiter(file.field_delimiter)

            r.insert(row_pos, cell)
            (
                r.insert(row_pos, delimiter)
                if row_pos > 0
                else r.insert(row_pos + 1, delimiter)
            )


def addRows(
    file: CSVFile,
    cell_content="",
    n_rows=0,
    position=0,
    col_count=None,
    role="",
    table=0,
):
    """
    Inserts a row in the table with user-defined padding content.
    Position has to be a positive integer. The polluter will insert a new row in the given position (0-indexing).
    If position is greater than the total number of rows, it will be appended at the end.
    If cell content is a list, it has to have the same dimension of col_count (or file.col_count if the parameter is None)
    Otherwise if it is a string, then it will be repeated across all cells.
    Role is the role of the cells of the row, either a list of strings or a string (same for every cell)
    """
    assert position >= 0, "Position has to be a positive integer!"
    root = file.xml.getroot().xpath("//table")[table]
    pos = position(root) if callable(position) else position
    if col_count is None:
        col_count = file.col_count

    if pos >= len(root):
        pos = len(root)

    for j in range(n_rows):
        row_role = max(set(role), key=role.count) if type(role) == list else role
        row = etree.Element("row", role=row_role)
        for i in range(col_count):
            rl = role[i] if type(role) == list else role
            content = cell_content[i] if type(cell_content) == list else cell_content
            cell = create_cell(
                field_delimiter=file.field_delimiter,
                quotation_char=file.quotation_char,
                escape_char=file.escape_char,
                text=content or "",
                role=rl,
            )
            row.insert(len(row), cell)
            if i < col_count - 1:
                delimiter = E.field_delimiter(file.field_delimiter)
                row.insert(len(row), delimiter)

        row_delimiter = E.record_delimiter(file.record_delimiter)
        row.insert(len(row), row_delimiter)
        root.insert(pos, row)


def addColumns(
    file: CSVFile,
    position,
    n_cols: int,
    col_names: list,
    cell_content="PAD",
    role="",
    table=0,
):
    root = file.xml.getroot()

    query = root.xpath(f"//table[{table + 1}]/row")

    reversed_col_names = list(reversed(col_names))
    for idx, r in enumerate(query):
        cell_list = [x for x in r if x.tag == "cell"]
        pos = position(cell_list) if callable(position) else position

        if pos >= len(cell_list):
            row_pos = len(r) - 1
        elif pos > 0:
            tmp = cell_list[pos]
            row_pos = r.index(tmp) - 1
        else:
            row_pos = 0

        for i in range(n_cols):
            content = (
                cell_content[idx - 1] if type(cell_content) == list else cell_content
            )
            content = content if idx >= 1 else reversed_col_names[i]
            rl = role[idx] if type(role) == list else role

            cell = create_cell(
                field_delimiter=file.field_delimiter,
                quotation_char=file.quotation_char,
                escape_char=file.escape_char,
                text=content or "",
                role=rl,
            )
            delimiter = E.field_delimiter(file.field_delimiter)

            r.insert(row_pos, cell)
            (
                r.insert(row_pos, delimiter)
                if row_pos > 0
                else r.insert(row_pos + 1, delimiter)
            )


def changeCell(file: CSVFile, row: int, col: int, new_content, table=0):
    root = file.xml.getroot()
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    if type(col) == int and col < 0:
        col = "last()-" + str(col + 1)

    if col == "*":
        query = root.xpath(f"//table[{table + 1}]/row[{row}]//cell")
    else:
        query = root.xpath(f"//table[{table + 1}]/row[{row}]/cell[{col}]")

    for c in query:
        [c.remove(child) for child in c]
        insert_value_cell(file, c, new_content)


def deleteCells(file: CSVFile, row: int, col, table=0):
    root = file.xml.getroot()

    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    if type(col) == int and col < 0:
        col = "last()-" + str(col + 1)

    if col == "*":
        query = root.xpath(f"//table[{table + 1}]/row[{row}]/cell")
    elif type(col) == list:
        query = []
        for c in col:
            query += root.xpath(f"//table[{table + 1}]/row[{row}]/cell[{c + 1}]")
            query += root.xpath(f"//table[{table + 1}]/row[{row}]/field_delimiter[{c}]")
    else:
        query = root.xpath(f"//table[{table + 1}]/row[{row}]/cell[{col}]")

    for c in query:
        c.getparent().remove(c)


def deleteRows(file: CSVFile, rows_to_delete: list, table=0):
    root = file.xml.getroot()

    query = []
    for row in rows_to_delete:
        query += root.xpath(
            f"//table[{table + 1}]/row[{row + 1}]"
        )  # xquery is 1-indexed

    for row in query:
        row.getparent().remove(row)


def getRow(file: CSVFile, row: int, table: int = 0, detach=False):
    """
    Returns a copy of a row element.

    row is 0-indexed.
    If detach=True, removes the row from the table.
    """

    root = file.xml.getroot()
    query = root.xpath(f"//table[{table + 1}]/row[{row + 1}]")

    if not query:
        raise IndexError(f"Row {row} not found")

    row_node = query[0]
    row_copy = deepcopy(row_node)
    if detach:
        row_node.getparent().remove(row_node)

    return row_copy


def insertRow(file: CSVFile, row_node, position: int, table: int = 0):
    """
    Inserts an existing row node at a position.
    Position is 0-indexed.
    """

    root = file.xml.getroot().xpath("//table")[table]

    if position >= len(root):
        position = len(root)

    root.insert(position, row_node)


def moveRow(file: CSVFile, src: int, dst: int, table: int = 0):
    insertRow(file, getRow(file, src, table, detach=True), dst, table)


def deleteColumns(file, col: list, table=0):
    root = file.xml.getroot()

    if col == "*":
        query = root.xpath(f"//table[{table + 1}]/row[*]")
    else:
        query = []
        for c in col:
            query += root.xpath(f"//table[{table + 1}]/row[*]/cell[{c + 1}]")
            query += root.xpath(
                f"//table[{table + 1}]/row[*]/field_delimiter[{c}]"
            )  # magic trick
    for el in query:
        el.getparent().remove(el)


def changeDelimiter(file: CSVFile, row=1, col=1, new_delimiter=";", table=0):
    """
    Row indexing is 1-based! Follows xquery
    """
    if type(row) == int and row < 0:
        row = "last()-" + str(row + 1)
    if type(col) == int and col < 0:
        col = "last()-" + str(col + 1)

    root = file.xml.getroot()

    query = root.xpath(f"//table[{table + 1}]/row[{row}]/field_delimiter[{col}]")
    for r in query:
        r.text = new_delimiter


def changeColumnDelimiters(file: CSVFile, col=1, new_delimiter=";", table=0):
    """
    Col indexing is 1-based! Follows xquery
    """
    if type(col) == int and col < 0:
        col = "last()-" + str(col + 1)

    root = file.xml.getroot()
    query = (
        root.xpath(f"//table[{table + 1}]/row/field_delimiter[{col}]")
        if col != "*"
        else root.xpath(f"table[{table + 1}]/row/field_delimiter")
    )
    for r in query:
        r.text = new_delimiter


def get_cell_value(cell) -> str:
    """
    Extracts the textual payload from a CSV XML cell.
    Expected structure:

    <cell>
        <value>...</value>
    </cell>
    """
    value_el = cell.find("value")
    return value_el.text if value_el is not None else None


def findMatchingCells(file: CSVFile, matching, table=0) -> set[tuple[int, int, str]]:
    """
    Finds all cells matching a predicate. Returns set of tuples of
    (row_idx, col_idx, value) for all matching cells.
    """

    root = file.xml.getroot()
    rows = root.xpath(f"//table[{table + 1}]/row")

    matches = set()
    for row_idx, row in enumerate(rows):
        cells = [x for x in row if x.tag == "cell"]
        for col_idx, cell in enumerate(cells):
            value = get_cell_value(cell)
            if matching(value, row_idx, col_idx):
                matches.add((row_idx, col_idx, value))

    return matches


def getRowCells(file: CSVFile, row: int, table: int = 0) -> list[any]:
    """
    Returns all cells from a row.
    """

    root = file.xml.getroot()
    query = root.xpath(f"//table[{table + 1}]/row[{row + 1}]")

    if not query:
        raise IndexError(f"Row {row} not found")

    row_node = query[0]
    return [cell for cell in row_node if cell.tag == "cell"]
