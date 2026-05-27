# Engine D — Line-ending and record-delimiter chaos

Pollutions that exploit parser disagreement on what constitutes a record
boundary: mixed line endings within one file, embedded delimiters in quoted
fields, NUL bytes, form feeds, trailing whitespace, missing/extra terminators,
unicode line separators, and compound byte-level injections at EOL.

All 46 attacks emit a polluted CSV but write an honest `clean/` reference and
`parameters/` JSON declaring `\r\n` as the record delimiter — so the parser
gets no signal that the line endings are weird, which is what makes most of
these land hardest.

## Engine summary

- Total pollutions: **46**
- Pollutions causing `cell_f1 < 0.5` on at least one Python SuT: **19**

### Mean cell_f1 per SuT (lower is better for the attacker)

| SuT          | mean cell_f1 | wins (cell_f1 < 0.5) |
|--------------|--------------|----------------------|
| duckdbparse  | 0.751        | 10 / 46              |
| duckdbauto   | 0.744        |  7 / 46              |
| pandas       | 0.648        | 15 / 46              |
| pycsv        | 0.701        | 12 / 46              |

`pandas` and `pycsv` were the most fragile against byte-level chaos at line
boundaries. `duckdbparse` resisted most attacks at the cell level (it tends
to recover full cells even when records are misaligned) but fails badly on a
tight cluster of replacement-record-delimiter attacks.

## Top 5 attacks (by total damage across all 4 Python SuTs)

| # | Filename                              | duckdbparse | duckdbauto | pandas | pycsv |
|---|---------------------------------------|-------------|------------|--------|-------|
| 1 | `lineend_c1_controls_at_eol.csv`      | 0.02        | 0.00       | 0.00   | 0.00  |
| 2 | `lineend_three_byte_after_crlf.csv`   | 0.02        | 0.02       | 0.00   | 0.00  |
| 3 | `lineend_fe_plus_nuls.csv`            | 0.02        | 0.02       | 0.00   | 0.00  |
| 4 | `lineend_byte_after_each_crlf.csv`    | 0.02        | 0.02       | 0.00   | 0.00  |
| 5 | `lineend_ps_record_delim.csv`         | 0.02        | 0.55       | 0.00   | 0.00  |

(Lower = parser produced fewer correct cells.)

## Why the winners win

1. **`c1_controls_at_eol`** — random C1 control byte (0x80-0x9F) injected
   immediately before each `\r\n`. UTF-8 decoders in pandas and pycsv abort
   the whole file on the invalid first byte; duckdb succeeds at file level
   but fails at record/cell level because the corrupted byte glues a row
   onto the next.

2. **`three_byte_after_crlf` (0xFE 0xFF 0x00)** and **`byte_after_each_crlf`
   (0xFE)** — placing a single non-CR/LF/printable byte right after every
   CRLF causes the parser to treat the trailing byte as the leading byte of
   the next field. Combined with NUL (`fe_plus_nuls`) the byte stream looks
   like garbage to anything that decodes UTF-8 strictly.

3. **`ps_record_delim` / `nel_record_delim`** — replacing `\r\n` with the
   UTF-8 encoding of U+2029 (Paragraph Separator) or U+0085 (NEL). The file
   has zero CR or LF anywhere, but the parameters JSON declares `\r\n`. Most
   parsers either read the whole file as a single record or crash on the
   multi-byte sequence.

4. **`half_ls_separator`, `interleave_ls_ps_crlf`** — half/cycling the file
   between CRLF and U+2028/U+2029. Mixed terminators inside a "normal-looking"
   file cause record alignment to drift midway through.

5. **`random_c1_throughout`, `c1_mid_cell`, `nel_inside_cells`** — C1
   bytes embedded mid-cell (away from EOL). pandas and pycsv abort on the
   bad UTF-8; duckdb keeps cells but the embedded bytes drop precision.

## Other notable hits

- `eof_mid_cell` — last row truncated mid-cell: pandas crashes (success=0).
- `stray_cr_in_cell`, `stray_quote_with_lf` — kill duckdbauto's auto-detection
  pipeline (success=0).
- `bom_after_each_crlf` — UTF-8 BOM after every CRLF: parsers strip BOM at
  file start only, mid-stream BOMs become garbage.
- `vt_as_record_delim` / `ff_as_record_delim` / `double_ff_delim` — declaring
  a non-printable as record delimiter always tanks duckdbparse.

## Methodology notes

- Source: `results/source.csv` (84 rows, 9 columns).
- All pollutions implemented in `pollock/polluters_lineend.py` exclusively
  via `RawBytePolluter` so the polluted bytes diverge from the honest
  `clean/` reference and the parameters JSON.
- Round 1 produced 36 pollutions; round 2 added 10 sharpened compound
  attacks based on round-1 wins (compound `0xFE + NULs`, mid-cell C1
  injection, BOM-after-CRLF, etc).
- Generation: `python3 pollute_main_extended.py --engine lineend
  --output data/extended_lineend --clean`.
- Scoring: `python3 scripts/score_engine.py --dataset extended_lineend
  --top-n 10 --n-reps 1 --n-jobs 4 --purge-loadings`.
- All output files < 25 KB; full dataset is well under the 5 MB budget.
