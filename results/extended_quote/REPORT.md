# Engine B - Quote & Escape Pathologies

**Theme**: RFC 4180 corner cases and underspecified quoting/escape behavior
where parsers diverge.

**Dataset**: `data/extended_quote/` (30 pollutions after round-2 sharpening).

**SuTs evaluated**: `duckdbparse`, `duckdbauto`, `pandas`, `pycsv`.

## Engine summary

| SuT          | mean cell_f1 (round 1) | mean cell_f1 (round 2) | success rate |
|--------------|-----------------------:|-----------------------:|-------------:|
| duckdbparse  |                 0.9601 |             **0.9189** |       0.9667 |
| duckdbauto   |                 0.8859 |             **0.7913** |       1.0000 |
| pandas       |                 0.9192 |             **0.8278** |       0.9000 |
| pycsv        |                 0.8705 |             **0.7352** |       1.0000 |

Round 2 dropped 4 single-row dud attacks (cell_f1 > 0.99 across all SuTs in
round 1), added 8 new high-impact pollutions, and turned several single-row
attacks into multi-row mass attacks. Net: every SuT got 4-13 points worse.

## Top 10 most damaging pollutions (round 2)

Ordered by min cell_f1 across the 4 SuTs (lower = more damage); ties broken
by mean cell_f1.

| # | File | duckdbparse | duckdbauto | pandas | pycsv | min | mean |
|--:|------|------------:|-----------:|-------:|------:|----:|-----:|
| 1 | `quote_char_section.csv`         | **0.000** | 0.552 | **0.000** | **0.000** | 0.000 | 0.138 |
| 2 | `quote_char_dollar.csv`          | 0.698 | 0.552 | 0.672 | **0.000** | 0.000 | 0.480 |
| 3 | `quote_char_pipe.csv`            | 1.000 | 0.412 | 1.000 | **0.000** | 0.000 | 0.603 |
| 4 | `quote_eof_unclosed_ws.csv`      | 0.994 | 0.548 | **0.000** | 0.991 | 0.000 | 0.633 |
| 5 | `quote_eof_quote_then_data.csv`  | 0.994 | 0.548 | **0.000** | 0.991 | 0.000 | 0.633 |
| 6 | `quote_char_caret.csv`           | 1.000 | 0.552 | 1.000 | **0.000** | 0.000 | 0.638 |
| 7 | `quote_char_backtick.csv`        | 1.000 | 0.552 | 1.000 | **0.000** | 0.000 | 0.638 |
| 8 | `quote_char_tilde.csv`           | 1.000 | 0.552 | 1.000 | **0.000** | 0.000 | 0.638 |
| 9 | `quote_char_hash.csv`            | 1.000 | 0.552 | 1.000 | **0.000** | 0.000 | 0.638 |
| 10| `quote_open_header_close_data.csv` | 0.993 | 0.809 | 0.559 | 0.983 | 0.559 | 0.836 |

## Theory of why each top winner breaks each parser

### `quote_char_section.csv` (mean 0.138)
File declares `quotechar="§"` (U+00A7) in the parameters JSON; body bytes
contain only ASCII because the original quoting (`"`) survives in the rendered
CSV.
- **duckdbparse 0.0**: hard-fails because params says quotechar is `§` but the
  source-rendered bytes still encode the file as UTF-8 with NO `§` characters,
  AND duckdbparse uses the declared params strictly with no fallback.
- **pycsv 0.0**: same root cause - csv.reader honors the declared `§` quote
  char, so all the legitimate `"`-quoted fields become unparseable garbage.
- **pandas 0.0**: tokenization error from inconsistent quoting collapses to
  zero rows.
- **duckdbauto 0.55**: salvages partial data because it auto-detects rather
  than trusting the declared quotechar.

### `quote_char_dollar.csv` (mean 0.480)
Quote declared as `$`, which is everywhere in the source (price column has
`$74.69` etc.). Each `$` is now interpreted as a quote delimiter.
- **pycsv 0.0**: csv.reader treats every price as opening a quoted field,
  destroying all subsequent parsing.
- **duckdbparse / pandas ~0.7**: less broken because price column is column
  4/9 - structure beyond it can sometimes be recovered.
- **duckdbauto 0.55**: ignores the declared quotechar and sniffs; partial
  recovery.

### `quote_char_pipe.csv` (mean 0.603)
Pipe declared as quote, but body has no pipes. pycsv (and similar) fails
identically to `_section`.
- **duckdbauto 0.41**: lower than other rare-quote variants because pipe is
  ambiguous with shell-style delimiters - duckdbauto's sniffer picks a
  different (wrong) interpretation here.

### `quote_eof_unclosed_ws.csv` (mean 0.633)
Trailing `"   ` appended to EOF without a close.
- **pandas 0.0**: pandas's C engine encounters an unterminated quoted field
  spanning to EOF and aborts before yielding any rows on this file.
- **pycsv 0.99 / duckdbparse 0.99**: tolerate the trailing junk by silently
  consuming the orphan opening quote.
- **duckdbauto 0.55**: stricter mode flags this as ambiguous and recovers
  partially.

### `quote_eof_quote_then_data.csv` (mean 0.633)
Append `"unfinished cell with content but no close` at EOF. Identical
fingerprint to `_eof_unclosed_ws` because both create a trailing unterminated
quote.

### `quote_char_caret/backtick/tilde/hash.csv`
Same structural attack as `_section`: declare a rare quote char that does NOT
appear in the body, so all real `"`-quoting becomes literal text. Each
parser's behavior matches `_section`. We keep all four because each tests a
different sniffing heuristic (caret/backtick/tilde/hash are all common
"alternative quote chars" some sniffers special-case).

### `quote_open_header_close_data.csv` (mean 0.836)
Inject `"` at end of header line and end of data row 1 - turns the header and
first data row into one giant quoted cell.
- **pandas 0.56**: pandas's C engine joins header+row1 into a single field,
  destroying the column count and cascading downstream.
- **duckdbauto 0.81**: handles header detection differently and salvages most
  data records, but still loses some.
- **duckdbparse / pycsv ~0.99**: less affected because they use the declared
  parameters and don't re-sniff after detecting structural anomalies.

## Strong second-tier attacks

| File | min cell_f1 |
|------|------------:|
| `quote_in_header_only.csv`         | 0.614 |
| `quote_close_then_garbage_many.csv`| 0.728 |
| `quote_every_field_triple_many.csv`| 0.761 |
| `quote_char_apostrophe.csv`        | 0.802 |
| `quote_storm.csv`                  | 0.805 |
| `quote_interlocked_pairs.csv`      | 0.812 |

## Sharpening notes

Round 1 had several single-row attacks that capped out at cell_f1 ~0.99
because only one record was ever wrong. In round 2 we:

1. **Mass-injected** the same pathology across many rows (e.g.
   `_quote_storm` hits every other row 3-49,
   `_close_then_garbage_many_rows` hits 10 rows).
2. **Added more rare-quote-char variants** (`_caret`, `_dollar`, `_hash`,
   `_apostrophe`) - these are nearly free wins for the dataset because pycsv
   in particular fails identically across them.
3. **Added EOF variants** (`_eof_open_long`, `_eof_quote_then_data`) - the
   EOF unclosed-quote pattern was a major pandas killer.
4. **Added header/data ambiguity variants** (`_open_header_close_row5`,
   `_in_header_only`).
5. **Dropped duds**: single-row variants of doubled-quote chains, escape-eats-
   close-quote, lone quote, double-quote-at-field-start, and several others
   that didn't move the needle in round 1.

## Reproducing

```bash
source .venv/bin/activate
python3 pollute_main_extended.py --engine quote --output data/extended_quote --clean
python3 scripts/score_engine.py --dataset extended_quote --top-n 10 \
    --n-reps 1 --n-jobs 4 --purge-loadings --out /tmp/quote_round2.json
```
