"""Run a small, fixed real-world CSV pilot and score against supplied clean files.

Usage: .venv/bin/python scripts/run_survey_sample_pilot.py
Outputs: results/runs/survey-sample-pilot/{manifest.json,per_file_results.csv}
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATASET = "survey_sample"
FILES = (
    "download (6).csv",
    "epcs-dwp-cmg-spend-july-2017.csv",
    "Note_4_Staff_costs_-_Average_number_of_persons_employed_13-14.csv",
    "20170320-ePC_Data-Travel-Stationery.csv",
)
MODELS = ("gpt-6-luna", "gpt-6.1-sol")
RUN_ROOT = ROOT / "results" / "runs" / "survey-sample-pilot"
RECORD_ROOT = ROOT / "experiments" / "survey_sample_pilot"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], env: dict[str, str]) -> None:
    print("Running", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for this pilot")
    endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    if not endpoint.endswith("/chat/completions"):
        raise SystemExit("OPENAI_ENDPOINT must end in /chat/completions")

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        DATASET=DATASET,
        RESULT_ROOT=str(RUN_ROOT),
        N_REPETITIONS="1",
        OPENAI_API_BASE=endpoint.removesuffix("/chat/completions"),
        LLM_BACKEND="openai",
    )
    manifest = {
        "dataset": DATASET,
        "files": list(FILES),
        "models": list(MODELS),
        "architectures": ["hybrid", "full_llm", "code_generation"],
        "baselines": ["clevercsv", "pandas_oracle_dialect"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "reference": "Existing data/survey_sample/clean files; no new human adjudication",
        "metric": "evaluate_single_file strict whole-table match, row-order invariant",
        "input_sha256": {f: digest(ROOT / "data" / DATASET / "csv" / f) for f in FILES},
        "reference_sha256": {f: digest(ROOT / "data" / DATASET / "clean" / f) for f in FILES},
    }
    (RUN_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    file_args = [arg for f in FILES for arg in ("--file", f)]
    run(["sut/clevercs/clevercs.py", *file_args, "--overwrite"], env)
    run(["sut/pandas/panda.py", *file_args, "--overwrite"], env)
    for model in MODELS:
        for f in FILES:
            run(["sut/llm_hybrid_parser/llm-hybrid-bench.py", "--model", model,
                 "--file", f, "--overwrite"], env)
            run(["sut/full_llm_loader/custom-bench.py", "--model", model,
                 "--file", f, "--overwrite"], env)
        run(["sut/code_generation_llm/custom-bench.py", "--model", model,
             *file_args, "--overwrite"], env)

    sys.path.insert(0, str(ROOT))
    from evaluate_utils import evaluate_single_file

    suts = ["clevercs", "pandas"]
    for model in MODELS:
        slug = model.replace("-", "_").replace(".", "_")
        suts.extend((f"llm_hybrid_parser_{slug}",
                     f"full_llm_loader_naive_{slug}",
                     f"code_generation_llm_{slug}"))
    columns = ("sut", "file", "success", "correct", "header_f1", "record_f1",
               "cell_f1", "evaluation_error")
    out = RUN_ROOT / "per_file_results.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for sut in suts:
            for f in FILES:
                result = evaluate_single_file(f, DATASET, sut, n_jobs=1,
                                              result_root=str(RUN_ROOT))
                writer.writerow({"sut": sut, "file": f,
                                 **{field: result.get(f"{sut}_{field}")
                                    for field in columns[2:]}})
    manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (RUN_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    RECORD_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUN_ROOT / "manifest.json", RECORD_ROOT / "manifest.json")
    shutil.copy2(out, RECORD_ROOT / "per_file_results.csv")
    print(out)


if __name__ == "__main__":
    main()
