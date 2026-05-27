# Engine E — Structural Ambiguity

**Theme.** Pollutions where the file is syntactically well-formed under more
than one plausible dialect interpretation. The benchmark grades against one
specific clean rendering; if a sniffer-driven parser settles on a different
*valid* interpretation it scores 0 on cells even though the answer is sensible.

## Numbers

- **49 pollutions** generated. All filenames start with `struct_`. Largest
  file is 44 KB.
- Closed loop: `pollute_main_extended.py --engine struct` produces
  `data/extended_struct/{csv, clean, parameters}`. `scripts/score_engine.py`
  scores against the four Python SuTs.

### Engine mean cell_f1 per SuT (lower = more attacks landed)

| SuT          | mean cell_f1 | success | wins (cell_f1 < 0.5) | total breaks (cell_f1 = 0) |
|--------------|--------------|---------|----------------------|----------------------------|
| pandas       | 0.688        | 1.000   | 13 / 49              | 7                          |
| duckdbauto   | 0.779        | 0.980   | 7 / 49               | 2                          |
| duckdbparse  | 0.840        | 1.000   | 4 / 49               | 0                          |
| pycsv        | 0.857        | 1.000   | 3 / 49               | 3                          |

The sniffer-driven sut targets (duckdbauto, pycsv, pandas via `engine='c'`)
all have at least one zero-cell-f1 outcome. The schema-explicit duckdbparse
is hardest to break, but two pollutions still get it under 0.21 — both attack
the *header* rather than the dialect.

## Top 5 attacks (lowest mean cell_f1 across the 4 Python SuTs)

| File                                       | mean | duckdbparse | duckdbauto | pandas | pycsv |
|--------------------------------------------|------|-------------|------------|--------|-------|
| struct_single_col_with_caret.csv           | 0.03 | 0.12        | 0.00       | 0.00   | 0.00  |
| struct_single_col_with_tab.csv             | 0.08 | 0.12        | 0.18       | 0.00   | 0.00  |
| struct_single_col_with_commas.csv          | 0.08 | 0.12        | 0.18       | 0.00   | 0.00  |
| struct_header_subset_with_pipe.csv         | 0.52 | 0.60        | 0.60       | 0.20   | 0.69  |
| struct_col_split_more.csv                  | 0.54 | 0.74        | 0.00       | 0.69   | 0.73  |

### Why they work

1. **single_col_with_caret / tab / commas.** The polluted file's first line
   is a single character (`^`, `\t`, or `|`). The rest of the file is
   each row wrapped in one big quoted cell. A sniffer asking "what's the
   delimiter?" sees only the rare char and parses 1 column. The clean
   rendering is the canonical 9-column comma-separated source. → 0 cell_f1
   on every row.
2. **header_subset_with_pipe.** Header line uses `|`, data rows from #40
   onward also use `|`, but rows 1-39 use `,`. Sniffers split on
   majority-vote and pick `|` (because it's used by the header AND a large
   block of data) — but the `,`-rows then under-tokenize.
3. **col_split_more.** Aggressively strips quotes around every short
   comma-bearing string in `ProductType`. duckdbauto's null_padding
   silently expands the row width; the cells line up wrong. clean still
   has the original 9-column layout.

## Pollution catalog (full 49)

### Round 1 — 25 ideas from the brief

| # | File suffix | Mechanism |
|---|-------------|-----------|
| 1 | two_delim_alt | Alternating `,` / `;` per row |
| 2 | two_delim_pipe | Alternating `,` / `\|` per row |
| 3 | var_col_count_5_7 | Bytes-only: every other row truncated to 7 cols |
| 4 | two_tables_no_sep | source.csv concatenated to itself, no separator |
| 5 | two_tables_blank_diff_cols | Blank-row separator + 5-col second table |
| 6 | two_tables_overlap | Second table starts 2 cols in |
| 7 | header_numeric | Header is `1..9` |
| 8 | midfile_header_lookalike | Row 10 looks like a header |
| 9 | reorder_cols_3_4 | Bytes-only: cols 3 & 4 swapped in 10 rows |
| 10 | header_extra_col | Header has 10 cols, data has 9 |
| 11 | empty_leading_col | `,DATE,...` on every row |
| 12 | empty_trailing_col | `...,Comments,` on every row |
| 13 | one_row_extra_col | One row has 10 cols |
| 14 | header_empty_first | First header cell is empty |
| 15 | header_all_duplicates | Every header cell = `DATE` |
| 16 | single_col_with_commas | First line is just `\|`, rows wrapped in quotes |
| 17 | empty_then_header | Blank line at start |
| 18 | empty_middle | Blank line at row 40 |
| 19 | three_empty_middle | 3 blank lines at row 40 |
| 20 | multiline_header_mismatch | 2-row header, 9 then 7 cols |
| 21 | single_string_row | Row 20 has only col 1 with whole content |
| 22 | mixed_trailing_comma | Half rows end with `,`, half don't |
| 23 | col1_unquoted_commas | Date col has `2018, January, N` style values |
| 24 | col_merge_ambiguity | Strip quotes from a few comma-bearing values |
| 25 | undeclared_preamble_4 | 4 unannounced preamble lines |

### Round 2 — sharpened variants

| File suffix | Mechanism |
|-------------|-----------|
| two_delim_block_split | First 30 rows `,`, rest `;` |
| two_delim_tab_block | Last 40+ rows use tab |
| header_only_tabs | Header tabs, data commas |
| empty_first_two_cols | Two phantom leading columns |
| numeric_header_data_swap | Numeric header AND a header-like row at 6 |
| midfile_repeated_header | Header copied at rows 25 and 50 |
| short_rows_5_cols_first_30 | First 30 data rows are 5 cols |
| two_tables_no_sep_xml | Pure XML doubled file (uses `addTable`) |
| reorder_many_rows | Cols 3/4 swapped on every other row |
| col_split_more | Aggressive quote-stripping on comma-bearing values |
| undeclared_preamble_1 | 1 unannounced preamble line |

### Round 3 — sharpened variants based on round 2 results

| File suffix | Mechanism |
|-------------|-----------|
| single_col_with_tab | Single-col trick with tab as marker |
| single_col_with_caret | Single-col trick with `^` as marker |
| header_only_pipe | Header pipes, data commas |
| header_only_semicolon | Header semicolons, data commas |
| two_tables_no_sep_no_header | source twice, second header dropped |
| undeclared_preamble_2 | 2-line preamble |
| undeclared_preamble_metadata | 3-line preamble, last looks like a header |
| col_merge_ambiguity_v2 | More aggressive quote-stripping (32 targets) |
| header_numeric_floats | Header is `1.0..9.0` |
| data_before_header | Inject a fake data row before the real header |
| trailing_partial_row | Append a single-cell footer line |
| preamble_blank_then_data | 3-line preamble + blank + real data |
| header_subset_with_pipe | Header pipes; first 39 rows commas; rest pipes |

## Notes / caveats

- `polluters_base.changeCell` and `addCells` in the upstream stdlib are
  buggy (they reference an undefined `insert_value_cell` and pass wrong
  args to `create_cell`). Engine E does not modify those — it ships drop-in
  equivalents `my_changeCell` / `my_addCells` inside
  `pollock/polluters_struct.py`.
- All raw-byte attacks use `RawBytePolluter`, which keeps the clean output
  honestly rendered from the unmodified XML. Only the on-disk CSV is
  mutated. This is what makes "structural ambiguity" gradeable: the parser
  picks an interpretation, and we measure it against the canonical one.
- We did NOT pursue character-encoding-style attacks (BOMs, mixed UTF-8) —
  those belong to engine `unicode`. Our attacks all live in the dialect
  and table-shape decision space.
