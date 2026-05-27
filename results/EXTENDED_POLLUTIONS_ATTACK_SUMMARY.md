# Extended Pollutions — Attack Summary

A digestible reference for the new CSV-parsing attacks added on top of the
headline Pollock benchmark. Each entry describes one pollution class, shows a
concrete example, lists how each parser performs, gives real-world context,
and comments on the parameters JSON's relationship to the polluted file.

## Source CSV (for reference)

All attacks are derived from `results/source.csv` (84 rows, 9 columns):

```
DATE,TIME,Qty,PRODUCTID,Price,ProductType,"ProductDescription","URL",Comments
28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,"These waterproof hiking boots for men are rugged enough for peak performance...","https://www.example.com/product/MG_8769.html",
29/01/2018,00:15,0,RI-3895,$29.81,Light-Up Running Jacket,"The next level of weather protection...","https://www.example.com/product/RI_3895.html",
...
```

## SuTs evaluated

- **duckdbparse** — DuckDB `read_csv()` with explicit dialect from parameters JSON, `auto_detect=False`, all columns VARCHAR. Trusts parameters.
- **duckdbauto** — DuckDB `read_csv()` with auto-detection. Sniffs everything.
- **pandas** — `pd.read_csv()` with `dtype=object`, `engine="c"`, `delimiter=None` (auto), encoding from parameters.
- **pycsv** — Python stdlib `csv.reader` with dialect from `csv.Sniffer().sniff()`.
- **clevercs** — `clevercsv.Sniffer().sniff()`. More robust sniffer than stdlib.

Scores below are `cell_f1` (multiset overlap on cell content, 0.0 = no match,
1.0 = perfect match). `success=0` means the parser raised an exception and
produced no output.

## Honesty key

- ✅ **honest** — parameters JSON accurately describes the polluted file
- ❌ **lie** — parameters JSON disagrees with the polluted file by design
- ⚠️ **inexpressible** — the file's pathology can't be represented in the parameters schema, so the JSON falls back to defaults that end up being technically wrong

---

## 1. Unicode line separator (U+2029) instead of CRLF

**Attack.** Replace every `\r\n` byte sequence in the file with the 3-byte
UTF-8 encoding of U+2029 PARAGRAPH SEPARATOR (`E2 80 A9`). The file becomes
visually multi-line (because U+2029 is a line separator) but contains zero
`\r` or `\n` bytes anywhere.

**Example bytes (hex):**

```
... Comments [E2 80 A9] 28/01/2018,00:00,2,MG-8769,$74.69,...
              ↑
              U+2029 — invisible to ASCII line splitters
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.024 | 1 | Looks for `\r\n`, finds none, loads everything as one row |
| duckdbauto | 0.555 | 1 | Auto-detect partial recovery |
| pandas | 0.000 | 0 | `lineterminator` mismatch → exception |
| pycsv | 0.000 | 0 | Sniffer can't find boundary → exception |
| clevercs | 0.000 | 0 | Same as pycsv |

**Breaks 5 of 5 SuTs.**

**Params status:** ⚠️ **inexpressible.** Parameters declare
`row_delimiter: "\r\n"` because the schema has no clean way to encode a
Unicode line separator there.

**Real-world source.** Files copy-pasted out of macOS Pages, Microsoft Word,
or Apple Notes. PDF text extraction tools (pdfplumber, pdftotext) often emit
U+2028/U+2029 between paragraphs. HTML scrapers that preserve `<p>` breaks as
raw Unicode.

---

## 2. Zero-width space around every delimiter

**Attack.** Wrap every `,` field delimiter in zero-width space (U+200B,
3-byte UTF-8 `E2 80 8B`). The file looks identical to the original in any
text editor, but every cell now has invisible ZWSP characters glued to its
boundaries.

**Example bytes:**

```
DATE [E2 80 8B] , [E2 80 8B] TIME [E2 80 8B] , [E2 80 8B] Qty ...
       ↑                          ↑
       ZWSP                       ZWSP
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.012 | 1 | Splits on `,`, every cell now has ZWSP attached → multiset mismatch |
| duckdbauto | 0.082 | 1 | Auto-detect picks ZWSP-byte sequence as delimiter |
| pandas | 0.000 | 0 | encoding=ascii in params + ZWSP is non-ASCII → UnicodeDecodeError |
| pycsv | 0.000 | 0 | Same encoding crash |
| clevercs | 0.000 | 0 | Same encoding crash |

**Breaks 5 of 5 SuTs.**

**Params status:** ⚠️ **inexpressible.** Parameters declare `delimiter: ","`
honestly describing the structural delimiter, but cannot say "comma surrounded
by ZWSP".

**Real-world source.** PDF-to-CSV extraction tools (pdfplumber, Tabula
sometimes inject ZWSPs at column boundaries to preserve visual spacing). CSVs
exported from web apps that use ZWSPs as anti-scraping markers. Cut-and-paste
from word processors that preserved hidden formatting.

---

## 3. Smart curly quotes substituted for ASCII quotes

**Attack.** Replace every ASCII `"` quote with curly Unicode quotes (U+201C
left, U+201D right). Parameters honestly declare the smart quotes as the
quotechar.

**Example:**

```
Source:    ...,"These waterproof boots, rugged...",...
Polluted:  ...,“These waterproof boots, rugged...”,...
                ↑                                ↑
                U+201C                           U+201D
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.000 | 0 | duckdb tokenizer rejects multi-byte quotechar → crash |
| duckdbauto | 0.552 | 1 | Auto-detect partial recovery |
| pandas | 0.000 | 0 | C engine can't handle multi-byte quotechar → exception |
| pycsv | 0.000 | 1 | Sniffer ignores params, re-detects ASCII `"`; unprotected commas split rows |
| clevercs | 0.664 | 1 | Sniffer handles partially |

**Breaks 4 of 5 SuTs.**

**Params status:** ✅ **honest.** Parameters declare `quotechar: "”“"`; the
file genuinely uses smart quotes.

**Real-world source.** Excel's "AutoCorrect → Replace straight quotes with
smart quotes" feature, on by default. Word documents saved as CSV. Any CSV
authored in a rich-text editor (Google Docs, Pages). News-article scraped
data.

---

## 4. File is UTF-16-LE, params declare UTF-8

**Attack.** Encode the rendered CSV in UTF-16 little-endian. Each character
becomes 2 bytes (ASCII chars get a NUL byte after them). The parameters JSON
claims the file is UTF-8.

**Example bytes:**

```
File bytes (utf-16-le):  44 00 41 00 54 00 45 00 2C 00 ...
                          D     A     T     E     ,
                          (NUL byte after each char)

Params declare:          {"encoding": "utf-8"}
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.081 | 1 | Reads as UTF-8, NUL bytes survive in cells |
| duckdbauto | 0.079 | 1 | Same |
| pandas | 0.102 | 1 | Reads with explicit utf-8, NULs in cells |
| pycsv | 0.056 | 1 | Same |
| clevercs | 0.000 | 0 | Sniffer crashes on the binary-looking content |

**Breaks 5 of 5 SuTs** (4 produce garbage, 1 crashes).

**Params status:** ❌ **lie.** Parameters claim utf-8; file is utf-16-le.

**Real-world source.** Windows Notepad's default save encoding for non-ASCII
content (until Win10 1903 changed the default). SQL Server `bcp` exports
default to UTF-16-LE. Excel "Save as Unicode Text". A common pipeline failure
when someone hands a Windows-exported file to a Linux ingest service.

---

## 5. Stray 0xFE byte after every CRLF

**Attack.** Insert a single 0xFE byte immediately after every `\r\n`. The
file otherwise looks like a normal CRLF-terminated CSV, but each row now has
junk at its very start.

**Example bytes:**

```
... Comments \r \n FE 28/01/2018,00:00,2,MG-8769,...
                  ↑
                  Single 0xFE byte
```

**Why 0xFE specifically?** Three failure modes at once:
- Illegal as a UTF-8 start byte (UTF-8 reserves only ranges that exclude 0xFE/0xFF)
- Looks like the start of a UTF-16-BE BOM (0xFE 0xFF)
- Renders as `þ` in Latin-1 / Windows-1252 (silent corruption fallback)

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.024 | 1 | `ignore_errors=True` keeps it alive; rogue byte glues onto first cell of every row |
| duckdbauto | 0.024 | 1 | Same |
| pandas | 0.000 | 0 | UTF-8 decode: 0xFE invalid → UnicodeDecodeError |
| pycsv | 0.000 | 0 | Same crash |
| clevercs | 0.000 | 0 | Same crash |

**Breaks 5 of 5 SuTs.** Most universally devastating attack in the dataset.

**Params status:** ⚠️ **inexpressible.** Parameters declare `row_delimiter:
"\r\n"`, `encoding: "ascii"` — they can't describe "CRLF followed by a junk
byte" and can't represent 0xFE in ASCII.

**Real-world source.** Less common as a "natural" pollution but occurs in:
corrupted FTP transfers (binary mode set wrong), files concatenated with a
separator byte by some legacy ETL tools, files that had a BOM stripped
halfway and left bytes orphaned, and intentional "tagging" by some logging
systems (e.g., syslog with binary headers between records).

---

## 6. Quote character declared as §, file uses "

**Attack.** Parameters declare `quotechar: "§"` (U+00A7 SECTION SIGN). The
file's bytes are unchanged from the source — still uses ASCII `"` for
quoting.

**Example:**

```
File bytes:    ...,"These waterproof boots, rugged...",...
Params:        {"quotechar": "§"}
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.000 | 0 | duckdb's tokenizer rejects multi-byte `§` → crash |
| duckdbauto | 0.552 | 1 | Ignores params, sniffs `"`, partial recovery |
| pandas | 0.000 | 0 | Multi-byte quotechar rejected → crash |
| pycsv | 0.000 | 1 | Honors `§` literally; ASCII `"` becomes content; commas inside descriptions split rows |
| clevercs | 0.640 | 1 | Sniffer ignores params, partial recovery |

**Breaks 3 of 5 SuTs hard.** Differential damage — sniffing parsers survive.

**Params status:** ❌ **lie.** Parameters declare `§` as quotechar; the file
contains zero `§` bytes.

**Real-world source.** Misconfigured database COPY commands (`COPY t FROM
'...' (QUOTE '§')` typed wrong). Schema registry mismatches in data lakes —
the schema says one quote character, the producer wrote a different one.
Legacy systems where the quote character was changed years ago and not all
clients updated.

---

## 7. Unterminated quote at EOF

**Attack.** Normal CSV with a stray `"   ` (or `"unfinished cell`) appended
at the very end of the file, with no closing quote.

**Example:**

```
...,02/04/2018,18:30,1,XY-1234,$45.00,...,Comments
"   ← stray opening quote at EOF, never closes
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.994 | 1 | Tolerant — silently swallows the orphan |
| duckdbauto | 0.548 | 1 | Stricter mode flags the unclosed quote → partial output |
| pandas | 0.000 | 0 | C engine: "EOF inside string" → aborts before emitting any rows |
| pycsv | 0.991 | 1 | Tolerant |
| clevercs | 0.999 | 1 | Tolerant |

**Breaks 1 of 5 SuTs hard.** Pure differential damage targeting pandas's
strict mode.

**Params status:** ✅ **honest.** The file IS a comma-separated, ASCII,
CRLF-terminated CSV — the EOF garbage isn't expressible in params anyway.

**Real-world source.** Killed processes that were writing CSV (`kill -9`
mid-write). Truncated S3 multipart uploads. Disk-full failures during export.
`tail -f`'d log files that someone interpreted as complete CSVs. Partial
downloads (broken HTTP connections).

---

## 8. File uses `;`, params declare `,`

**Attack.** Replace every comma between fields with `;` (only structural
delimiters, not commas inside quoted strings). Parameters lie about the
delimiter.

**Example:**

```
File bytes:  DATE;TIME;Qty;PRODUCTID;Price;...
             28/01/2018;00:00;2;MG-8769;$74.69;...

Params:      {"delimiter": ","}
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.122 | 1 | Trusts params, finds no commas, loads each row as one giant cell |
| duckdbauto | 0.992 | 1 | Auto-detects `;`, parses correctly |
| pandas | 0.000 | 1 | sniffer + `dtype=object` produces output but cells don't match |
| pycsv | 1.000 | 1 | Sniffer finds `;`, perfect recovery |
| clevercs | 1.000 | 1 | Sniffer finds `;`, perfect recovery |

**Breaks 2 of 5 SuTs.** Cleanly separates "trust params" from "sniff" parsers.

**Params status:** ❌ **lie.** Parameters say `,`; file uses `;`.

**Real-world source.** Extremely common. German, French, Italian, Spanish
Excel installations default to `;` as CSV separator (because `,` is the
decimal separator in those locales). Hand a German Excel CSV to a US-default
ingest pipeline and this is exactly what happens. OpenOffice Calc has the
same locale-driven behavior.

---

## 9. File has 2 header rows, params declare 1

**Attack.** Insert an extra header-shaped row between the original header
and the data. Parameters claim only 1 header row.

**Example:**

```
File:    DATE,TIME,Qty,...                        ← row 0: real header
         DATE_FORMAT,TIME_FORMAT,QUANTITY,...     ← row 1: extra header (lie)
         28/01/2018,00:00,2,...                   ← row 2: first data
         29/01/2018,00:15,0,...                   ← row 3: second data

Params:  {"header_lines": 1}
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.994 | 1 | Mild drift — extra header row becomes "data" but only 1 row out of 84 |
| duckdbauto | 0.974 | 1 | Same |
| pandas | 0.982 | 1 | Same |
| pycsv | 0.974 | 1 | Same |
| clevercs | 0.982 | 1 | Same |

**Breaks 0 of 5 SuTs hard.** Mild damage across all parsers — the clean
reference combines multi-line headers with spaces, so most cells still match.

**Params status:** ❌ **lie.** Parameters say 1 header row; file has 2.

**Real-world source.** Government and scientific data formats. Census CSVs
typically have one row of column names + one row of units (`age, gender,
income\nyears, M/F, USD`). UN, World Bank, and academic-paper supplementary
data routinely use 2- or 3-row headers. Config defaults to `header=1` and
silently breaks.

---

## 10. Late row triggers type promotion (Inf in Qty column)

**Attack.** Rows 0-79 have normal small Qty values (0-9). Row 80 has `Inf`
in the Qty column. The file is otherwise pristine CSV.

**Example:**

```
DATE,TIME,Qty,PRODUCTID,...
28/01/2018,00:00,2,MG-8769,...           ← normal
29/01/2018,00:15,0,RI-3895,...           ← normal
... (78 more normal rows)
07/04/2018,12:00,Inf,XX-9999,...         ← row 80: triggers type promotion
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 1.000 | 1 | All-VARCHAR, types don't matter, perfect output |
| duckdbauto | 0.885 | 1 | Type-promotes Qty BIGINT → DOUBLE; every `2` becomes `2.0` |
| pandas | 1.000 | 1 | `dtype=object`, types don't matter |
| pycsv | 0.991 | 1 | No type inference |
| clevercs | 1.000 | 1 | No type inference |

**Breaks 1 of 5 SuTs.** Highly targeted — only duckdbauto's type sniffer is
vulnerable.

**Params status:** ✅ **honest.** The file IS a comma-separated, ASCII CSV
with the declared structure — the attack is on type inference, not dialect.

**Real-world source.** Database exports where a column is mostly small ints
but has rare NaN/Inf/sentinel values. Sensor data with occasional
out-of-range readings. Financial data with `999999999` sentinel for
"missing". Survey data where a free-text "other" answer appears in row 5000
of an otherwise numeric column.

---

## 11. Unquoted commas in content

**Attack.** Strip the protective quotes from a column whose values contain
commas (e.g., ProductDescription or ProductType). The internal commas now
behave as field separators.

**Example:**

```
Source row (correctly quoted):
  28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,
  "These waterproof boots, rugged for peak performance",https://...

Polluted row (quotes stripped from ProductDescription):
  28/01/2018,00:00,2,MG-8769,$74.69,Men's Waterproof Hiking Boots,
  These waterproof boots, rugged for peak performance,https://...
                          ↑                          ↑
                          parser treats as           parser treats as
                          field separators
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.671 | 1 | Sees 11 fields per row instead of 9, every cell shifts right |
| duckdbauto | 0.800 | 1 | Same shift, slightly better recovery via null_padding |
| pandas | 0.671 | 1 | Same shift |
| pycsv | 0.800 | 1 | Same shift |
| clevercs | 0.802 | 1 | Same shift |

**Breaks 5 of 5 SuTs uniformly.** No defense in dialect declaration — this
is a content attack, not a parser bug.

**Params status:** ✅ **honest.** The file genuinely has more fields per row
than the declared structure expects. The lie is in the data, not the
metadata.

**Real-world source.** Hand-edited CSVs ("I'll just put John, Smith here").
Legacy CRM exports that don't quote consistently. Address fields exported as
`123 Main St, Apt 4` without quoting. Open-text survey responses written
naively to CSV.

---

## 12. European decimal commas in numeric column

**Attack.** Replace `$74.69` with `74,69`, `$29.81` with `29,81`, etc. for
every Price cell. The file remains comma-separated.

**Example:**

```
Source:    ...,$74.69,...
Polluted:  ...,74,69,...
                ↑↑
                European decimal — but parser splits on `,`
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.783 | 1 | Splits on every `,` → 10 columns instead of 9 → Price column splits in two |
| duckdbauto | 0.775 | 1 | Same |
| pandas | 0.782 | 1 | Same |
| pycsv | 0.838 | 1 | Same |
| clevercs | 0.846 | 1 | Same |

**Breaks 5 of 5 SuTs.**

**Params status:** ✅ **honest.** File is genuinely comma-separated; the
attack is that decimal commas now look like field separators.

**Real-world source.** Same locale clash as #8. Financial data from
German/French banks. Pricing data from EU e-commerce platforms. Scientific
data from European labs (`9,81 m/s²` for gravity). A worldwide source of
pipeline failures.

---

## 13. Single-column file with `^` marker on row 0

**Attack.** Row 0 is just a single `^`. Rows 1+ each contain ONE quoted cell
that holds the whole row's content (with internal commas).

**Example:**

```
File:    ^
         "28/01/2018,00:00,2,MG-8769,$74.69,Men's...,These waterproof...,https://...,"
         "29/01/2018,00:15,0,RI-3895,$29.81,Light-Up...,The next level...,https://...,"
         ...

Params:  {"delimiter": ","}
Clean:   The original 9-column comma-separated source.
```

**Performance:**

| SuT | cell_f1 | success | Failure mode |
|---|---:|---:|---|
| duckdbparse | 0.121 | 1 | Trusts `,` from params, splits each mega-cell on internal commas |
| duckdbauto | 0.000 | 1 | Auto-detects, settles on a wrong dialect |
| pandas | 0.000 | 1 | `delimiter=None` sniffs commas inside the cells |
| pycsv | 0.000 | 1 | Sniffer picks `,`, splits inside cells |
| clevercs | 0.463 | 1 | Sniffer is more robust here, partial recovery |

**Breaks 4 of 5 SuTs.**

**Params status:** ❌ **lie.** Parameters declare `,` as the delimiter; the
file is structurally a 1-column file (the only "delimiter" character at the
top level is the quotation marks).

**Real-world source.** Mainframe and AS/400 exports often use `^` or `|` as
record separators with the entire row as a single field. Some logging
systems write records as `<timestamp>^<entire_log_line>`. Government data
from the 1990s frequently in this format. Fixed-width formats partially
converted to CSV.

---

## Summary table

| # | Attack | Params | Wild source | Breaks 5 SuTs | Crashes (success=0) |
|---|---|---|---|:---:|:---:|
| 1 | U+2029 line separator | ⚠️ inexpressible | macOS/Word, PDF extraction | 5/5 | 3 |
| 2 | ZWSP around delimiters | ⚠️ inexpressible | PDF extraction, anti-scraping | 5/5 | 3 |
| 3 | Smart curly quotes | ✅ honest | Excel AutoCorrect, Word→CSV | 4/5 | 3 |
| 4 | UTF-16-LE / params utf-8 | ❌ lie | Windows Notepad, SQL bcp | 5/5 | 1 |
| 5 | 0xFE after every CRLF | ⚠️ inexpressible | Corrupt FTP, partial BOM strip | 5/5 | 3 |
| 6 | Quote § / file uses " | ❌ lie | Misconfigured COPY, schema drift | 3/5 | 2 |
| 7 | Unterminated quote at EOF | ✅ honest | Killed export, truncated upload | 1/5 | 1 |
| 8 | File `;`, params `,` | ❌ lie | German/French Excel exports | 2/5 | 0 |
| 9 | 2 header rows, params 1 | ❌ lie | Census, UN, scientific CSVs | 0/5 | 0 |
| 10 | Late-row type promotion | ✅ honest | DB exports with sentinels | 1/5 | 0 |
| 11 | Unquoted commas in content | ✅ honest | Hand-edited CSVs, legacy CRM | 5/5 (mild) | 0 |
| 12 | European decimal commas | ✅ honest | EU financial/scientific data | 5/5 (mild) | 0 |
| 13 | Single-col with `^` marker | ❌ lie | Mainframe, log exports | 4/5 | 0 |

## Three patterns that separate hard from soft attacks

1. **Inexpressible bytes (#1, #2, #5).** Bytes that the parameters schema
   literally cannot describe. Universal damage because parsers default to
   interpreting params as honest while the bytes contradict them.

2. **Encoding lies (#4).** Bytes that need a different decoder than the
   params demand. Universal damage; mostly silent corruption rather than
   crashes.

3. **Content attacks (#11, #12).** Bytes that are perfectly valid CSV under
   any dialect, but the content itself creates more fields than the structure
   expects. Universal *mild* damage; no parser defends against it because
   it's not a parser problem, it's a data problem.

**Differential attacks (#7, #8, #10)** are valuable for benchmarking *which*
parser to choose, not for assessing absolute robustness — they isolate
specific implementation choices (strict mode, sniff vs trust, type inference).
