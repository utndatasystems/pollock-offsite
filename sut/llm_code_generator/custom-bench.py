import sys
import os
import re
import json
import argparse
from os.path import join, abspath, dirname

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
    "--llm-repair",
    action="store_true",
    help="Deprecated/no-op: LLM repair is the default unless --cheat or --no-llm-repair is set",
)
parser.add_argument(
    "--no-llm-repair",
    action="store_true",
    help="Disable LLM calls; load with CleverCSV/DuckDB dialect detection and skip rejected rows",
)
parser.add_argument(
    "--llm-context-lines",
    type=int,
    default=10,
    help="Number of sample/good lines included in LLM prompts",
)
parser.add_argument(
    "--no-llm-sniff",
    action="store_true",
    help="Disable LLM dialect detection; use CleverCSV only",
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
    "--count-tokens",
    action="store_true",
    help="Dry-run: build all prompts and count tokens without calling the LLM",
)
args = parser.parse_args()
if args.cheat and args.llm_repair:
    parser.error("--cheat and --llm-repair cannot be used together")
if args.cheat and args.no_llm_repair:
    parser.error("--cheat already disables LLM repair")

LLM_REPAIR = not args.cheat and not args.no_llm_repair
LLM_SNIFF = not args.no_llm_sniff
if (LLM_REPAIR or LLM_SNIFF) and not args.count_tokens and not (
    os.environ.get("OPENAI_API_KEY")
):
    parser.error("LLM calls are enabled by default and require OPENAI_API_KEY. Use --no-llm-sniff --no-llm-repair, --cheat, or --count-tokens to avoid LLM calls.")

if args.model:
    os.environ["OPENAI_MODEL"] = args.model

from utils import print, save_time_df
from solution import parse_csv_with_validation, configure_llm_cache, configure_llm_dry_run, get_llm_cache_stats

if args.model:
    _model_slug = re.sub(r'[^a-z0-9]+', '_', args.model.lower()).strip('_')
    sut = f'custom_{_model_slug}'
else:
    sut = 'custom'
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

_cache_path = None if args.no_llm_cache else join(REPO_ROOT, 'results', sut, 'llm_cache.json')
configure_llm_cache(path=_cache_path, enabled=not args.no_llm_cache)
configure_llm_dry_run(args.count_tokens)

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

times_dict = {}
benchmark_files = os.listdir(IN_DIR)
for idx, file in enumerate(benchmark_files):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    malformed_path = malformed_report_path(f)
    if not args.overwrite and os.path.exists(out_filepath) and os.path.exists(malformed_path):
        continue
    print(f"({idx + 1}/{len(benchmark_files)}) {f}")

    for time_rep in range(N_REPETITIONS):
        malformed = []
        try:
            start = time.time()
            clean_filepath = join(CLEAN_DIR, f)
            llm_sidecar = join(OUT_DIR, f + ".llm.jsonl")
            df, malformed = parse_csv_with_validation(
                in_filepath,
                clean_csv=clean_filepath,
                cheat=CHEAT,
                llm_repair=LLM_REPAIR,
                llm_sniff=LLM_SNIFF,
                sidecar_path=llm_sidecar,
                llm_context_lines=LLM_CONTEXT_LINES,
                reset_sidecar=(time_rep == 0),
            )
            end = time.time()
            if malformed:
                print(f"\t{len(malformed)} malformed row(s):")
                for row in malformed:
                    print(f"\t  line {row['line_num']}: {row['reason']} — {row['raw']!r}")
                if CHEAT:
                    print("\t  cheat mode: loaded ground truth")
            df.to_csv(out_filepath, index=False)
            write_malformed_report(malformed_path, malformed=malformed)
        except Exception as e:
            end = time.time()
            print("\t", e)
            with open(out_filepath, "w") as text_file:
                text_file.write("Application Error\n")
                text_file.write(str(e))
            write_malformed_report(malformed_path, malformed=malformed, error=e)

        times_dict[f] = times_dict.get(f, []) + [(end - start)]

        try:
            del start, end, df, text_file
        except:
            pass

save_time_df(TIME_DIR, sut, times_dict)

if LLM_REPAIR or LLM_SNIFF:
    stats = get_llm_cache_stats()
    if stats["total"] > 0:
        print(f"LLM calls: {stats['cached']}/{stats['total']} served from cache")
    if args.count_tokens and stats["total"] > 0:
        def _tok(chars): return chars // 4
        inp_total  = _tok(stats["input_chars_total"])
        inp_cached = _tok(stats["input_chars_cached"])
        inp_fresh  = inp_total - inp_cached
        out_cached = _tok(stats["output_chars_cached"])
        out_fresh  = _tok(stats["output_chars_fresh"])
        out_total  = out_cached + out_fresh
        print(f"Token estimate (~4 chars/token, output is estimated):")
        print(f"  Input:  {inp_total:,} total  ({inp_fresh:,} fresh + {inp_cached:,} cached)")
        print(f"  Output: {out_total:,} total  ({out_fresh:,} fresh estimated + {out_cached:,} cached)")
        print(f"  (repair estimate based on CleverCSV sniff; actual may differ if LLM corrects dialect)")
