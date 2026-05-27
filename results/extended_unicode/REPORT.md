# Engine A — Unicode & Encoding Hostility — Report

This engine attacks the Pollock CSV-parsing benchmark with Unicode and
byte-level edge cases that mainstream parsers should handle but often
don't. All filenames begin with `unicode_`. 36 pollutions total
(25 in round 1, then dud-pruning + 12 sharpened variants in round 2).

## Engine summary (mean across 36 files)

| SuT | success | cell_f1 | header_f1 | record_f1 |
|-----|---------|---------|-----------|-----------|
| duckdbparse | 0.917 | 0.638 | 0.917 | 0.579 |
| duckdbauto  | 1.000 | 0.679 | 0.413 | 0.461 |
| pandas      | 0.250 | 0.158 | 0.139 | 0.155 |
| pycsv       | 0.306 | 0.219 | 0.198 | 0.196 |

pandas and pycsv are devastated by this engine: more than 70% of files
either crash or produce 0 cells in agreement with the clean reference.
The two duckdb readers do better but each has its own failure mode:
duckdbparse is dialect-aware and handles BOMs/encodings, but trips on
Unicode line separators and smart quotes; duckdbauto auto-detects
header rows and gets confused by header-position lies (BOMs, mixed
encodings, NBSP delimiters).

## Top 10 attacks (sorted by mean cell_f1 across 4 SuTs, lower = worse for parsers)

| # | filename | duckdbparse | duckdbauto | pandas | pycsv | mean cell_f1 | theory |
|---|---|---|---|---|---|---|---|
| 1 | `unicode_zwsp_around_every_delim.csv` | 0.012 | 0.082 | 0.000 | 0.000 | **0.024** | Every comma wrapped in U+200B (ZWSP). Multi-byte UTF-8 around the delimiter defeats simple `,`-split logic and the autodetectors think delimiter = ZWSP byte sequence. |
| 2 | `unicode_rlm_lrm_marks.csv` | 0.000 | 0.082 | 0.000 | 0.111 | **0.048** | RLM/LRM injected in headers and around field delimiters via XML pipeline. The non-ASCII characters appear in the parsed delimiter, breaking column count and shifting cells. |
| 3 | `unicode_smart_double_quotes.csv` | 0.000 | 0.552 | 0.000 | 0.000 | **0.138** | Quote char declared as U+201C in params; pycsv/pandas expect ASCII `"`, so quoted fields containing commas split into separate columns. duckdbparse honors the param but the quote-state machine is brittle. |
| 4 | `unicode_smart_single_quotes.csv` | 0.000 | 0.552 | 0.000 | 0.000 | **0.138** | Same mechanism as smart double quotes, with U+2018/U+2019. |
| 5 | `unicode_bom_with_ps.csv` | 0.024 | 0.555 | 0.000 | 0.000 | **0.145** | BOM hides from sniffer + every `\r\n` replaced with U+2029 PS. Parsers see one giant line. |
| 6 | `unicode_bom_with_nel.csv` | 0.024 | 0.555 | 0.000 | 0.000 | **0.145** | BOM + NEL (U+0085) line endings. NEL is in C1 control range; many parsers ignore it. Result: one giant row. |
| 7 | `unicode_record_delim_nel.csv` | 0.024 | 0.555 | 0.000 | 0.000 | **0.145** | Plain NEL line endings (no BOM). Same outcome — none of the four parsers recognize NEL as a record delimiter. |
| 8 | `unicode_record_delim_ls.csv` | 0.024 | 0.555 | 0.000 | 0.000 | **0.145** | Plain U+2028 LS line endings. Encoded as 3 bytes E2 80 A8 — invisible to ASCII line-splitters. |
| 9 | `unicode_record_delim_ps.csv` | 0.024 | 0.555 | 0.000 | 0.000 | **0.145** | Plain U+2029 PS line endings. Same as LS attack. |
| 10 | `unicode_ls_no_terminator.csv` | 0.024 | 0.556 | 0.000 | 0.000 | **0.145** | LS line endings + trailing terminator stripped — eliminates the EOF-flush some parsers rely on. |

## All pollutions — full per-SuT table

Sorted by mean cell_f1 (ascending). Columns: cell_f1 (`c`), header_f1 (`h`), record_f1 (`r`).

| filename | duckdbparse c/h/r | duckdbauto c/h/r | pandas c/h/r | pycsv c/h/r | mean |
|---|---|---|---|---|---|
| unicode_zwsp_around_every_delim.csv | 0.01/1.00/0.00 | 0.08/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.024 |
| unicode_rlm_lrm_marks.csv | 0.00/0.00/0.00 | 0.08/0.00/0.00 | 0.00/0.00/0.00 | 0.11/0.11/0.00 | 0.048 |
| unicode_smart_double_quotes.csv | 0.00/0.00/0.00 | 0.55/0.58/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.138 |
| unicode_smart_single_quotes.csv | 0.00/0.00/0.00 | 0.55/0.58/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.138 |
| unicode_bom_with_ps.csv | 0.02/1.00/0.00 | 0.55/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_bom_with_nel.csv | 0.02/1.00/0.00 | 0.55/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_record_delim_nel.csv | 0.02/1.00/0.00 | 0.55/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_record_delim_ls.csv | 0.02/1.00/0.00 | 0.55/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_record_delim_ps.csv | 0.02/1.00/0.00 | 0.55/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_ls_no_terminator.csv | 0.02/1.00/0.00 | 0.56/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.145 |
| unicode_fffd_everywhere.csv | 0.50/1.00/0.00 | 0.45/0.00/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.238 |
| unicode_smart_quotes_invalid_utf8.csv | 0.64/1.00/0.00 | 0.55/0.58/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.297 |
| unicode_mixed_line_endings.csv | 0.73/1.00/0.50 | 0.71/0.53/0.47 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.358 |
| unicode_lone_surrogate.csv | 0.99/1.00/0.99 | 0.94/0.95/0.92 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.482 |
| unicode_invalid_utf8_bytes.csv | 0.98/1.00/0.98 | 0.97/1.00/0.91 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.489 |
| unicode_multiple_boms_scattered.csv | 0.99/1.00/0.98 | 0.98/1.00/0.91 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.494 |
| unicode_overlong_utf8.csv | 0.99/1.00/0.99 | 0.99/1.00/0.92 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_bom_utf16le_in_utf8.csv | 1.00/1.00/1.00 | 0.98/0.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_bom_utf16be_in_utf8.csv | 1.00/1.00/1.00 | 0.98/0.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_invalid_utf8_in_quoted_field.csv | 1.00/1.00/1.00 | 0.98/0.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_bom_utf32be.csv | 1.00/1.00/1.00 | 0.98/0.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_bom_utf32le.csv | 1.00/1.00/1.00 | 0.98/0.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.495 |
| unicode_bom_with_embedded_nul.csv | 1.00/1.00/0.96 | 0.99/1.00/0.90 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.496 |
| unicode_bom_midfile.csv | 1.00/1.00/0.99 | 0.99/1.00/0.92 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.497 |
| unicode_bom_plus_smart_quotes.csv | 1.00/1.00/1.00 | 0.99/0.89/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.498 |
| unicode_crlf_to_lf_with_bom.csv | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.498 |
| unicode_bom_utf8_doubled.csv | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.498 |
| unicode_bom_utf8.csv | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | 0.498 |
| unicode_ideographic_space_delim.csv | 1.00/1.00/1.00 | 0.12/0.00/0.00 | 0.00/0.00/0.00 | 1.00/1.00/1.00 | 0.531 |
| unicode_nbsp_field_delim.csv | 1.00/1.00/1.00 | 0.12/0.00/0.00 | 0.00/0.00/0.00 | 1.00/1.00/1.00 | 0.531 |
| unicode_utf16le_file.csv | 0.08/1.00/0.00 | 0.08/0.00/0.00 | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.538 |
| unicode_utf16be_file.csv | 0.08/1.00/0.00 | 0.09/0.00/0.00 | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.540 |
| unicode_mixed_smart_ascii_quotes.csv | 0.82/1.00/0.49 | 0.65/0.75/0.46 | 0.71/1.00/0.63 | 0.82/1.00/0.46 | 0.750 |
| unicode_mixed_header_utf16_body_utf8.csv | 0.99/1.00/0.99 | 0.36/0.00/0.00 | 0.98/0.00/0.98 | 0.98/0.00/0.92 | 0.827 |
| unicode_embedded_nul.csv | 1.00/1.00/0.96 | 0.99/1.00/0.90 | 1.00/1.00/0.96 | 0.99/1.00/0.90 | 0.992 |
| unicode_zwsp_in_header.csv | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 1.00/1.00/1.00 | 0.99/1.00/0.93 | 0.996 |

## Why each winning class works

- **Unicode line separators (NEL, LS, PS, mixed):** None of the four parsers
  recognize U+0085, U+2028, or U+2029 as record terminators by default.
  Pandas with `engine="c"` and the params-supplied `lineterminator=\r\n`
  won't see any of them. Pycsv's `Sniffer` produces a dialect that
  fixates on `\r\n`. duckdbparse's `read_csv` with explicit dialect
  reads everything as one giant row. duckdbauto succeeds in producing
  output but loses the column structure, so cell_f1 ≈ 0.55.

- **Smart curly quotes (U+201C/U+201D):** Parameters honestly declare
  `quotechar = "\u201c"`, but pycsv passes that through `Sniffer` which
  re-detects ASCII `"`, then comma-rich product descriptions split
  across columns. Pandas accepts the multi-byte quote char but its
  `engine="c"` doesn't unescape U+201C correctly, so quoted commas
  break rows. duckdbparse passes the exact quote char to duckdb's
  reader but its tokenizer also treats it as foreign and errors out.

- **BOMs (UTF-8, UTF-16 LE/BE, UTF-32 LE/BE, doubled, mid-file):** pycsv
  fails universally — `Sniffer.sniff()` consumes the BOM bytes and
  then misidentifies the dialect, so the resulting reader yields
  zero correct rows. Pandas with `encoding="ascii"` (the param value)
  raises `UnicodeDecodeError` immediately on every BOM (success=0).
  duckdbparse handles the BOM transparently. duckdbauto handles
  most BOMs except UTF-16/32 BOMs on UTF-8-encoded files, where it
  decides the file is binary garbage and produces unstructured output.

- **Smart quotes + ASCII quotes mixed:** pycsv's Sniffer picks
  whichever quote it sees first and then mismatches all other rows.
  duckdbparse and pandas similarly only honor one quote shape.

- **NBSP / ideographic space as field delimiter:** Parameters declare
  the multi-byte delimiter; duckdbparse and pycsv handle it (pycsv via
  Sniffer rediscovering the space delimiter, duckdbparse via the
  explicit param). Pandas with `engine="c"` and `delimiter=None`
  auto-detects and prefers `,`. duckdbauto also gravitates to a
  single-byte separator.

- **UTF-16 LE/BE files (params honest):** pycsv and pandas decode them
  fine because they pass the encoding through. duckdbparse and
  duckdbauto error out — duckdb's `read_csv` doesn't accept utf_16_le
  as an encoding, so they fall back to raw-bytes which is hopeless.

- **Invalid UTF-8 / lone surrogate / overlong UTF-8:** The duckdb
  readers tolerate invalid UTF-8 thanks to `ignore_errors=True` and
  produce mostly correct output. Pandas with `engine="c"` and the
  ascii encoding from params fails on the first non-ascii byte. Pycsv
  decodes via Python's strict-ascii codec and crashes.

- **ZWSP around every delimiter:** Even duckdbparse loses cells because
  the embedded ZWSP makes the "previous column" and "next column"
  values include extra zero-width spaces, which the multiset
  comparator counts as different cell content. The duckdbauto
  autodetector decides the delimiter is now the ZWSP byte sequence
  and produces nonsense.

- **RLM/LRM around delimiters:** Same story as ZWSP, but more violent
  because the marks appear in the `field_delimiter` element of the
  XML, so parsers see e.g. `\u200e,\u200e` as the delimiter — none
  of the four can re-parse that.

- **FFFD scattered:** Replacement characters every 25 chars. Pandas
  and pycsv decode-and-crash because params declare ascii, and FFFD
  is non-ASCII. duckdb readers handle the multi-byte sequence but
  cell content drifts due to the inserted characters.

- **Mixed line endings (CRLF/LF/NEL/LS):** All parsers split on `\r\n`
  but treat the LF and Unicode separators as cell content, producing
  a small number of giant rows. pandas/pycsv crash; duckdb produces
  malformed output but better cell_f1 because most cells survive.

## Duds (left in but barely scoring; would drop in next iteration)

- `unicode_embedded_nul.csv` (mean 0.992) — duckdb and pandas both
  treat the NUL bytes as cell content; pycsv truncates at NUL but the
  delta is tiny.
- `unicode_zwsp_in_header.csv` (mean 0.996) — ZWSP is silently kept in
  cell text; the cell-multiset comparison is char-by-char so the
  inserted ZWSPs do change the strings, but rounding hides this.

Both are kept because they are the seed pollutions and the
sharpened variants (`unicode_zwsp_around_every_delim`,
`unicode_bom_with_embedded_nul`) are derived from them.

## Methodology notes

- All clean files and parameter JSONs are written by the standard XML
  pipeline so the evaluator compares against an honest reference.
- For pollutions that change the actual file encoding (UTF-16-LE,
  CP1252, UTF-7), `EncodingAwareRawBytePolluter` sets `file.encoding`
  before `write_parameters` runs so the declared encoding matches the
  on-disk bytes — this isolates Unicode-handling bugs from
  dialect-mismatch tests (which belong to a separate engine).
- All files stay below 5 MB; the dataset totals ~1 MB on disk.
