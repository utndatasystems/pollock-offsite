# Extended Pollutions: Final Synthesis Report

## TL;DR

Six attack engines, run in parallel, generated **259 candidate CSV pollutions**. After per-engine closed-loop sharpening and hash-deduped merge, **179 pollutions** were scored against five top-tier parsers (duckdbparse, duckdbauto, pandas, pycsv, clevercs).

The headline benchmark clusters all top parsers at the ceiling (9.18-9.96 / 10). On this adversarial dataset, every parser drops 1.9-4.5 points, and **the leaderboard reorders meaningfully**: pandas (#3 on the headline) collapses to last, while duckdbparse / duckdbauto retain their leadership with a much wider gap above the rest.

| SuT          | Headline (`polluted_files`) | Extended (179 files) | Δ      |
|--------------|----------------------------:|---------------------:|-------:|
| duckdbparse  |                        9.96 |             **8.06** | -1.90  |
| duckdbauto   |                        9.65 |             **6.77** | -2.88  |
| pycsv        |                        9.72 |             **6.05** | -3.67  |
| clevercs     |                        9.19 |             **5.96** | -3.23  |
| pandas       |                        9.88 |             **5.38** | -4.50  |

## How the dataset was built

1. Six engines, each themed on a distinct class of CSV pathology, ran in parallel as autonomous agents.
2. Each engine wrote a Python module (`pollock/polluters_<engine>.py`) with ~25-50 polluter functions and used the new `RawBytePolluter` helper for byte-level attacks the existing XML pipeline can't represent.
3. Each engine ran a closed loop: generate candidates → score against duckdbparse / duckdbauto / pandas / pycsv → identify wins (cell_f1 < 0.5 against any SuT) → generate sharpened variants → re-score.
4. The merge step picked the worst-K=20 pollutions per (engine, SuT) by cell_f1, deduplicated by (csv_bytes, parameters_json) hash, and combined them into `data/extended_pollutions/`.
5. Final scoring: 5 SuTs (above) on the merged dataset via `evaluate.py --dataset extended_pollutions`. Unweighted `pollock_simple` only (the new dataset has no entries in `pollock_weights.json`; `evaluate.py` already gates the weighted path on `dataset == "polluted_files"` so no patch was needed).

## Engine ranking

Mean cell_f1 across all 5 SuTs, lower = engine produced more damaging pollutions:

| Engine     | mean cell_f1 | Best target          |
|------------|-------------:|----------------------|
| **unicode** |        0.346 | pandas (0.115), pycsv (0.184), clevercs (0.196) |
| **lineend** |        0.466 | pandas (0.360), clevercs (0.391) |
| **dialect** |        0.604 | pandas (0.372), duckdbparse (0.575) |
| **struct**  |        0.696 | pandas (0.491), duckdbauto (0.647) |
| **quote**   |        0.801 | pycsv (0.717), duckdbauto (0.777) |
| **typeinfer** |      0.953 | duckdbauto (0.937), pycsv (0.936) |

Two surprises:

- **Unicode is by far the most damaging vector**. Smart quotes, ZWSPs around delimiters, and Unicode line separators (NEL/LS/PS) routinely zero out pandas, pycsv, and clevercs. The mean cell_f1 of 0.115 against pandas is jaw-dropping.
- **Type-inference is the weakest engine in raw damage** (0.953) — but that's misleading: duckdbparse declares all columns as VARCHAR, sidestepping type inference entirely; pandas reads with `dtype=object`; pycsv doesn't infer types at all. The engine still found uniform-cross-SuT hits (European decimal commas: ~0.78 across all 5).

## Top 10 worst-of-the-worst attacks (mean cell_f1 across 5 SuTs)

| Rank | File                                          | mean cell_f1 | duckdbparse | duckdbauto | pandas | pycsv | clevercs | Mechanism |
|---:|-----------------------------------------------|-------------:|------------:|-----------:|-------:|------:|---------:|-----------|
| 1 | `lineend_c1_controls_at_eol.csv`              | 0.005        | 0.024       | 0.000      | 0.000  | 0.000 | 0.000    | C1 control byte before every CRLF — UTF-8 decoders crash, duckdbparse misaligns |
| 2 | `lineend_byte_after_each_crlf.csv`            | 0.009        | 0.024       | 0.024      | 0.000  | 0.000 | 0.000    | 0xFE byte after every CRLF — byte alignment drift |
| 3 | `lineend_fe_plus_nuls.csv`                    | 0.009        | 0.024       | 0.024      | 0.000  | 0.000 | 0.000    | 0xFE-after-CRLF + scattered NULs |
| 4 | `lineend_three_byte_after_crlf.csv`           | 0.009        | 0.024       | 0.024      | 0.000  | 0.000 | 0.000    | 0xFE 0xFF 0x00 sequence after every CRLF |
| 5 | `unicode_zwsp_around_every_delim.csv`         | 0.019        | 0.012       | 0.082      | 0.000  | 0.000 | 0.000    | Zero-width space around every comma — sniffer can't find delimiter |
| 6 | `unicode_rlm_lrm_marks.csv`                   | 0.061        | 0.000       | 0.082      | 0.000  | 0.111 | 0.111    | Right-to-left/left-to-right marks interleaved into header & delimiters |
| 7 | `dialect_encoding_lies_utf8_actual_utf16le.csv` | 0.064      | 0.081       | 0.079      | 0.102  | 0.056 | 0.000    | Parameters say utf-8, file is UTF-16-LE bytes |
| 8 | `dialect_encoding_lies_utf8_actual_utf16be.csv` | 0.065      | 0.081       | 0.086      | 0.103  | 0.056 | 0.000    | Parameters say utf-8, file is UTF-16-BE bytes |
| 9 | `dialect_combo_utf16le_semicolon.csv`         | 0.097        | 0.081       | 0.152      | 0.195  | 0.056 | 0.000    | UTF-16-LE bytes + `;` delimiter, parameters lie about both |
| 10 | `unicode_record_delim_ps.csv`                | 0.116        | 0.024       | 0.555      | 0.000  | 0.000 | 0.000    | U+2029 paragraph separator as record delimiter |

A pattern jumps out: **byte-level attacks that interleave a non-printable byte with each line ending** (entries 1-4) destroy every parser. They survive RFC-4180 validation because the file *is* well-formed CSV — it's just bracketed with bytes that no parser expects to see in that position. pandas and pycsv crash on UTF-8 decode; duckdbparse loads cells but they're all misaligned because the stray byte gets glued onto the first cell of the next row.

## Top 5 worst attacks per SuT

### duckdbparse (the headline leader, hardest to break)

| File | cell_f1 | success | Why |
|---|---:|---:|---|
| `quote_char_section.csv` | 0.000 | 0 | Declares quotechar = `§`; file uses `"`. Parser hard-fails. |
| `unicode_smart_single_quotes.csv` | 0.000 | 0 | Quotechar declared as U+2018; rendering breaks the parser. |
| `unicode_smart_double_quotes.csv` | 0.000 | 0 | Same with U+201C. |
| `unicode_rlm_lrm_marks.csv` | 0.000 | 0 | RTL marks in header & delimiters confuse parsing. |
| `unicode_zwsp_around_every_delim.csv` | 0.012 | 1 | ZWSP around every comma — parser loads, output is shredded. |

### duckdbauto (auto-detection)

| File | cell_f1 | success | Why |
|---|---:|---:|---|
| `lineend_c1_controls_at_eol.csv` | 0.000 | 1 | C1 byte after each CRLF — auto-detect picks wrong record delimiter. |
| `lineend_stray_cr_in_cell.csv` | 0.000 | 0 | Stray CR inside a cell value — record boundary inferred wrong. |
| `lineend_stray_quote_with_lf.csv` | 0.000 | 0 | Stray `"` followed by LF — parser confused about quoting state. |
| `struct_col_split_more.csv` | 0.000 | 0 | Single row has +N columns — auto-detect's column count wrong. |
| `struct_single_col_with_caret.csv` | 0.000 | 1 | Single-column file with `^` separator chosen against ASCII letters. |

### pandas (largest drop overall)

| File | cell_f1 | success | Why |
|---|---:|---:|---|
| `unicode_bom_plus_smart_quotes.csv` | 0.0 | 0 | BOM + smart quotes — encoding mismatch + quote substitution. |
| `dialect_encoding_lies_ascii_actual_cp1252.csv` | 0.0 | 0 | Parameters say ascii, file is cp1252 — `read_csv` raises UnicodeDecodeError. |
| `dialect_encoding_bom_utf8_lies_utf16le.csv` | 0.0 | 0 | Real BOM + lying parameters → decode fails. |
| `dialect_delim_lies_comma_actual_tab.csv` | 0.0 | 1 | Parameters say `,`, file uses `\t` → everything in one column. |
| `dialect_delim_lies_comma_actual_semicolon.csv` | 0.0 | 1 | Same with `;`. |

### pycsv

| File | cell_f1 | success | Why |
|---|---:|---:|---|
| `unicode_bom_plus_smart_quotes.csv` | 0.0 | 0 | BOM + smart quotes. |
| `quote_char_backtick.csv` | 0.0 | 1 | Quotechar declared as `` ` `` — `csv.Sniffer` re-detects ASCII `"` and splits on commas inside fields. |
| `quote_char_caret.csv` | 0.0 | 1 | Same with `^`. |
| `quote_char_dollar.csv` | 0.0 | 1 | Same with `$` (collides with prices). |
| `quote_char_hash.csv` | 0.0 | 1 | Same with `#`. |

The pycsv pattern: when the declared quotechar isn't actually used in the file (because all our quoting still uses `"`), `csv.Sniffer().sniff()` ignores the declaration and re-infers a different dialect, which then mangles fields containing commas.

### clevercs

| File | cell_f1 | success | Why |
|---|---:|---:|---|
| `unicode_bom_plus_smart_quotes.csv` | 0.0 | 0 | Encoding crash. |
| `unicode_zwsp_around_every_delim.csv` | 0.0 | 0 | ZWSP defeats sniffer. |
| `dialect_encoding_lies_utf8_actual_utf16le.csv` | 0.0 | 0 | Encoding lies → decode fails. |
| `dialect_encoding_lies_utf8_actual_utf16be.csv` | 0.0 | 0 | Same. |
| `dialect_encoding_lies_utf8_actual_big5.csv` | 0.0 | 0 | Same. |

## Cross-cutting findings

1. **Unicode is the biggest unfilled hole in the headline benchmark.** The existing `polluters_stdlib.py` only changes encoding via `changeEncoding` and assumes the parameters JSON tells the truth about it. Real-world CSV breakage from BOMs, smart quotes, NEL/LS/PS line separators, and zero-width Unicode is not represented at all in the headline 9.96 / 10 numbers.

2. **The "auto" parsers fail differently than the "dialect-using" parsers.** Sniffer-driven SuTs (duckdbauto, pycsv, clevercs) fall to dialectal trickery (single-column files, weird delimiters, structural ambiguity). Dialect-using SuTs (duckdbparse, pandas) fall to encoding/quotechar lies. Different attack vectors expose different failure modes — the engines confirm this cleanly.

3. **`success=1` cell_f1=0 cases are the most insidious.** Many of these attacks don't crash the parser; they produce a fully-loaded but completely wrong CSV. From the parser's perspective the file looks fine. This silent-corruption pattern is what makes the new dataset more valuable than the headline one for production-readiness assessment.

4. **Duckdbparse's `auto_detect=False` defense is a strong moat.** Compared to duckdbauto (which drops 2.88), duckdbparse drops only 1.90 — explicit dialect declaration absorbs a lot of damage. But it's not impervious: encoding lies (Engine F) and Unicode quote substitutions (Engine A) still find purchase.

5. **Pandas's encoding-strictness hurts it.** Many of the pandas-zero results aren't logical errors — they're `UnicodeDecodeError` exceptions from `read_csv`. With `errors='replace'` or a more forgiving encoding strategy, pandas would likely score significantly better. This is more of a configuration trap than a parser weakness.

## Reproducibility

To regenerate the dataset and re-score from scratch:

```bash
# Activate venv (only once per shell)
source .venv/bin/activate

# Per-engine generation + closed-loop scoring (parallelizable)
for engine in unicode quote typeinfer lineend struct dialect; do
    python3 pollute_main_extended.py --engine $engine \
        --output data/extended_$engine --clean
    python3 scripts/score_engine.py --dataset extended_$engine \
        --top-n 10 --n-reps 1 --n-jobs 4 \
        --out /tmp/${engine}_round.json
done

# Merge winners (top-20 per engine x SuT, deduped on csv+params hash)
python3 scripts/merge_engines.py \
    --engines unicode quote typeinfer lineend struct dialect \
    --top-k 20 --clean-out

# Run the SuTs on the merged set
DATASET=extended_pollutions N_REPETITIONS=1 \
    bash scripts/run_python_suts.sh extended_pollutions \
        duckdbparse duckdbauto pandas pycsv clevercs

# Score
python3 evaluate.py --dataset extended_pollutions --njobs 8

# Inspect the per-file CSV
ls results/global_results_extended_pollutions.csv
ls results/aggregate_results_extended_pollutions.csv
```

## Per-engine artifacts

Each engine wrote its own report:

- `pollock/polluters_unicode.py` & `results/extended_unicode/REPORT.md` — 36 pollutions
- `pollock/polluters_quote.py` & `results/extended_quote/REPORT.md` — 30 pollutions
- `pollock/polluters_typeinfer.py` & `results/extended_typeinfer/REPORT.md` — 57 pollutions
- `pollock/polluters_lineend.py` & `results/extended_lineend/REPORT.md` — 46 pollutions
- `pollock/polluters_struct.py` & `results/extended_struct/REPORT.md` — 49 pollutions
- `pollock/polluters_dialect.py` & `results/extended_dialect/REPORT.md` — 41 pollutions

## Notes on infrastructure

- Two upstream bugs in `pollock/polluters_base.py` were noticed by Engines C and E (`changeCell` calls undefined `insert_value_cell`; `addCells` passes wrong args to `create_cell`). Engines worked around them by writing local re-implementations inside their own modules. Worth fixing upstream — these helpers are useful primitives that other future engines (or contributions to the headline benchmark) would want to use.
- `sut/clevercs/clevercs.py` had a NameError in its error path (`del dialect` fires even when sniff threw before binding `dialect`). Fixed in this work to enable clevercs scoring on the extended dataset.
- `pollock/polluters_extended.py::RawBytePolluter` is the new shared scaffolding all six engines used. It runs the standard `write_clean_csv` + `write_parameters` pipeline on the un-mutated CSVFile, then mutates the rendered bytes — letting byte-level attacks coexist with the existing XML-based polluters.

## Limitations &amp; caveats

- The closed loop for each engine ran on Python SuTs only (~seconds per file). Docker SuTs (mariadb, sqlite, etc.) were not in scope per the user's "Python + clevercs" choice. Some attacks may be more or less effective against database CSV importers; that would be a follow-up.
- `pollock_weighted` is not computed for this dataset — there are no entries in `pollock_weights.json`, and weighted scoring is meaningless for an exploratory adversarial set anyway. All comparisons here use the unweighted `pollock_simple` (sum of 10 metrics, max = 10.0).
- The dataset was deliberately seeded toward differential damage: pollutions that 100% crash every parser were filtered out (they don't discriminate). Pollutions that score 1.0 across all parsers were also filtered out (they're not attacks). The mid-band where one parser fails but another succeeds is what makes this useful as a benchmark.
- 36 of the 179 promoted pollutions are Unicode-themed; if you're more interested in a broader category mix, re-run merge with a smaller `--top-k` and wider engine coverage.
