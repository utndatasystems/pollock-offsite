# PAPER_NUMBERS — CSVStorm (camera-ready)

### Table 1 — CSVStorm results

| Architecture | System | SuT Success [%] | Pollock Score | Accuracy [%] |
|---|---|---|---|---|
| Hybrid | GPT-5.6 Sol | 100.0 | 9.94 | 84.1 |
| Hybrid | GPT-5.6 Luna | 100.0 | 9.93 | 79.7 |
| Hybrid | GPT-5.4 Mini | 100.0 | 9.82 | 68.1 |
| Hybrid | Qwen3.5 0.8B | 97.1 | 8.15 | 30.4 |
| Full Agentic | GPT-5.6 Sol | 98.6 | 9.57 | 73.9 |
| Full Agentic | GPT-5.6 Luna | 89.9 | 8.67 | 59.4 |
| Full Agentic | GPT-5.4 Mini | 53.6 | 5.21 | 37.7 |
| Full Agentic | Qwen3.5 0.8B | 26.1 | 1.79 | 4.3 |
| Custom Parser Code | GPT-5.6 Sol | 100.0 | 9.82 | 75.4 |
| Custom Parser Code | GPT-5.6 Luna | 98.6 | 9.70 | 59.4 |
| Custom Parser Code | GPT-5.4 Mini | 97.1 | 8.44 | 34.8 |
| Custom Parser Code | Qwen3.5 0.8B | 8.7 | 0.42 | 1.4 |
| Baselines | CleverCSV | 100.0 | 8.67 | 55.1 |
| Baselines | DuckDB Parse* | 100.0 | 9.31 | 43.5 |
| Baselines | DuckDB Auto | 98.6 | 8.21 | 34.8 |
| Baselines | PyCSV | 98.6 | 8.76 | 10.1 |
| Baselines | Pandas* | 98.6 | 8.08 | 34.8 |

\* oracle-assisted parsing. Hybrid = `llm_hybrid_parser_<model>_duckdb`; DuckDB Auto = `duckdbauto_strict`.

### Table 2 — runtime and cost of the hybrid

| Model | Acc. (%) | Time median (s/file) | Time total (s) | Cost median ($/file) | Cost total ($) |
|---|---|---|---|---|---|
| GPT-5.6 Sol | 84.1 | 3.43 | 644.76 | 0.0173 | 3.5763 |
| GPT-5.6 Luna | 79.7 | 6.10 | 964.33 | 0.0050 | 0.8392 |
| GPT-5.4 Mini | 68.1 | 1.85 | 387.23 | 0.0024 | 0.5621 |
| Qwen3.5 0.8B | 30.4 | 0.65 | 454.82 | Local | Local |

### Reproducing the full evaluation
All outputs behind these numbers are in commit `8ab20ac36` of branch `old_models_submission_code`
(`results/<sut>/csv_storm/`). From the repository root, this prints every metric per SUT (SuT success,
Pollock simple/weighted, cell/record/header F1, accuracy, correct/wrong) and rewrites the summary CSVs
in `results/`; it also lists the LLM-sniff-only hybrids, which are not part of the paper:

```bash
python3 evaluate.py --dataset csv_storm --cached-only   # re-aggregate the stored per-file results
python3 evaluate.py --dataset csv_storm --sut <sut>     # re-evaluate one SUT from its outputs
```

`evaluate.py` prints the `success` column from the commit after `8ab20ac36` on.
