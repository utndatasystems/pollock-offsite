# Engine F — Adversarial Dialect Mismatch

## Theme

The polluted CSV is written with one dialect, but the parameters JSON declares
a different one. Targets parsers that *trust* the parameters file
(duckdbparse, pandas, mariadb, sqlite, libreoffice) and mimics a real-world
ETL failure: a misconfigured COPY command or a wrong dialect declared in a
config file alongside an externally-produced file.

## Engine summary

41 pollutions, all filenames prefixed `dialect_`. Two attack patterns:

1. **Pattern A (byte-level lies).** Render the CSV via the standard XML
   pipeline so `write_parameters()` produces an honest JSON. Then a byte
   mutator rewrites the rendered bytes (swap `,`→`;`, `"`→`'`, transcode to
   utf-16-le, etc.). The parameters JSON keeps describing the un-mutated
   dialect — i.e. it lies.
2. **Pattern B (parameter-key overrides).** After the standard pipeline runs
   honestly, rewrite specific keys in the parameters JSON
   (`header_lines`, `preamble_lines`, `n_columns`, `column_names`,
   `encoding`, `delimiter`, ...). Often combined with an XML mutator that
   adds extra header rows, preamble rows, or alternate columns so the file
   carries one structure while the JSON claims another.

Both patterns are wired through a `_DialectMismatchPolluter` subclass of
`RawBytePolluter` defined locally in `pollock/polluters_dialect.py`. Optional
hooks: `xml_mutator`, `mutator`, `parameter_overrides`, `encoding_override`.
This avoids touching `polluters_extended.py`.

## Results — mean cell_f1 per Python SuT (round 2, 41 files)

| SuT          | cell_f1 | header_f1 | record_f1 | success |
|--------------|---------|-----------|-----------|---------|
| duckdbparse  | 0.677   | 0.927     | 0.561     | 1.000   |
| duckdbauto   | 0.820   | 0.734     | 0.723     | 1.000   |
| pandas       | 0.522   | 0.520     | 0.466     | 0.878   |
| pycsv        | 0.757   | 0.675     | 0.701     | 0.878   |

Round 1 (25 files) baseline for comparison:

| SuT          | cell_f1 (R1) | cell_f1 (R2) | Δ      |
|--------------|--------------|--------------|--------|
| duckdbparse  | 0.723        | 0.677        | -0.046 |
| duckdbauto   | 0.902        | 0.820        | -0.082 |
| pandas       | 0.651        | 0.522        | -0.129 |
| pycsv        | 0.883        | 0.757        | -0.126 |

Round 2 sharpened variants (combined dialect lies, multi-byte delimiters,
NUL delimiter, utf-16-be, big5, BOM-vs-encoding lies, larger header/preamble
lies) demolished the auto-detect parsers (duckdbauto, pycsv).

## Top 5 attacks by mean cell_f1 across the 4 Python SuTs

1. **`dialect_encoding_lies_utf8_actual_utf16le.csv`** — mean 0.080.
   Bytes are utf-16-le; parameters declare utf-8. All four SuTs see almost
   no usable cells (0.08, 0.08, 0.10, 0.06).
2. **`dialect_encoding_lies_utf8_actual_utf16be.csv`** — mean 0.082.
   Same pattern with utf-16-be — confirms the encoding-lie attack
   generalizes beyond utf-16-le.
3. **`dialect_combo_utf16le_semicolon.csv`** — mean 0.121.
   Stacked: bytes are utf-16-le AND use `;` between fields; parameters
   claim utf-8 + `,`. Two compounding lies.
4. **`dialect_combo_comma_space_with_cp1252.csv`** — mean 0.210.
   File uses `, ` delimiter and is cp1252; parameters claim `,` + ascii.
   Pandas and pycsv crash (success=0); duckdb-family hits 0.37/0.47 cell_f1.
5. **`dialect_delim_lies_comma_actual_nul.csv`** — mean 0.319.
   File uses NUL (0x00) between fields; parameters claim `,`.
   pycsv shrugs it off (1.00) but the others sink (0.12, 0.13, 0.03).

Honourable mentions: `dialect_quote_lies_double_actual_brackets.csv` (mean
0.343, hits pandas+pycsv badly), `dialect_delim_lies_comma_actual_double_pipe.csv`
(mean 0.375, breaks pandas at 0.0), and the structural lies
`dialect_combo_preamble_and_multi_header.csv` and
`dialect_preamble_lies_zero_actual_three.csv` (silent corruption — both
make pandas mis-align all data rows).

## Per-SuT worst attacks (cell_f1)

**pandas** (the most thoroughly broken — `delimiter=None` makes it sniff,
but the wrong encoding starves the sniffer of usable bytes):
- 0.000: `dialect_delim_lies_comma_actual_semicolon.csv`
- 0.000: `dialect_delim_lies_comma_actual_tab.csv`
- 0.000: `dialect_delim_lies_comma_actual_pipe.csv`
- 0.000: `dialect_combo_comma_space_with_cp1252.csv` (crash)
- 0.000: `dialect_delim_lies_comma_actual_double_pipe.csv`
- 0.000: `dialect_encoding_bom_utf8_lies_utf16le.csv` (crash)
- 0.000: `dialect_encoding_lies_utf8_actual_big5.csv` (crash)
- 0.000: `dialect_combo_preamble_and_multi_header.csv`
- 0.000: `dialect_preamble_lies_zero_actual_three.csv`
- 0.000: `dialect_encoding_lies_ascii_actual_cp1252.csv` (crash)

**duckdbparse** (uses parameters strictly — every delimiter lie sinks it):
- 0.081: `dialect_encoding_lies_utf8_actual_utf16le.csv`
- 0.081: `dialect_encoding_lies_utf8_actual_utf16be.csv`
- 0.081: `dialect_combo_utf16le_semicolon.csv`
- 0.122: every byte-level delimiter lie (semicolon/tab/pipe/double-pipe/NUL)
- 0.384: `dialect_delim_lies_comma_actual_comma_space.csv`

**pycsv** (Python csv.reader with sniffer; encoding lies kill it):
- 0.000: `dialect_encoding_bom_utf8_lies_utf16le.csv`
- 0.000: `dialect_combo_comma_space_with_cp1252.csv`
- 0.000: `dialect_encoding_lies_ascii_actual_utf8.csv`
- 0.000: `dialect_quote_lies_double_actual_brackets.csv`
- 0.000: `dialect_encoding_lies_ascii_actual_cp1252.csv`
- 0.000: `dialect_encoding_lies_utf8_actual_big5.csv`

**duckdbauto** (auto-detects most things, hardest target):
- 0.079: `dialect_encoding_lies_utf8_actual_utf16le.csv`
- 0.086: `dialect_encoding_lies_utf8_actual_utf16be.csv`
- 0.125: `dialect_delim_lies_comma_actual_nul.csv`
- 0.152: `dialect_combo_utf16le_semicolon.csv`
- 0.192: `dialect_delim_subtle_mostly_comma_some_semicolon.csv` (10% rows
  use `;`, 90% use `,`; sniffer locks onto `,` and rejects 10%)
- 0.469: `dialect_combo_comma_space_with_cp1252.csv`

## Key observations

- **Encoding lies are the universal weapon.** They corrupt bytes before
  any sniffer or parameter-driven parser even sees usable text. Even the
  auto-detect SuTs (duckdbauto, pycsv) have no fallback when the JSON
  hands them the wrong encoding.
- **Delimiter swaps cleanly bypass parameter-trusting SuTs.** duckdbparse
  and pandas (when its sniffer is suppressed) read everything into one
  giant column.
- **Subtle delimiter mismatches (10–50% mixed) defeat sniffers.** The
  majority bias still picks the dominant delimiter, but every minority
  row gets corrupted (5–50% of records mis-aligned).
- **Combined lies compound.** Stacking encoding + delimiter or
  preamble + header_lies produces close-to-zero scores on multiple SuTs
  simultaneously.
- **Structural lies are silent.** `header_lines: 1` + a 2-row header
  promotes a real data row to a header line, and the SuT reports
  `success=1` while the cell-mapping has shifted by one row.

## Files

- `pollock/polluters_dialect.py` — engine source.
- `data/extended_dialect/csv/` — 41 polluted CSVs.
- `data/extended_dialect/parameters/` — 41 lying parameter JSONs.
- `data/extended_dialect/clean/` — honest clean references for evaluation.
- `results/global_results_extended_dialect.csv` — per-file metrics.
