# Pollock Offsite

Pollock Offsite provides the CSV Storm benchmark: a dataset of corrupted CSV
files generated with Pollock 2.0 and curated pollution combinations. It runs
CSV parsers (systems under test, or SUTs) and compares their reconstructed
output with known clean data. The repository includes conventional CSV parsers
and two LLM-based parser architectures.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Commands below assume you are in the repository root with the virtual
environment activated.

## Run a Benchmark

The repository includes CSV Storm under `data/csv_storm/`. Run the included
Python-only SUTs against it, then evaluate them:

```bash
scripts/run_python_suts.sh csv_storm duckdbauto duckdbparse pandas pycsv clevercs
.venv/bin/python evaluate.py --dataset csv_storm
```

To run a smaller selection:

```bash
scripts/run_python_suts.sh csv_storm duckdbauto clevercs
```

Docker-based SUTs can be run with `bash benchmark.sh`. Edit `benchmark.sh` to
disable systems you do not need; the first run may take a while because it
builds several images.

### Generate a Dataset

Download the prepared CSV Storm dataset:

> <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" alt="Hugging Face" width="20" height="20"> **Dataset download:** [CSV Storm on Hugging Face — link to be added](https://huggingface.co/datasets/REPLACE_WITH_ORGANIZATION/REPLACE_WITH_DATASET)

Alternatively, generate CSV Storm locally with Pollock 2.0 and the curated
pollution combinations:

```bash
.venv/bin/python pollute_main.py \
  --source ./results/source.csv \
  --output ./data/csv_storm \
  --polluters pollock2.0 \
  --combinations \
  --overwrite
```

Each dataset contains polluted input in `csv/`, expected output in `clean/`,
dialect metadata in `parameters/`, and alternative valid interpretations in
`ground_truth/` where a corruption is ambiguous.

## Run the LLM Parsers Locally

Install [Ollama](https://ollama.com/), start `ollama serve` in another terminal,
and download the model:

```bash
ollama pull qwen3.5:0.8b
```

Run both parser architectures on CSV Storm:

```bash
DATASET=csv_storm .venv/bin/python sut/full_llm_loader/custom-bench.py \
  --backend ollama --model qwen3.5:0.8b --overwrite

DATASET=csv_storm .venv/bin/python \
  sut/llm_hybrid_parser_Robin/llm-hybrid-bench.py \
  --backend ollama --model qwen3.5:0.8b --overwrite
```

Append `--file file_field_delimiter_0x3B.csv` for a quick smoke test or
`--verbose` to inspect prompts and responses. Use `--api-base` if Ollama is not
available at `http://localhost:11434/v1`.

Evaluate the results:

```bash
.venv/bin/python evaluate.py \
  --sut full_llm_loader_naive_qwen3_5_0_8b --dataset csv_storm
.venv/bin/python evaluate.py \
  --sut llm_hybrid_parser_qwen3_5_0_8b --dataset csv_storm
```

### CSV Storm Results

<!-- CSV_STORM_RESULTS_START -->
| Parser | Model | Exact file matches | Accuracy |
| --- | --- | ---: | ---: |
| Full LLM (naive) | `qwen3.5:0.8b` | 0/68 | 0.0% |
| Hybrid | `qwen3.5:0.8b` | 21/68 | 30.9% |
<!-- CSV_STORM_RESULTS_END -->

A file is correct only when its complete evaluated output matches an accepted
ground truth. Refresh this table after rerunning the parsers:

```bash
.venv/bin/python scripts/update_readme_csv_storm_results.py
```

## Add a Parser

Use `sut/custom_template/` as a starting point for a new SUT. Parsers read from
`data/<dataset>/csv/` and write normalized CSV files to
`results/<sut>/<dataset>/loading/`; select a dataset with
`DATASET=<dataset_name>`.

## Evaluation

```bash
.venv/bin/python evaluate.py --sut <sut> --dataset <dataset>
```

Omit `--sut` to evaluate every SUT with output for that dataset. One invocation
calculates strict whole-file accuracy and Pollock's loading success, precision,
recall, F1, and combined scores. It writes:

- per-file results to `results/<sut>/<dataset>/<sut>_results.csv`;
- a dataset summary to `results/evaluation_summary_<dataset>.csv`; and
- cross-SUT results to `results/evaluation_by_file_<dataset>.csv`.

Pollock's combined score is the sum of mean success and the mean precision,
recall, and F1 values for headers, records, and cells. Its maximum is 10.
Weighted scores use pollution frequencies from a government CSV survey and are
only comparable for datasets generated from `results/source.csv`.

To inspect parsing errors:

```bash
.venv/bin/python eval/find_errors.py --sut <sut>
```

## Paper

> **Publication:** [Pollock Offsite paper — link to be added after submission](https://doi.org/REPLACE_WITH_DOI)
