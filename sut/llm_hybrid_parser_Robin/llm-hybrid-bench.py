import sys
import os
import re
import json
import argparse
from os.path import join, abspath, dirname

import pandas as pd

# make sure this script can be invoked from anywhere by finding repo root
REPO_ROOT = abspath(join(dirname(__file__), '..', '..'))
sys.path.insert(0, join(REPO_ROOT, 'sut'))

import time

parser = argparse.ArgumentParser()
parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Re-process files even if output already exists (default: skip already-processed files)",
)
parser.add_argument(
    "--cheat",
    action="store_true",
    help="Load the ground-truth file from data/<dataset>/clean instead of using LLM repair",
)
parser.add_argument(
    "--no-llm-repair",
    action="store_true",
    help="Disable LLM repair of malformed rows; skip rejected rows instead (dialect detection unaffected)",
)
parser.add_argument(
    "--llm-context-lines",
    type=int,
    default=10,
    help="Number of sample/good lines included in LLM prompts",
)
parser.add_argument(
    "--no-llm-dialect",
    action="store_true",
    help="Disable LLM dialect detection (requires --clevercsv so a dialect source remains)",
)
parser.add_argument(
    "--clevercsv",
    action="store_true",
    help="Also run CleverCSV and reconcile it with the LLM dialect (default: LLM dialect only). "
         "Tags results under the sut name suffix '_clevercsv'.",
)
parser.add_argument(
    "--duckdb-sniff",
    action="store_true",
    help="Also run DuckDB's sniff_csv and reconcile it with the LLM dialect, the same way "
         "--clevercsv does (default: off). Mutually exclusive with --clevercsv. "
         "Tags results under the sut name suffix '_duckdb'.",
)
parser.add_argument(
    "--no-llm-cache",
    action="store_true",
    help="Disable persistent LLM response cache (caching is on by default)",
)
parser.add_argument(
    "--model",
    default=None,
    help="OpenAI-compatible model to use (overrides OPENAI_MODEL env var); also sets sut name to custom_<model>",
)
parser.add_argument(
    "--file",
    default=None,
    help="Process only this single file from the dataset's csv/ dir (basename or path). "
         "Output is written to the usual dataset location; existing output is overwritten.",
)
parser.add_argument(
    "--verbose",
    action="store_true",
    help="Print each LLM prompt and response (dialect + repair) to the console",
)
args = parser.parse_args()
if args.cheat and args.no_llm_repair:
    parser.error("--cheat already disables LLM repair")

LLM_REPAIR = not args.cheat and not args.no_llm_repair
LLM_DIALECT = not args.no_llm_dialect
USE_CLEVERCSV = args.clevercsv
USE_DUCKDB_SNIFF = args.duckdb_sniff
if USE_CLEVERCSV and USE_DUCKDB_SNIFF:
    parser.error("--clevercsv and --duckdb-sniff are mutually exclusive; pick one non-LLM sniffer")
if not LLM_DIALECT and not (USE_CLEVERCSV or USE_DUCKDB_SNIFF):
    parser.error("--no-llm-dialect removes the LLM dialect source; pass --clevercsv or "
                 "--duckdb-sniff so a dialect source remains")
if (LLM_REPAIR or LLM_DIALECT) and not os.environ.get("OPENAI_API_KEY"):
    parser.error("LLM calls are enabled by default and require OPENAI_API_KEY. Use --no-llm-dialect "
                 "--no-llm-repair (with --clevercsv or --duckdb-sniff), or --cheat "
                 "to avoid LLM calls.")

if args.model:
    os.environ["OPENAI_MODEL"] = args.model

from utils import print
from solution import (
    configure_llm_cache,
    configure_llm_verbose,
    get_llm_cache_stats,
    get_llm_cost_summary,
    parse_csv_with_validation,
    reset_llm_cost_records,
)
from llm import _openai_model

if args.model:
    _model_slug = re.sub(r'[^a-z0-9]+', '_', args.model.lower()).strip('_')
    sut = f'llm_hybrid_parser_{_model_slug}'
else:
    sut = 'llm_hybrid_parser'
if USE_CLEVERCSV:
    sut += '_clevercsv' if LLM_DIALECT else '_clevercsv_only'
elif USE_DUCKDB_SNIFF:
    sut += '_duckdb' if LLM_DIALECT else '_duckdb_only'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = join(REPO_ROOT, 'data', DATASET, 'csv')
CLEAN_DIR = join(REPO_ROOT, 'data', DATASET, 'clean')
OUT_DIR = join(REPO_ROOT, 'results', sut, DATASET, 'loading')
TIME_DIR = join(REPO_ROOT, 'results', sut, DATASET)
CHEAT = args.cheat
LLM_CONTEXT_LINES = max(0, args.llm_context_lines)

os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)

# Shared LLM cache: one file per model, reused across every parser config. The cache key
# already embeds the model (see llm._prompt_hash), so different models never collide and
# identical prompts across parsers hit the same entry. Named after the resolved model so
# the filename matches the model baked into the keys.
_cache_slug = re.sub(r'[^a-z0-9]+', '_', _openai_model().lower()).strip('_')
_cache_path = None if args.no_llm_cache else join(REPO_ROOT, 'results', '_llm_cache', f'{_cache_slug}.json')
configure_llm_cache(path=_cache_path, enabled=not args.no_llm_cache)
configure_llm_verbose(args.verbose)

default_repetitions = 1 if (CHEAT or LLM_REPAIR) else 3
N_REPETITIONS = int(os.environ.get("N_REPETITIONS", default_repetitions))


def malformed_report_path(filename):
    return join(OUT_DIR, f"{filename}_malformed.txt")


def _json_safe_raw(raw):
    if isinstance(raw, (str, int, float, bool)) or raw is None:
        return raw
    if isinstance(raw, list):
        return raw
    return repr(raw)


def write_malformed_report(path, malformed=None, error=None):
    malformed = malformed or []
    with open(path, "w", encoding="utf-8") as text_file:
        if error is not None:
            text_file.write("Application Error\n")
            text_file.write(str(error))
            text_file.write("\n")
            return

        text_file.write(f"Malformed rows: {len(malformed)}\n")
        for row in malformed:
            payload = {
                "line_num": row.get("line_num"),
                "reason": row.get("reason"),
                "raw": _json_safe_raw(row.get("raw")),
            }
            if "repaired" in row:
                payload["repaired"] = bool(row.get("repaired"))
            text_file.write(json.dumps(payload, ensure_ascii=True))
            text_file.write("\n")

def save_run_df(time_dir, sut_name, run_dict):
    if not run_dict:
        print("No run changes to update")
        return

    rows = []
    for filename, records in run_dict.items():
        row = {"filename": filename, "model": _openai_model()}
        for idx, record in enumerate(records):
            for field in (
                "time",
                "llm_calls",
                "local_cache_hits",
                "uncached_input_tokens",
                "cached_input_tokens",
                "completion_tokens",
                "total_tokens",
                "input_cost_usd",
                "cached_input_cost_usd",
                "output_cost_usd",
                "estimated_api_cost_usd",
                "billable_cost_usd",
            ):
                row[f"{field}_{idx}"] = record.get(field)
        rows.append(row)

    update_run_df = pd.DataFrame(rows)
    run_path = join(time_dir, f"{sut_name}_time.csv")
    try:
        existing_run_df = pd.read_csv(run_path)
        if "filename" not in existing_run_df.columns:
            existing_run_df = existing_run_df.rename(
                columns={existing_run_df.columns[0]: "filename"}
            )
        if "model" not in existing_run_df.columns:
            existing_run_df["model"] = _openai_model()
        run_df = pd.concat(
            [existing_run_df, update_run_df],
            ignore_index=True,
        )
        run_df = run_df.drop_duplicates(
            subset=["filename", "model"],
            keep="last",
        )
    except FileNotFoundError:
        run_df = update_run_df
    run_df.to_csv(run_path, index=False)


run_dict = {}
benchmark_files = os.listdir(IN_DIR)
if args.file:
    target = os.path.basename(args.file)
    if target not in benchmark_files:
        parser.error(f"--file {target!r} not found in {IN_DIR}")
    benchmark_files = [target]
for idx, file in enumerate(benchmark_files):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    malformed_path = malformed_report_path(f)
    if not args.overwrite and not args.file and os.path.exists(out_filepath) and os.path.exists(malformed_path):
        continue
    print(f"({idx + 1}/{len(benchmark_files)}) {f}")

    for time_rep in range(N_REPETITIONS):
        malformed = []
        reset_llm_cost_records()
        try:
            start = time.time()
            clean_filepath = join(CLEAN_DIR, f)
            llm_sidecar = join(OUT_DIR, f + ".llm.jsonl")
            df, malformed = parse_csv_with_validation(
                in_filepath,
                clean_csv=clean_filepath,
                cheat=CHEAT,
                llm_repair=LLM_REPAIR,
                llm_dialect=LLM_DIALECT,
                use_clevercsv=USE_CLEVERCSV,
                use_duckdb_sniff=USE_DUCKDB_SNIFF,
                sidecar_path=llm_sidecar,
                llm_context_lines=LLM_CONTEXT_LINES,
                reset_sidecar=(time_rep == 0),
                verbose=args.verbose,
            )
            end = time.time()
            if malformed and args.verbose:
                print(f"\t{len(malformed)} malformed row(s):")
                for row in malformed:
                    print(f"\t  line {row['line_num']}: {row['reason']} — {row['raw']!r}")
                if CHEAT:
                    print("\t  cheat mode: loaded ground truth")
            if df.empty and len(df.columns) == 0:
                open(out_filepath, "w").close()
            else:
                df.to_csv(out_filepath, index=False)
            write_malformed_report(malformed_path, malformed=malformed)
        except Exception as e:
            end = time.time()
            print("\t", e)
            with open(out_filepath, "w") as text_file:
                text_file.write("Application Error\n")
                text_file.write(str(e))
            write_malformed_report(malformed_path, malformed=malformed, error=e)

        cost_summary = get_llm_cost_summary()
        cost_summary["time"] = end - start
        run_dict.setdefault(f, []).append(cost_summary)

        try:
            del start, end, df, text_file
        except:
            pass

save_run_df(TIME_DIR, sut, run_dict)

if LLM_REPAIR or LLM_DIALECT:
    stats = get_llm_cache_stats()
    if stats["total"] > 0:
        print(f"LLM calls: {stats['cached']}/{stats['total']} served from cache")
