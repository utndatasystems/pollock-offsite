# PAPER_NUMBERS — CSVStorm reruns for the camera-ready (GPT-5.6 / GPT-5.4 Mini / Qwen3.5 0.8B)

All runs in this folder were made on 2026-11-27 on branch `old_models_submission_code`,
which starts from the submission commit `251c9f8ee` (Aug 4, 2026) and changes only:

| Commit | Change |
|---|---|
| `5614f5cb4`, `33a3198d4` | Code generation: output limit 4096 → 12288 tokens; sandbox allows the missing side-effect-free builtins (`map`, `filter`, `frozenset`, `__build_class__`, `OverflowError`, `bytes`, …) |
| `868a9b536` | `.gitignore`: keep the code-generation sidecars (`*.llm.jsonl`, which hold the generated programs) |
| `2810e0992` | `custom-bench.py` of code generation: add the missing `import pandas as pd` (commit `52916fb41` broke the per-file time CSV; parser behaviour unchanged) |
| uncommitted at the time of writing | sandbox also allows `object` (see "Replay" below) |

Dataset: `data/csv_storm` (69 files: 68 polluted + `source.csv`). Evaluation: `evaluate.py --dataset csv_storm --sut <sut>`.

## What was rerun and why

| SUT | Why | Cache hits |
|---|---|---|
| `llm_hybrid_parser_{gpt_5_6_sol,gpt_5_6_luna,gpt_5_4_mini,qwen3_5_0_8b}_duckdb` | The submission runs of the DuckDB-sniff hybrid were almost entirely served from the response cache, so their timings were meaningless. Rerun with `--overwrite` (cache off). | 0 |
| `full_llm_loader_naive_gpt_5_6_luna` | Missing from Table 1. | not recorded by this script; started with an empty cache |
| `code_generation_llm_{gpt_5_6_sol,gpt_5_6_luna,gpt_5_4_mini,qwen3_5_0_8b}` | Submission failures were artefacts: Sol 22 × empty response (4096-token limit used up by reasoning), Luna 11 × quota exceeded (HTTP 429), sandbox missing harmless builtins. | 16 per model: files whose prompt is identical to another file's in the same run (same behaviour as the submission code) |
| `full_llm_loader_naive_qwen3_5_0_8b` | Missing from Table 1. The submission artefact `full_llm_loader_naive_qwen3_4_0_8b` is unusable: wrong model name, sent to the OpenAI endpoint, 69 × HTTP 404. | not recorded by this script; started with an empty cache |

Qwen runs (code generation, hybrid, full agentic) ran on the GPU machine via Ollama; all GPT runs via the OpenAI API.

### Replay (no LLM calls)
After the code-generation runs, `object` was added to the sandbox allowlist and every saved program
(sidecars) of all four code-generation SUTs was re-executed. A control replay with the previous sandbox
reproduced every output byte for byte (except Qwen's `file_num_columns_pad_randints_1000.csv`, which has no
program: prompt longer than the model's context). With `object`, exactly one file changed:
`code_generation_llm_gpt_5_6_sol` / `file_embedded_json_cell_2_1_len_4.csv` (crash → correct table).
Its output, malformed report and time-CSV row (`success_0`, `error_0`; `time_0` kept) were replaced.

## Numbers

SuT Success [%] / Pollock score / Accuracy [%], from `evaluation_summary_csv_storm.csv` in this folder.

### Table 1 — rows that change

The hybrid in the camera-ready is the **DuckDB-sniff** variant (`llm_hybrid_parser_<model>_duckdb`).
The submission's Table 1 showed the LLM-sniff-only variant; that variant is not part of this folder.

| Architecture | Model | Submission (paper) | Now |
|---|---|---|---|
| Hybrid | GPT-5.6 Sol | 100.0 / 9.94 / 82.6 | **100.0 / 9.94 / 84.1** |
| Hybrid | GPT-5.6 Luna | 100.0 / 9.71 / 73.9 | **100.0 / 9.93 / 79.7** |
| Hybrid | GPT-5.4 Mini | 94.2 / 9.23 / 63.8 | **100.0 / 9.82 / 68.1** |
| Hybrid | Qwen3.5 0.8B | 100.0 / 7.53 / 27.5 | **97.1 / 8.15 / 30.4** |
| Full Agentic | GPT-5.6 Luna | — | **89.9 / 8.67 / 59.4** |
| Full Agentic | Qwen3.5 0.8B | — | **26.1 / 1.79 / 4.3** |
| Custom Parser Code | GPT-5.6 Sol | 68.1 / 6.71 / 44.9 | **100.0 / 9.82 / 75.4** |
| Custom Parser Code | GPT-5.6 Luna | 79.7 / 7.75 / 49.3 | **98.6 / 9.70 / 59.4** |
| Custom Parser Code | GPT-5.4 Mini | 95.7 / 8.46 / 34.8 | **97.1 / 8.44 / 34.8** |
| Custom Parser Code | Qwen3.5 0.8B | 0.0 / 0.00 / 0.0 | **8.7 / 0.42 / 1.4** |

### Table 2 — runtime and cost of the hybrid (DuckDB sniff, cold reruns)
Time: `time_0` over all 69 files (no cache hits). Cost recomputed from the token columns of the time CSVs
with the prices of the submission notebook (`eval/notebooks/error_statistics.ipynb`, cell 18; USD per 1M
input / cached input / output tokens): Sol 5.00 / 0.50 / 30.00, Luna 1.00 / 0.10 / 6.00, Mini 0.75 / 0.075 / 4.50.

| Model | Acc. (%) | Time median (s/file) | Time total (s) | Cost median ($/file) | Cost total ($) |
|---|---|---|---|---|---|
| GPT-5.6 Sol | 84.1 | 3.43 | 644.76 | 0.0173 | 3.5763 |
| GPT-5.6 Luna | 79.7 | 6.10 | 964.33 | 0.0050 | 0.8392 |
| GPT-5.4 Mini | 68.1 | 1.85 | 387.23 | 0.0024 | 0.5621 |
| Qwen3.5 0.8B | 30.4 | 0.65 | 454.82 | Local | Local |

## Caveats
- **Prices:** all GPT-5.6 Luna prices on this branch are fixed to the pre-July-30 list (1.00 / 0.10 / 6.00 USD per 1M tokens), in `sut/llm_hybrid_parser/llm.py`, `sut/full_llm_loader/llm_utils.py` and the notebook. The Luna hybrid rerun originally ran with the July-30 price (0.20 / 0.02 / 1.20); its cost columns were recomputed from the recorded tokens with the pre-July-30 price.
- **Paper vs. committed summary:** some unchanged rows in the paper differ slightly from the committed evaluation summary (e.g. DuckDB Parse 40.6 vs 43.5, Pandas 33.3 vs 34.8). The paper table was built from an earlier evaluation; these SUTs were not rerun.
- **Code-generation timings:** the 16 cache-hit files per model take ~0 s; the time totals include them as zeros.
- Hybrid DuckDB: all three GPT models hit a DuckDB strict-mode error on `file_unescaped_multiline_string_row_2_col_7.csv` and fall back to non-strict parsing (parser behaviour, not an API error). Qwen hybrid: one HTTP 400 (prompt longer than context) on `file_num_columns_pad_randints_1000.csv`.
- No run hit a quota, rate limit, authentication, server or connection error. Remaining failures are method or model limits: context length (Qwen code generation 1, Qwen hybrid 1, full agentic Luna 1, full agentic Qwen 2), output-token limit 16000 (full agentic Luna 1, full agentic Qwen 39), Qwen repetition abort (hybrid 1, HTTP 500 "token repeat limit reached"), generated-parser timeouts (Qwen code generation 2), and unparseable or wrong outputs.

## Folder layout
- `logs/<sut>.log` — console log of each rerun.
- `results/<sut>/` — `<sut>_time.csv` (per-file time, success, error, tokens, cost) and `<sut>_results.csv` (per-file evaluation) of each rerun.
- `evaluation_summary_csv_storm.csv`, `evaluation_by_file_csv_storm.csv` — evaluation of all SUTs at the time of writing.
- Full outputs, sidecars and caches stay in `results/<sut>/csv_storm/` of this branch.
