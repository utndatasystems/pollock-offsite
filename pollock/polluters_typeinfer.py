"""
Type-inference & sniffer-trap polluter engine.

Targets parsers that infer column types from a sample window:
  * pandas (delimiter=None auto-detection)
  * duckdbauto (auto_detect=True, with restricted auto_type_candidates)

duckdbparse declares everything VARCHAR up front and pycsv only sniffs
dialect, so they're largely immune. The attacks here lean on:

  - Late-row anomalies after a clean prefix (sample-window evasion)
  - Ambiguous numeric-vs-string content (currency, thousands, EU decimals)
  - Pseudo-types (booleans in numeric col, dates as numbers, etc.)
  - Locale/edge-value confusion (NaN, Inf, leading zeros, hex/oct)
  - Null-flavor proliferation
  - Quoted-content shaped like a CSV fragment

All filenames begin with `typeinfer_`. All entries mutate the XML so the
clean output reflects the intended cell content (the parser must preserve
the values we wrote).
"""
from __future__ import annotations

from lxml import etree
from lxml.builder import E

from . import polluters_base as pb
from .CSVFile import CSVFile, create_cell


# Source columns (1-indexed for xpath cell[N]):
#   1=DATE 2=TIME 3=Qty 4=PRODUCTID 5=Price 6=ProductType
#   7=ProductDescription 8=URL 9=Comments
# Data rows: indices 2..84 (83 rows). Row 1 is header.

QTY_COL = 3
PRICE_COL = 5
DATE_COL = 1
TIME_COL = 2
PRODUCTID_COL = 4
URL_COL = 8
COMMENTS_COL = 9


def _set_cell(file: CSVFile, row: int, col: int, new_text: str, should_quote: bool = True) -> None:
    """Replace the value of a cell at (row, col) with new_text.

    pb.changeCell in polluters_base is broken (calls undefined insert_value_cell),
    so we do our own. Rebuilds the cell using create_cell to preserve quote/escape
    semantics. should_quote=True keeps the quote_all=True default behaviour."""
    root = file.xml.getroot()
    query = root.xpath(f"//table[1]/row[{row}]/cell[{col}]")
    for c in query:
        # Find this cell's parent and its index, then replace it.
        parent = c.getparent()
        idx = parent.index(c)
        new_c = create_cell(
            field_delimiter=file.field_delimiter,
            quotation_char=file.quotation_char,
            escape_char=file.escape_char,
            text=new_text,
            should_quote=should_quote,
            role=c.get("role"),
        )
        parent.remove(c)
        parent.insert(idx, new_c)


# Aliasing pb.changeCell to the local helper so the rest of the module
# can use a familiar name without rewriting every call site.
def _change_cell(file: CSVFile, row: int, col: int, new_content: str) -> None:
    _set_cell(file, row, col, new_content)


# Patch into pb namespace so existing references work transparently.
pb.changeCell = _change_cell


# ---------------------------------------------------------------------------
# 1. Sample-window evasion: clean prefix, then garbage at the very end.
# ---------------------------------------------------------------------------

def qty_late_string_anomaly(file: CSVFile):
    """Rows 2..82 keep clean small ints in Qty; row 83 has 'N/A'.
    Sniffer sees ~80 small ints, commits to BIGINT, then chokes on the string
    or silently coerces. duckdb's default sample is 20480 rows so it sees this,
    but the *type* commitment differs from string handling."""
    pb.changeCell(file, row=83, col=QTY_COL, new_content="N/A")


def qty_late_overflow(file: CSVFile):
    """All Qty look like clean small ints, except row 84 which overflows BIGINT."""
    pb.changeCell(file, row=84, col=QTY_COL, new_content="99999999999999999999")


def qty_late_inf(file: CSVFile):
    """Late-row 'inf' value in Qty after clean integer prefix."""
    pb.changeCell(file, row=83, col=QTY_COL, new_content="inf")
    pb.changeCell(file, row=84, col=QTY_COL, new_content="-inf")


def qty_late_huge_float(file: CSVFile):
    """Late-row 1e308 in Qty: forces FLOAT/DOUBLE upgrade after BIGINT commit."""
    pb.changeCell(file, row=84, col=QTY_COL, new_content="1e308")


def qty_late_currency(file: CSVFile):
    """All Qty clean; row 84 becomes '$2.00' — currency string after numeric prefix."""
    pb.changeCell(file, row=84, col=QTY_COL, new_content="$2.00")


# ---------------------------------------------------------------------------
# 2. Currency / locale / decimal-separator confusion
# ---------------------------------------------------------------------------

def qty_all_currency(file: CSVFile):
    """Every Qty cell becomes '$X.00'. Forces currency parsing or VARCHAR fallback."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for v in cells:
        if v.text is not None:
            v.text = "$" + v.text + ".00"


def price_european_decimal(file: CSVFile):
    """Price column: $74.69 -> 74,69 — embedded comma in a comma-delimited file
    causes column-count drift unless quoted. The parser keeps the quotes from
    quote_all=True; type sniffer sees 'XX,YY' which is neither int nor float
    in en_US locale but valid float in de_DE."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[5]/value")
    for v in cells:
        if v.text is not None:
            v.text = v.text.replace("$", "").replace(".", ",")


def qty_thousands_separator(file: CSVFile):
    """Qty values like '1,000', '2,500' — embedded thousands separator in
    comma-delimited file. With quote_all=True they survive, but type detection
    sees them as strings (not ints)."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="1,000")
    pb.changeCell(file, row=20, col=QTY_COL, new_content="2,500")
    pb.changeCell(file, row=40, col=QTY_COL, new_content="10,000")
    pb.changeCell(file, row=60, col=QTY_COL, new_content="1,234,567")


def price_thousands_currency(file: CSVFile):
    """Price column gets thousands separator with currency: '$1,234.56'."""
    pb.changeCell(file, row=2, col=PRICE_COL, new_content="$1,234.56")
    pb.changeCell(file, row=10, col=PRICE_COL, new_content="$12,345.00")
    pb.changeCell(file, row=20, col=PRICE_COL, new_content="$1,000,000.99")


# ---------------------------------------------------------------------------
# 3. Pseudo-booleans / pseudo-dates / pseudo-types
# ---------------------------------------------------------------------------

def qty_pseudo_booleans(file: CSVFile):
    """Mix Y/N, T/F, Yes/No, true/TRUE in Qty column."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="Y")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="N")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="T")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="F")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="Yes")
    pb.changeCell(file, row=7, col=QTY_COL, new_content="No")
    pb.changeCell(file, row=8, col=QTY_COL, new_content="true")
    pb.changeCell(file, row=9, col=QTY_COL, new_content="TRUE")
    pb.changeCell(file, row=10, col=QTY_COL, new_content="False")


def comments_pseudo_dates(file: CSVFile):
    """Comments column normally empty — fill with strings that look like dates."""
    pb.changeCell(file, row=2, col=COMMENTS_COL, new_content="01/02/03")
    pb.changeCell(file, row=3, col=COMMENTS_COL, new_content="2024-13-45")
    pb.changeCell(file, row=4, col=COMMENTS_COL, new_content="45000")
    pb.changeCell(file, row=5, col=COMMENTS_COL, new_content="Jan 5, 2024")
    pb.changeCell(file, row=6, col=COMMENTS_COL, new_content="2024-02-30")


def date_format_chaos(file: CSVFile):
    """Mix DD/MM/YYYY, ISO YYYY-MM-DD, MM/DD/YY in DATE column."""
    pb.changeCell(file, row=2, col=DATE_COL, new_content="2018-01-28")
    pb.changeCell(file, row=3, col=DATE_COL, new_content="01/28/18")
    pb.changeCell(file, row=4, col=DATE_COL, new_content="28-Jan-2018")
    pb.changeCell(file, row=5, col=DATE_COL, new_content="Jan 28, 2018")
    pb.changeCell(file, row=10, col=DATE_COL, new_content="28.01.2018")


def date_excel_serials(file: CSVFile):
    """DATE column values become Excel serials — perfectly valid integers
    that Excel-aware sniffers might interpret as dates, others as ints."""
    pb.changeCell(file, row=2, col=DATE_COL, new_content="43128")
    pb.changeCell(file, row=3, col=DATE_COL, new_content="43129")
    pb.changeCell(file, row=4, col=DATE_COL, new_content="43130")
    pb.changeCell(file, row=5, col=DATE_COL, new_content="43131")


def time_locale_ambiguity(file: CSVFile):
    """Time values that should not parse as times in any sane locale."""
    pb.changeCell(file, row=2, col=TIME_COL, new_content="13:00:00 PM")
    pb.changeCell(file, row=3, col=TIME_COL, new_content="25:99:99")
    pb.changeCell(file, row=4, col=TIME_COL, new_content="12:00 AM")
    pb.changeCell(file, row=5, col=TIME_COL, new_content="0:00:00.0000000")
    pb.changeCell(file, row=6, col=TIME_COL, new_content="24:00:00")


# ---------------------------------------------------------------------------
# 4. Numeric edge values
# ---------------------------------------------------------------------------

def qty_numeric_edges(file: CSVFile):
    """Edge numeric values across Qty: +0, -0, NaN, Inf, leading zeros, signed."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="+0")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="-0")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="Infinity")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="-Infinity")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="NaN")
    pb.changeCell(file, row=7, col=QTY_COL, new_content="007")
    pb.changeCell(file, row=8, col=QTY_COL, new_content="0042")
    pb.changeCell(file, row=9, col=QTY_COL, new_content="+5")


def qty_hex_octal(file: CSVFile):
    """Programmer-style numeric formats in Qty: 0x1F (hex), 0o17 (octal),
    1_000 (Python underscored), 2^64."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="0x1F")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="0o17")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="1_000")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="0b101010")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="2^64")


def qty_denormal_floats(file: CSVFile):
    """Tiny denormal floats and underflow: 4.9e-324, 1e-400 (underflow), -0.0."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="4.9e-324")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="1e-400")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="-0.0")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="1e9999")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="2.2250738585072014e-308")


# ---------------------------------------------------------------------------
# 5. Type-confusable cells in non-numeric columns
# ---------------------------------------------------------------------------

def productid_pseudo_scientific(file: CSVFile):
    """PRODUCTID values that look like scientific notation: MG-1e10, etc."""
    pb.changeCell(file, row=2, col=PRODUCTID_COL, new_content="1e10")
    pb.changeCell(file, row=3, col=PRODUCTID_COL, new_content="2E5")
    pb.changeCell(file, row=4, col=PRODUCTID_COL, new_content="3.14e2")
    pb.changeCell(file, row=5, col=PRODUCTID_COL, new_content="1E308")


def url_as_booleans(file: CSVFile):
    """URL column gets booleans/numbers — was always 'https://...' for whole sample."""
    pb.changeCell(file, row=2, col=URL_COL, new_content="True")
    pb.changeCell(file, row=3, col=URL_COL, new_content="False")
    pb.changeCell(file, row=4, col=URL_COL, new_content="1")
    pb.changeCell(file, row=5, col=URL_COL, new_content="0")
    pb.changeCell(file, row=6, col=URL_COL, new_content="NULL")


def url_as_dates(file: CSVFile):
    """URL column gets date-shaped strings — type confusion for sniffer."""
    pb.changeCell(file, row=2, col=URL_COL, new_content="2024-01-01")
    pb.changeCell(file, row=3, col=URL_COL, new_content="2024-02-15")
    pb.changeCell(file, row=4, col=URL_COL, new_content="1234567890")


# ---------------------------------------------------------------------------
# 6. Null-flavor proliferation
# ---------------------------------------------------------------------------

def qty_null_flavors(file: CSVFile):
    """Different null tokens scattered in Qty column to trigger different
    NA-detection paths in pandas vs duckdb."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="NULL")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="null")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="None")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="NA")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="n/a")
    pb.changeCell(file, row=7, col=QTY_COL, new_content="#N/A")
    pb.changeCell(file, row=8, col=QTY_COL, new_content="-")
    pb.changeCell(file, row=9, col=QTY_COL, new_content="--")
    pb.changeCell(file, row=10, col=QTY_COL, new_content="?")


def qty_whitespace_padded(file: CSVFile):
    """NBSP, tab, regular space padding around Qty integers."""
    # Need utf-8 for NBSP / line separator chars.
    file.encoding = "utf-8"
    file.xml.getroot().attrib["encoding"] = "utf-8"
    pb.changeCell(file, row=2, col=QTY_COL, new_content="\u00a05\u00a0")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="\t42")
    pb.changeCell(file, row=4, col=QTY_COL, new_content=" 7 ")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="\u20283")


# ---------------------------------------------------------------------------
# 7. Mixed numeric formats (comprehensive)
# ---------------------------------------------------------------------------

def qty_mixed_numeric_formats(file: CSVFile):
    """Lots of numeric variants — pandas/duckdb pick one type, which makes
    the others string-ify or coerce."""
    pb.changeCell(file, row=2, col=QTY_COL, new_content="1.5")
    pb.changeCell(file, row=3, col=QTY_COL, new_content="1,5")
    pb.changeCell(file, row=4, col=QTY_COL, new_content="1.5e3")
    pb.changeCell(file, row=5, col=QTY_COL, new_content="0x1F")
    pb.changeCell(file, row=6, col=QTY_COL, new_content="01F")
    pb.changeCell(file, row=7, col=QTY_COL, new_content="1_000")
    pb.changeCell(file, row=8, col=QTY_COL, new_content="1.0E+10")
    pb.changeCell(file, row=9, col=QTY_COL, new_content=".5")
    pb.changeCell(file, row=10, col=QTY_COL, new_content="5.")


# ---------------------------------------------------------------------------
# 8. Quoted content shaped like a CSV fragment
# ---------------------------------------------------------------------------

def productid_csv_fragment(file: CSVFile):
    """PRODUCTID = 'a,b,c' — quoted but parser may misinterpret as 3 cells."""
    pb.changeCell(file, row=2, col=PRODUCTID_COL, new_content="a,b,c")
    pb.changeCell(file, row=3, col=PRODUCTID_COL, new_content="x,y")
    pb.changeCell(file, row=4, col=PRODUCTID_COL, new_content="1,2,3,4")


# ---------------------------------------------------------------------------
# 9. Long uniform run with one anomaly (sample window stable)
# ---------------------------------------------------------------------------

def qty_uniform_with_word_anomaly(file: CSVFile):
    """Qty all '2' (uniform), then one row with 'seventy-six' written out."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for v in cells:
        v.text = "2"
    pb.changeCell(file, row=70, col=QTY_COL, new_content="seventy-six")


def qty_uniform_with_late_negative(file: CSVFile):
    """Qty all '2' until the very last row which goes negative."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for v in cells:
        v.text = "2"
    pb.changeCell(file, row=84, col=QTY_COL, new_content="-9223372036854775809")


# ---------------------------------------------------------------------------
# 10. Whitespace-only column
# ---------------------------------------------------------------------------

def url_whitespace_only(file: CSVFile):
    """URL column entirely spaces — will normalize_cell strip these?"""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[8]/value")
    for v in cells:
        v.text = "    "


# ---------------------------------------------------------------------------
# 11. Empty cells via NA tokens in numeric column
# ---------------------------------------------------------------------------

def qty_empty_cells_scattered(file: CSVFile):
    """Empty Qty cells scattered — pandas turns into NaN, duckdb varies."""
    for row in [3, 7, 13, 19, 23, 29, 41, 53, 67, 79]:
        pb.changeCell(file, row=row, col=QTY_COL, new_content="")


# ---------------------------------------------------------------------------
# 12. Very large pseudo-numeric URLs (timestamp-like)
# ---------------------------------------------------------------------------

def url_unix_timestamps(file: CSVFile):
    """URL column with Unix timestamps — looks like int but should stay string."""
    for i, row in enumerate(range(2, 85)):
        ts = 1700000000 + i * 86400
        pb.changeCell(file, row=row, col=URL_COL, new_content=str(ts))


# ---------------------------------------------------------------------------
# 13. ProductDescription with embedded numerics
# ---------------------------------------------------------------------------

def comments_excel_serials(file: CSVFile):
    """Comments with Excel serial numbers — may be type-confused as int."""
    serials = ["44927", "44928", "44929", "44930", "44931", "44932", "44933", "44934"]
    for i, s in enumerate(serials):
        pb.changeCell(file, row=2 + i, col=COMMENTS_COL, new_content=s)


# ---------------------------------------------------------------------------
# 14. Boolean-valued QTY mimicking 0/1 range (sniffer sees BOOL)
# ---------------------------------------------------------------------------

def qty_pure_01_then_anomaly(file: CSVFile):
    """First 80 rows of Qty are 0/1 only — looks like BOOL — last rows have ints."""
    root = file.xml.getroot()
    rows = root.xpath("//row[@role='data']")
    for i, r in enumerate(rows):
        cell_value = r.xpath("cell[3]/value")[0]
        if i < 78:
            cell_value.text = "0" if i % 2 == 0 else "1"
        else:
            # Late anomaly: a real integer that breaks the boolean illusion
            cell_value.text = str(100 + i)


# ---------------------------------------------------------------------------
# 15. Late negative leading zero plus signed +
# ---------------------------------------------------------------------------

def qty_signed_plus_leading_zero(file: CSVFile):
    """Mix of +007, -007, 0042 in late rows after clean prefix."""
    pb.changeCell(file, row=80, col=QTY_COL, new_content="+007")
    pb.changeCell(file, row=81, col=QTY_COL, new_content="-007")
    pb.changeCell(file, row=82, col=QTY_COL, new_content="0042")
    pb.changeCell(file, row=83, col=QTY_COL, new_content="+0042")


# ---------------------------------------------------------------------------
# 16. Currency Price -> all weird formats
# ---------------------------------------------------------------------------

def price_currency_chaos(file: CSVFile):
    """Mix of currency formats: '$74.69', 'USD 74.69', '74.69 USD', '€74,69'."""
    # Need utf-8 for euro / pound symbols.
    file.encoding = "utf-8"
    file.xml.getroot().attrib["encoding"] = "utf-8"
    pb.changeCell(file, row=2, col=PRICE_COL, new_content="USD 74.69")
    pb.changeCell(file, row=3, col=PRICE_COL, new_content="74.69 USD")
    pb.changeCell(file, row=4, col=PRICE_COL, new_content="\u20ac74,69")
    pb.changeCell(file, row=5, col=PRICE_COL, new_content="\u00a374.69")
    pb.changeCell(file, row=6, col=PRICE_COL, new_content="74.69$")
    pb.changeCell(file, row=7, col=PRICE_COL, new_content="$ 74.69")


# ---------------------------------------------------------------------------
# 17. Productid scientific lookalike
# ---------------------------------------------------------------------------

def productid_only_digits(file: CSVFile):
    """All productids become pure ints — sniffer picks BIGINT, then the
    'MG-' prefix that came back in row 84 will be string and break columns."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[4]/value")
    for i, v in enumerate(cells):
        if i < len(cells) - 1:
            v.text = str(1000000 + i)
        # last row keeps MG- prefix


# ---------------------------------------------------------------------------
# 18. ProductID scientific notation that completely overlaps with a real product code
# ---------------------------------------------------------------------------

def productid_e_notation(file: CSVFile):
    """All product IDs become scientific-notation lookalikes via E format."""
    pb.changeCell(file, row=2, col=PRODUCTID_COL, new_content="1E10")
    pb.changeCell(file, row=3, col=PRODUCTID_COL, new_content="2E5")
    pb.changeCell(file, row=4, col=PRODUCTID_COL, new_content="-3E2")
    pb.changeCell(file, row=5, col=PRODUCTID_COL, new_content="0E0")
    pb.changeCell(file, row=6, col=PRODUCTID_COL, new_content="1.5E3")
    pb.changeCell(file, row=7, col=PRODUCTID_COL, new_content="9.99E308")


# ---------------------------------------------------------------------------
# 19. Time anomaly — 24h-vs-12h chaos
# ---------------------------------------------------------------------------

def time_12h_24h_mix(file: CSVFile):
    """TIME column gets a mix of HH:MM (24h), HH:MM AM/PM, HH:MM:SS."""
    pb.changeCell(file, row=2, col=TIME_COL, new_content="00:00 AM")
    pb.changeCell(file, row=3, col=TIME_COL, new_content="12:00 PM")
    pb.changeCell(file, row=4, col=TIME_COL, new_content="13:00:00")
    pb.changeCell(file, row=5, col=TIME_COL, new_content="1:00 pm")
    pb.changeCell(file, row=6, col=TIME_COL, new_content="14:30:45.123")


# ---------------------------------------------------------------------------
# 20. Mixed dates: 2-digit + 4-digit years
# ---------------------------------------------------------------------------

def date_2digit_4digit(file: CSVFile):
    """DATE column with two-digit and four-digit years mixed."""
    pb.changeCell(file, row=2, col=DATE_COL, new_content="28/01/18")
    pb.changeCell(file, row=3, col=DATE_COL, new_content="28/01/2018")
    pb.changeCell(file, row=4, col=DATE_COL, new_content="28/1/18")
    pb.changeCell(file, row=5, col=DATE_COL, new_content="2018/01/28")
    pb.changeCell(file, row=6, col=DATE_COL, new_content="28-01-2018")


# ---------------------------------------------------------------------------
# 21. Boolean look-alikes in BOOLEAN auto_type_candidate's path
# ---------------------------------------------------------------------------

def qty_all_booleans(file: CSVFile):
    """Every Qty becomes 0 or 1 — duckdb likely picks BOOLEAN, pandas picks
    int, behaviour diverges."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for i, v in enumerate(cells):
        v.text = "0" if i % 2 == 0 else "1"


# ---------------------------------------------------------------------------
# 22. Late row with BOOLEAN-looking string after BIGINT prefix
# ---------------------------------------------------------------------------

def qty_late_boolean(file: CSVFile):
    """Clean ints, then 'true' / 'false' at the end."""
    pb.changeCell(file, row=83, col=QTY_COL, new_content="true")
    pb.changeCell(file, row=84, col=QTY_COL, new_content="false")


# ---------------------------------------------------------------------------
# 23. URL with bool/int that then transitions back to https — mixed type
# ---------------------------------------------------------------------------

def url_mixed_types_drift(file: CSVFile):
    """First 75 rows: URLs as integers. Last 8: real https. Sniffer commits to int."""
    root = file.xml.getroot()
    rows = root.xpath("//row[@role='data']")
    for i, r in enumerate(rows):
        cv = r.xpath("cell[8]/value")[0]
        if i < 75:
            cv.text = str(1000 + i)


# ---------------------------------------------------------------------------
# 24. Repeating very long string values (push past sample window)
# ---------------------------------------------------------------------------

def qty_long_zeros_then_text(file: CSVFile):
    """Qty all '0000000' (7 leading zeros), then late row 'pending'."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for v in cells:
        v.text = "0000000"
    pb.changeCell(file, row=84, col=QTY_COL, new_content="pending")


# ---------------------------------------------------------------------------
# 25. ISO 8601 timestamps in DATE column
# ---------------------------------------------------------------------------

def date_iso_timestamps(file: CSVFile):
    """DATE column with full ISO 8601 timestamps including T and Z."""
    pb.changeCell(file, row=2, col=DATE_COL, new_content="2018-01-28T00:00:00Z")
    pb.changeCell(file, row=3, col=DATE_COL, new_content="2018-01-29T00:15:30+01:00")
    pb.changeCell(file, row=4, col=DATE_COL, new_content="2018-01-30 00:30:00")
    pb.changeCell(file, row=5, col=DATE_COL, new_content="20180128")
    pb.changeCell(file, row=6, col=DATE_COL, new_content="2018W04")


# ---------------------------------------------------------------------------
# Round 2: sharpened — multi-column / column-shifting / whole-column attacks
# ---------------------------------------------------------------------------


def _set_unquoted_value(file: CSVFile, row: int, col: int, new_text: str) -> None:
    """Replace a cell's value WITHOUT wrapping in quotes, even if the new
    text contains the field delimiter. Used for column-shift attacks: the
    polluted file omits quotes so the parser sees N+1 cells, but the clean
    file keeps the original cell's intent."""
    root = file.xml.getroot()
    cells = root.xpath(f"//table[1]/row[{row}]/cell[{col}]")
    for c in cells:
        # Wipe children and rebuild as a no-quote cell with single value.
        for child in list(c):
            c.remove(child)
        c.append(E.value(new_text))


# ---------------------------------------------------------------------------
# 26. Multi-column late-row anomaly: kill 3 columns at once
# ---------------------------------------------------------------------------

def multi_column_late_anomaly(file: CSVFile):
    """Late row with bad values in DATE, Qty, and Price simultaneously.
    Forces multiple column type inferences to fail in one shot."""
    pb.changeCell(file, row=84, col=DATE_COL, new_content="not-a-date")
    pb.changeCell(file, row=84, col=QTY_COL, new_content="9999999999999999999999")
    pb.changeCell(file, row=84, col=PRICE_COL, new_content="FREE")
    pb.changeCell(file, row=84, col=TIME_COL, new_content="99:99:99")


# ---------------------------------------------------------------------------
# 27. Whole-column type flip: Qty all become floats with .0 suffix on every value
#     (forces string-comparison mismatch even though logically equivalent)
# ---------------------------------------------------------------------------

def qty_all_with_explicit_float(file: CSVFile):
    """Every Qty value gets '.5' decimal suffix — pure float column. After
    auto-inference this stays float, but the source had ints. Result: ALL
    83 Qty cells are mismatched on string comparison."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[3]/value")
    for v in cells:
        if v.text is not None:
            v.text = v.text + ".5"


# ---------------------------------------------------------------------------
# 28. Massive column shift: unquoted comma in EVERY Qty cell
# ---------------------------------------------------------------------------

def qty_all_unquoted_thousands(file: CSVFile):
    """Every Qty value becomes a thousands-separated unquoted '1,000' style.
    Each row gets +1 cell from the parser's POV, scrambling 6 columns to the
    right of Qty across all 83 rows."""
    root = file.xml.getroot()
    rows = root.xpath("//row[@role='data']")
    for r in rows:
        cells = r.xpath("cell")
        if len(cells) >= 3:
            cell = cells[2]  # 0-indexed: Qty is cell index 2
            for child in list(cell):
                cell.remove(child)
            cell.append(E.value("1,000"))


# ---------------------------------------------------------------------------
# 29. Multi-column shift: Price gets unquoted EU decimal across ALL rows
# ---------------------------------------------------------------------------

def price_all_unquoted_eu(file: CSVFile):
    """Every Price cell gets a value like '74,69' (unquoted comma)
    so all 83 rows get column-shifted by 1. Massive cell mismatch."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[5]")
    for c in cells:
        for child in list(c):
            c.remove(child)
        c.append(E.value("74,69"))


# ---------------------------------------------------------------------------
# 30. Late-row column shift: insert N late rows (rows 80-84) with 1 extra cell
# ---------------------------------------------------------------------------

def late_rows_extra_cell(file: CSVFile):
    """Last 5 rows have 1 extra unquoted-comma cell each. Sniffer expects
    9 columns based on header + 78 rows; last 5 rows have 10 — column shift
    only at the end."""
    root = file.xml.getroot()
    for row in [80, 81, 82, 83, 84]:
        cells = root.xpath(f"//row[{row}]/cell[3]")
        for c in cells:
            for child in list(c):
                c.remove(child)
            c.append(E.value("1,234"))


# ---------------------------------------------------------------------------
# 31. Combine: late huge float + currency turnover (kills duckdbauto twice)
# ---------------------------------------------------------------------------

def qty_late_huge_and_strings(file: CSVFile):
    """Late row: 1e308. Plus rows 80-83 have 'PENDING' strings.
    duckdbauto's BIGINT/DOUBLE candidates can't handle this combination."""
    pb.changeCell(file, row=80, col=QTY_COL, new_content="PENDING")
    pb.changeCell(file, row=81, col=QTY_COL, new_content="REVIEW")
    pb.changeCell(file, row=82, col=QTY_COL, new_content="HOLD")
    pb.changeCell(file, row=83, col=QTY_COL, new_content="N/A")
    pb.changeCell(file, row=84, col=QTY_COL, new_content="1e308")


# ---------------------------------------------------------------------------
# 32. Aggressive ALL-Qty type-confusing strings
# ---------------------------------------------------------------------------

def qty_all_pseudo_bool_strings(file: CSVFile):
    """All Qty become 'Y'/'N' (alternating). Forces parsers down a Boolean-
    or-string path. Source had ints — every cell mismatches."""
    root = file.xml.getroot()
    rows = root.xpath("//row[@role='data']")
    for i, r in enumerate(rows):
        cv = r.xpath("cell[3]/value")
        if cv:
            cv[0].text = "Y" if i % 2 == 0 else "N"


# ---------------------------------------------------------------------------
# 33. Date column entirely Excel serial integers (sniffer sees BIGINT)
# ---------------------------------------------------------------------------

def date_all_excel_serials(file: CSVFile):
    """Every DATE becomes an Excel serial number. duckdb auto picks BIGINT
    based on shape; original was DD/MM/YYYY string. Whole column flips type."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[1]/value")
    for i, v in enumerate(cells):
        v.text = str(43128 + i)


# ---------------------------------------------------------------------------
# 34. Price column: $ removed from EVERY row. Whole column type flips int->float
# ---------------------------------------------------------------------------

def price_all_no_dollar(file: CSVFile):
    """Every Price value loses the '$' prefix and becomes a bare float.
    Source had '$74.69' (CURRENCY type); now '74.69' (FLOAT). Every cell
    normalizes differently."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[5]/value")
    for v in cells:
        if v.text:
            v.text = v.text.replace("$", "")


# ---------------------------------------------------------------------------
# 35. URL column with unquoted commas in EVERY row (column shift everywhere)
# ---------------------------------------------------------------------------

def url_all_unquoted_csv_fragment(file: CSVFile):
    """Replace every URL with 'a,b,c' unquoted. URL was always quoted
    (long string with http://...); now becomes 3 unquoted cells per row.
    Every row column-shifts by 2 → Comments column gets URL fragment."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[8]")
    for c in cells:
        for child in list(c):
            c.remove(child)
        c.append(E.value("a,b,c"))


# ---------------------------------------------------------------------------
# 36. Combine three known-strong attacks into one mega
# ---------------------------------------------------------------------------

def mega_late_currency_overflow_eu(file: CSVFile):
    """Mega: late-row Qty overflow + late Price EU decimal + late date chaos.
    Targets duckdbauto where multiple columns flip wrong types."""
    pb.changeCell(file, row=80, col=DATE_COL, new_content="2024-13-45")
    pb.changeCell(file, row=81, col=DATE_COL, new_content="bad-date")
    pb.changeCell(file, row=82, col=QTY_COL, new_content="99999999999999999999")
    pb.changeCell(file, row=83, col=QTY_COL, new_content="-1e9999")
    pb.changeCell(file, row=84, col=QTY_COL, new_content="NaN")
    pb.changeCell(file, row=80, col=PRICE_COL, new_content="negative")
    pb.changeCell(file, row=81, col=TIME_COL, new_content="not-a-time")


# ---------------------------------------------------------------------------
# 37. ProductID column entirely floats (e.g. 1.0, 2.0...) — flips type
# ---------------------------------------------------------------------------

def productid_all_floats(file: CSVFile):
    """Every PRODUCTID becomes a small float. Source had alphanumeric like
    'MG-8769'; auto-detection now sees a uniform DOUBLE column. All 83
    cells mismatch on normalize_cell (FLOAT '1.5' vs STRING 'mg-8769')."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[4]/value")
    for i, v in enumerate(cells):
        v.text = f"{i + 1}.{i:03d}"


# ---------------------------------------------------------------------------
# 38. ProductDescription with currency tokens (price_parser sees them)
# ---------------------------------------------------------------------------

def desc_all_currency_prefix(file: CSVFile):
    """Prepend '$10 ' to every ProductDescription. parse_cell normalize will
    extract a currency from the first dollar amount; whole column flips
    type from STRING to CURRENCY."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[7]/value")
    for v in cells:
        if v.text:
            v.text = "$10 " + v.text


# ---------------------------------------------------------------------------
# 39. Comments column gets unquoted comma everywhere (column shift, 1 extra cell)
# ---------------------------------------------------------------------------

def comments_all_unquoted_two_values(file: CSVFile):
    """Comments was empty; fill with 'foo,bar' unquoted. Adds 1 cell to
    every row → 83 column-shifts. Even though Comments is the LAST column,
    extra cell after means parser sees 10 cells per row."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[9]")
    for c in cells:
        for child in list(c):
            c.remove(child)
        c.append(E.value("foo,bar"))


# ---------------------------------------------------------------------------
# 40. ProductType column gets unquoted commas — column shift
# ---------------------------------------------------------------------------

def producttype_all_unquoted_comma(file: CSVFile):
    """Every ProductType value becomes 'A,B,C' unquoted, which the
    parser will read as 3 cells per row instead of 1 → +2 cells per row →
    massive column shift across all 83 rows."""
    root = file.xml.getroot()
    cells = root.xpath("//row[@role='data']/cell[6]")
    for c in cells:
        for child in list(c):
            c.remove(child)
        c.append(E.value("A,B,C"))


POLLUTIONS = [
    ("typeinfer_qty_late_string_anomaly.csv", qty_late_string_anomaly, {}),
    ("typeinfer_qty_late_overflow.csv", qty_late_overflow, {}),
    ("typeinfer_qty_late_inf.csv", qty_late_inf, {}),
    ("typeinfer_qty_late_huge_float.csv", qty_late_huge_float, {}),
    ("typeinfer_qty_late_currency.csv", qty_late_currency, {}),
    ("typeinfer_qty_all_currency.csv", qty_all_currency, {}),
    ("typeinfer_price_european_decimal.csv", price_european_decimal, {}),
    ("typeinfer_qty_thousands_separator.csv", qty_thousands_separator, {}),
    ("typeinfer_price_thousands_currency.csv", price_thousands_currency, {}),
    ("typeinfer_qty_pseudo_booleans.csv", qty_pseudo_booleans, {}),
    ("typeinfer_comments_pseudo_dates.csv", comments_pseudo_dates, {}),
    ("typeinfer_date_format_chaos.csv", date_format_chaos, {}),
    ("typeinfer_date_excel_serials.csv", date_excel_serials, {}),
    ("typeinfer_time_locale_ambiguity.csv", time_locale_ambiguity, {}),
    ("typeinfer_qty_numeric_edges.csv", qty_numeric_edges, {}),
    ("typeinfer_qty_hex_octal.csv", qty_hex_octal, {}),
    ("typeinfer_qty_denormal_floats.csv", qty_denormal_floats, {}),
    ("typeinfer_productid_pseudo_scientific.csv", productid_pseudo_scientific, {}),
    ("typeinfer_url_as_booleans.csv", url_as_booleans, {}),
    ("typeinfer_url_as_dates.csv", url_as_dates, {}),
    ("typeinfer_qty_null_flavors.csv", qty_null_flavors, {}),
    ("typeinfer_qty_whitespace_padded.csv", qty_whitespace_padded, {}),
    ("typeinfer_qty_mixed_numeric_formats.csv", qty_mixed_numeric_formats, {}),
    ("typeinfer_productid_csv_fragment.csv", productid_csv_fragment, {}),
    ("typeinfer_qty_uniform_with_word_anomaly.csv", qty_uniform_with_word_anomaly, {}),
    ("typeinfer_qty_uniform_with_late_negative.csv", qty_uniform_with_late_negative, {}),
    ("typeinfer_url_whitespace_only.csv", url_whitespace_only, {}),
    ("typeinfer_qty_empty_cells_scattered.csv", qty_empty_cells_scattered, {}),
    ("typeinfer_url_unix_timestamps.csv", url_unix_timestamps, {}),
    ("typeinfer_comments_excel_serials.csv", comments_excel_serials, {}),
    ("typeinfer_qty_pure_01_then_anomaly.csv", qty_pure_01_then_anomaly, {}),
    ("typeinfer_qty_signed_plus_leading_zero.csv", qty_signed_plus_leading_zero, {}),
    ("typeinfer_price_currency_chaos.csv", price_currency_chaos, {}),
    ("typeinfer_productid_only_digits.csv", productid_only_digits, {}),
    ("typeinfer_productid_e_notation.csv", productid_e_notation, {}),
    ("typeinfer_time_12h_24h_mix.csv", time_12h_24h_mix, {}),
    ("typeinfer_date_2digit_4digit.csv", date_2digit_4digit, {}),
    ("typeinfer_qty_all_booleans.csv", qty_all_booleans, {}),
    ("typeinfer_qty_late_boolean.csv", qty_late_boolean, {}),
    ("typeinfer_url_mixed_types_drift.csv", url_mixed_types_drift, {}),
    ("typeinfer_qty_long_zeros_then_text.csv", qty_long_zeros_then_text, {}),
    ("typeinfer_date_iso_timestamps.csv", date_iso_timestamps, {}),
    # Round 2 sharpened entries
    ("typeinfer_multi_column_late_anomaly.csv", multi_column_late_anomaly, {}),
    ("typeinfer_qty_all_with_explicit_float.csv", qty_all_with_explicit_float, {}),
    ("typeinfer_qty_all_unquoted_thousands.csv", qty_all_unquoted_thousands, {}),
    ("typeinfer_price_all_unquoted_eu.csv", price_all_unquoted_eu, {}),
    ("typeinfer_late_rows_extra_cell.csv", late_rows_extra_cell, {}),
    ("typeinfer_qty_late_huge_and_strings.csv", qty_late_huge_and_strings, {}),
    ("typeinfer_qty_all_pseudo_bool_strings.csv", qty_all_pseudo_bool_strings, {}),
    ("typeinfer_date_all_excel_serials.csv", date_all_excel_serials, {}),
    ("typeinfer_price_all_no_dollar.csv", price_all_no_dollar, {}),
    ("typeinfer_url_all_unquoted_csv_fragment.csv", url_all_unquoted_csv_fragment, {}),
    ("typeinfer_mega_late_currency_overflow_eu.csv", mega_late_currency_overflow_eu, {}),
    ("typeinfer_productid_all_floats.csv", productid_all_floats, {}),
    ("typeinfer_desc_all_currency_prefix.csv", desc_all_currency_prefix, {}),
    ("typeinfer_comments_all_unquoted_two_values.csv", comments_all_unquoted_two_values, {}),
    ("typeinfer_producttype_all_unquoted_comma.csv", producttype_all_unquoted_comma, {}),
]
