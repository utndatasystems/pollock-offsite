# Extended Typeinfer Engine — Report

## Engine theme
**Type-inference & sniffer traps.** Pollutions targeted at parsers that
infer column types (and column count) from a sample window. The duckdbauto
SuT restricts `auto_type_candidates` to `['NULL','BOOLEAN','BIGINT','DOUBLE','VARCHAR']`
to dodge a known TIMESTAMP write bug; this engine attacks that defense and
the broader sniffer surface in pandas (delimiter=None auto-detect) and
pycsv (Sniffer().sniff() dialect detection).

## Summary

- **Total pollutions:** 57 (round 1: 42, round 2: +15 sharpened entries)
- **All 57 generate cleanly** (no skips/errors during pollution)
- **All 57 produce a successful loading on every Python SuT** (success=1.0
  across the board — no application errors)

### Engine mean cell_f1 per Python SuT (round 2)

| SuT          | mean cell_f1 | mean record_f1 | mean header_f1 |
|--------------|--------------|-----------------|-----------------|
| duckdbparse  | 0.977        | 0.894           | 1.000           |
| duckdbauto   | **0.957**    | **0.717**       | 0.996           |
| pandas       | 0.972        | 0.892           | 1.000           |
| pycsv        | 0.956        | 0.813           | 0.982           |

duckdbauto and pycsv are the most affected on cell_f1; duckdbauto loses the
most on record_f1 because the late-row anomalies promote whole columns to
DOUBLE (every `2` becomes `2.0`), which doesn't match the raw integer in
the source on multiset comparison.

duckdbparse remains highly resilient (everything is VARCHAR up front), but
column-shifting attacks via unquoted commas still wound it because pollock's
metric is on cells, not types — column shift moves cell content to a
different position, breaking record-level matches.

## Top 5 attacks (by lowest cell_f1)

Below are the worst pollutions per SuT — the ones that most successfully
defeated each parser. (Lower cell_f1 = stronger attack.)

### duckdbauto (the primary target)
| File | cell_f1 | record_f1 |
|------|---------|-----------|
| `typeinfer_qty_all_unquoted_thousands.csv` | 0.772 | 0.000 |
| `typeinfer_price_all_unquoted_eu.csv` | 0.772 | 0.000 |
| `typeinfer_price_european_decimal.csv` | 0.775 | 0.012 |
| `typeinfer_url_all_unquoted_csv_fragment.csv` | 0.794 | 0.000 |
| `typeinfer_producttype_all_unquoted_comma.csv` | 0.800 | 0.000 |

### pandas
| File | cell_f1 | record_f1 |
|------|---------|-----------|
| `typeinfer_producttype_all_unquoted_comma.csv` | 0.671 | 0.000 |
| `typeinfer_url_all_unquoted_csv_fragment.csv` | 0.671 | 0.000 |
| `typeinfer_price_all_unquoted_eu.csv` | 0.780 | 0.000 |
| `typeinfer_qty_all_unquoted_thousands.csv` | 0.780 | 0.000 |
| `typeinfer_comments_all_unquoted_two_values.csv` | 0.780 | 0.000 |

### pycsv
| File | cell_f1 | record_f1 |
|------|---------|-----------|
| `typeinfer_url_whitespace_only.csv` | **0.003** | 0.000 |
| `typeinfer_url_all_unquoted_csv_fragment.csv` | 0.795 | 0.000 |
| `typeinfer_producttype_all_unquoted_comma.csv` | 0.800 | 0.000 |
| `typeinfer_qty_all_unquoted_thousands.csv` | 0.836 | 0.000 |
| `typeinfer_price_all_unquoted_eu.csv` | 0.836 | 0.000 |

### duckdbparse
| File | cell_f1 | record_f1 |
|------|---------|-----------|
| `typeinfer_producttype_all_unquoted_comma.csv` | 0.671 | 0.000 |
| `typeinfer_qty_all_unquoted_thousands.csv` | 0.780 | 0.000 |
| `typeinfer_price_all_unquoted_eu.csv` | 0.780 | 0.000 |
| `typeinfer_url_all_unquoted_csv_fragment.csv` | 0.780 | 0.000 |
| `typeinfer_price_european_decimal.csv` | 0.783 | 0.012 |

## Notable findings

### 1. The `pycsv` whitespace-only column kill
`typeinfer_url_whitespace_only.csv` is by far the most destructive attack on
pycsv: cell_f1 drops to **0.003**, header_f1 to 0. Whitespace-only column
content confuses `csv.Sniffer().sniff()` so badly the dialect detection
reports a different delimiter, and the file is parsed as one long row.

### 2. Column-shifting via unquoted commas is the universal damage vector
The strongest cross-SuT attacks all share the same pattern: replace a
column's value across all rows with an unquoted comma-bearing string
(`"1,000"` in Qty, `"74,69"` in Price, `"a,b,c"` in URL/ProductType).
The clean output is properly quoted (so the metric expects N columns),
but the polluted file's parser sees N+1 or N+2 columns, scrambling
everything to the right.

### 3. duckdbauto's late-row type promotion is exposed
With `auto_type_candidates=['NULL','BOOLEAN','BIGINT','DOUBLE','VARCHAR']`,
late-row anomalies in Qty (`1e308`, `99...99`, `-1e9999`) force the entire
column from BIGINT→DOUBLE. Result: every `2` becomes `2.0` in the loaded
output, which doesn't match `2` on multiset comparison → cell_f1 ≈ 0.88
just from that single column flip. Six pollutions land in this bucket
(`qty_late_overflow`, `qty_late_huge_float`, `qty_late_inf`,
`qty_late_negative`, `mega_late_currency_overflow_eu`, `qty_denormal_floats`).

### 4. The European decimal classic still works
`typeinfer_price_european_decimal.csv` (rewriting `$74.69` → `74,69`) is the
single attack that hurts ALL four SuTs (cell_f1 0.78 across the board) —
no auto_type_candidates restriction can save you from a column shift.

### 5. URL → URL-as-numbers does not phase pandas/duckdb
`typeinfer_url_unix_timestamps.csv` (replace all URLs with timestamps) and
`typeinfer_url_as_booleans.csv` lose only single-digit-percent on cell_f1
because pandas reads with `dtype=object` (everything is string anyway) and
duckdbparse uses VARCHAR. Type-inference attacks on the URL column are
mostly absorbed.

## Pollution catalog (selected highlights)

The full list lives in `pollock/polluters_typeinfer.py`. Categories:

1. **Sample-window evasion** — clean prefix, late-row anomalies (`qty_late_*`)
2. **Currency / locale / decimal-separator confusion**
   (`price_european_decimal`, `qty_thousands_separator`)
3. **Pseudo-types** — booleans/dates/numbers in wrong columns
4. **Numeric edge values** — Inf, NaN, hex/octal, denormals
5. **Type-confusable cells** — scientific notation, dates as ints
6. **Null-flavor proliferation** — NULL/null/N/A/None/--
7. **Whitespace-only and column-shift** — the strongest payloads
8. **Whole-column type flips** — every Qty becomes 0/1, every PRODUCTID
   becomes a float, every Price loses `$`

## How to reproduce

```bash
source .venv/bin/activate
python3 pollute_main_extended.py --engine typeinfer \
        --output data/extended_typeinfer --clean
python3 scripts/score_engine.py --dataset extended_typeinfer \
        --top-n 10 --n-reps 1 --n-jobs 4 --out /tmp/typeinfer.json
```
