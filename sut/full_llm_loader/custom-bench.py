import argparse
import os
import sys
import time
from os.path import abspath, dirname, join

# make sure this script can be invoked from anywhere by finding repo root
REPO_ROOT = abspath(join(dirname(__file__), '..', '..'))
sys.path.insert(0, join(REPO_ROOT, 'sut'))

import pandas as pd

from utils import print
from solution import parse_csv
from llm_utils import get_last_llm_cost_record


parser = argparse.ArgumentParser()
parser.add_argument(
    '--overwrite',
    action='store_true',
    help='Re-process files and bypass the local LLM response cache (default: skip already-processed files)',
)
parser.add_argument(
    '--file',
    default=None,
    help='Process only this single file from the dataset\'s csv/ dir (basename or path). Output is written to the usual dataset location; existing output is overwritten.',
)
parser.add_argument(
    '--version',
    choices=('naive', 'guided'),
    default='naive',
    help='Prompt version to use when querying the LLM.',
)
parser.add_argument(
    '--encoding',
    default='utf-8',
    help='CSV encoding to pass through to the prompt builder.',
)
parser.add_argument(
    '--nrows',
    type=int,
    default=None,
    help='Optional row limit for the reconstructed DataFrame.',
)
args = parser.parse_args()

if args.nrows is not None and args.nrows < 0:
    parser.error('--nrows must be non-negative or omitted')

if args.overwrite:
    os.environ['FULL_LLM_LOADER_BYPASS_CACHE'] = '1'

sut = f'full_llm_loader_{args.version}'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = join(REPO_ROOT, 'data', DATASET, 'csv')
OUT_DIR = join(REPO_ROOT, 'results', sut, DATASET, 'loading')
TIME_DIR = join(REPO_ROOT, 'results', sut, DATASET)

os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)

N_REPETITIONS = int(os.environ.get('N_REPETITIONS', 3))

benchmark_files = os.listdir(IN_DIR)
if args.file:
    target = os.path.basename(args.file)
    if target not in benchmark_files:
        parser.error(f"--file {target!r} not found in {IN_DIR}")
    benchmark_files = [target]

def save_run_df(time_dir, sut_name, run_dict):
    if not run_dict:
        print("No run changes to update")
        return

    rows = {}
    for filename, records in run_dict.items():
        row = {}
        for idx, record in enumerate(records):
            row[f"time_{idx}"] = record.get("time")
            row[f"uncached_input_tokens_{idx}"] = record.get("uncached_input_tokens")
            row[f"cached_input_tokens_{idx}"] = record.get("cached_input_tokens")
            row[f"completion_tokens_{idx}"] = record.get("completion_tokens")
        rows[filename] = row

    update_run_df = pd.DataFrame.from_dict(rows, orient="index")
    run_path = join(time_dir, f"{sut_name}_time.csv")
    try:
        existing_run_df = pd.read_csv(run_path, index_col="filename")
        run_df = pd.concat([existing_run_df, update_run_df]).groupby(level=0).last()
    except FileNotFoundError:
        run_df = update_run_df
    run_df.to_csv(run_path, index_label="filename")


run_dict = {}
for idx, file in enumerate(benchmark_files):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    if not args.overwrite and not args.file and os.path.exists(out_filepath):
        continue
    print(f"({idx}/{len(benchmark_files)}) {f}")

    for time_rep in range(N_REPETITIONS):
        start = time.time()
        try:
            # This is where the full_llm_parser is being called
            df = parse_csv(
                in_filepath,
                nrows=args.nrows,
                prompt_version=args.version,
                encoding=args.encoding,
            )
            end = time.time()
            df.to_csv(out_filepath, index=False)
        except Exception as e:
            end = time.time()
            print('\t', e)
            with open(out_filepath, 'w') as text_file:
                text_file.write('Application Error\n')
                text_file.write(str(e))

        elapsed = end - start
        cost_record = get_last_llm_cost_record() or {}
        run_dict.setdefault(f, []).append({
            "time": elapsed,
            "uncached_input_tokens": cost_record.get("uncached_input_tokens"),
            "cached_input_tokens": cost_record.get("cached_input_tokens"),
            "completion_tokens": cost_record.get("completion_tokens"),
        })

        try:
            del start, end, df, text_file
        except:
            pass

save_run_df(TIME_DIR, sut, run_dict)
