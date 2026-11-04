# CSVStorm

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


Required environment variables and hosting
  - `OPENAI_ENDPOINT`: OpenAI-compatible chat-completions endpoint 
  - `OPENAI_API_KEY`: Key for OpenAI endpoint
  - `OLLAMA_API_BASE`: local Ollama API base. Needs Qwen3.5 0.8B hosted. (see further instructions below, default: http://localhost:11434/v1)

**!WILL INCUR MONETARY COST FROM API CALLS!**

```
bash scripts/run_full_benchmark_on_csvstorm.sh --regenerate --confirm-cost
```

or to just run the classical baselines without LLM-Calls:

```
bash scripts/run_classical_baselines_on_csvstorm.sh --regenerate
```

Each benchmark invocation creates a new directory under `results/runs/` and
prints its run ID. Use `--run-id NAME` to choose an ID, or `--resume NAME` to
continue an interrupted run. Resume checks the Git commit, dataset fingerprint,
Python version, and run settings before using existing outputs. Runs require a
clean Git working tree. The full benchmark makes cold LLM calls for official
runtime measurements; `--confirm-cost` is still required.

Each run contains `manifest.json`, per-parser outputs, and evaluation summaries.
Run directories are ignored by Git. To copy a completed run's manifest and
summary CSVs into the trackable `experiments/NAME/` directory, run:

```bash
.venv/bin/python scripts/experiment_run.py export --run-id NAME
```

Review and commit only the experiment records used in the paper. Keep a durable
copy of the full run directory if raw parser outputs are needed later.


## Access or generate the CSV Storm dataset

(automatically done by --regenerate flag in the above benchmark bash scripts)

Download the prepared CSV Storm dataset:

> <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" alt="Hugging Face" width="20" height="20"> **Dataset download:**  [CSV Storm on Hugging Face](https://huggingface.co/datasets/csvstorm/csvstorm)

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


## Evaluation

```bash
.venv/bin/python evaluate.py --sut <sut> --dataset csv_storm
```

Omit `--sut` to evaluate every SUT with output for csv_storm. One invocation
calculates strict whole-file accuracy and Pollock's loading success, precision,
recall, F1, and combined scores. It writes:

- per-file results to `<result-root>/<sut>/csv_storm/<sut>_results.csv`;
- a dataset summary to `<result-root>/evaluation_summary_csv_storm.csv`; and
- cross-SUT results to `<result-root>/evaluation_by_file_csv_storm.csv`.

The benchmark scripts set `<result-root>` to `results/runs/<run-id>`. Direct
calls to `evaluate.py` still use `results/` unless `--result` is provided.
For a small sample run, repeat `evaluate.py --file FILENAME` to evaluate only
selected dataset files.

Pollock's combined score is the sum of mean success and the mean precision,
recall, and F1 values for headers, records, and cells. Its maximum is 10.
Weighted scores use pollution frequencies from a government CSV survey and are
only applicable for set of files used by the original Pollock paper.


## Paper

The LaTeX manuscript lives in the `manuscript/` Git submodule, linked to the
[Overleaf-connected repository](https://github.com/luisaneubauer/Agentic-Parsing-CR).
After cloning this repository, fetch it with `git submodule update --init`.
Commit and push manuscript edits from inside `manuscript/`, then run
`git add manuscript` and commit the updated submodule pointer in this repository.

The code used for the accepted CIDR submission is preserved at the annotated
Git tag `cidr-submission` (commit `251c9f8eed0e1c83bbe277d8503a35e365064491`).
Further experiments for the camera-ready paper are developed on the
`cidr-camera-ready` branch.

> **Publication:** Link to the camera-ready paper to be added when available.
