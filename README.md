# CSV Storm

A benchmark for agentic CSV loading and reconstruction.

CSV Storm generates datasets containing deliberately corrupted CSV files alongside corresponding ground-truth data.
It evaluates systems under test by comparing their reconstructed outputs against the automatically generated ground truth files.

The repository includes conventional CSV parsers as well as three LLM-based parsing architectures.

## Setup


```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Commands below assume you are in the repository root with the virtual
environment activated.


## Run the whole Benchmark start to finish

Needs:
- environment variable `OPENAI_API_KEY`
- local Ollama instance with Qwen3.5 0.8B  hosted (see further instructions below)

**!WILL INCUR MONETARY COST FROM API CALLS!**

```
bash scripts/run_full_benchmark_on_csvstorm.sh --regenerate --confirm-cost
```

or to just run the classical baselines without LLM-Calls:

```
bash scripts/run_classical_baselines_on_csvstorm.sh --regenerate
```


## Access or generate the CSV Storm dataset

(automatically done by --regenerate flag in the above benchmark bash scripts)

Download the prepared CSV Storm dataset:

> <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" alt="Hugging Face" width="20" height="20"> **Dataset download:** [CSV Storm on Hugging Face — link to be added](https://huggingface.co/datasets/REPLACE_WITH_ORGANIZATION/REPLACE_WITH_DATASET)

Alternatively, generate CSV Storm locally:

```bash
.venv/bin/python pollute_main.py \
  --source ./results/source.csv \
  --output ./data/csv_storm \
  --polluters csv_storm \
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
  sut/llm_hybrid_parser/llm-hybrid-bench.py \
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

## Evaluation

```bash
.venv/bin/python evaluate.py --sut <sut> --dataset csv_storm
```

Omit `--sut` to evaluate every SUT with output for csv_storm. One invocation
calculates strict whole-file accuracy and Pollock's loading success, precision,
recall, F1, and combined scores. It writes:

- per-file results to `results/<sut>/csv_storm/<sut>_results.csv`;
- a dataset summary to `results/evaluation_summary_csv_storm.csv`; and
- cross-SUT results to `results/evaluation_by_file_csv_storm.csv`.

Pollock's combined score is the sum of mean success and the mean precision,
recall, and F1 values for headers, records, and cells. Its maximum is 10.
Weighted scores use pollution frequencies from a government CSV survey and are
only applicable for set of files used by the original Pollock paper.


## Paper

> **Publication:** [Pollock Offsite paper — link to be added after submission](https://doi.org/REPLACE_WITH_DOI)
