import argparse
import os
import re
import sys
import time
from os.path import abspath, dirname, join

# make sure this script can be invoked from anywhere by finding repo root
REPO_ROOT = abspath(join(dirname(__file__), '..', '..'))
sys.path.insert(0, join(REPO_ROOT, 'sut'))

import pandas as pd
from tqdm import tqdm

from utils import print
from solution import parse_csv
from llm_utils import get_last_llm_cost_record
from llm_config import get_openai_model


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
parser.add_argument(
    '--verbose',
    action='store_true',
    help='Print the raw LLM response to the console.',
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
CACHE_DIR = join(TIME_DIR, 'llm_cache')
os.environ['FULL_LLM_LOADER_CACHE_DIR'] = CACHE_DIR

os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

N_REPETITIONS = int(os.environ.get('N_REPETITIONS', 1))
MODEL = get_openai_model()

benchmark_files = os.listdir(IN_DIR)
if args.file:
    target = os.path.basename(args.file)
    if target not in benchmark_files:
        parser.error(f"--file {target!r} not found in {IN_DIR}")
    benchmark_files = [target]

POLLUTION_PATTERNS = [
    (r"file_no_payload",                "Empty file (0 bytes)"),
    (r"file_no_trailing_newline",        "Missing trailing newline"),
    (r"file_double_trailing_newline",    "Double trailing newline"),
    (r"file_no_header",                  "No header row"),
    (r"file_header_multirow_(\d+)",      "Multi-row header ({0} rows)"),
    (r"file_header_only",                "Header row only, no data"),
    (r"file_one_data_row",               "Single data row"),
    (r"file_preamble",                   "Preamble rows before header"),
    (r"file_multitable_less",            "Two tables, first has fewer columns"),
    (r"file_multitable_more",            "Two tables, first has more columns"),
    (r"file_multitable_same",            "Two tables with the same number of columns"),
    (r"file_field_delimiter_(0x\w+)",    "Non-standard field delimiter ({0})"),
    (r"file_quotation_char_(0x\w+)",     "Non-standard quotation character ({0})"),
    (r"file_escape_char_(0x\w+)",        "Non-standard escape character ({0})"),
    (r"file_record_delimiter_(0x\w+)",   "Non-standard record delimiter ({0})"),
    (r"row_extra_quote(\d+)_col(\d+)",   "Extra unescaped quote in row {0}, column {1}"),
    (r"row_field_delimiter_(\d+)_",      "Row {0} uses space as field delimiter (opposed to the correct delimiter defined by the grammar)"),
    (r"row_less_sep_row(\d+)_col(\d+)",  "Missing delimiter in row {0} at column {1}"),
    (r"row_more_sep_row(\d+)_col(\d+)",  "Extra delimiter in row {0} at column {1}"),
]


def pollution_type(filename):
    stem = filename.removesuffix('.csv')
    for pattern, description in POLLUTION_PATTERNS:
        match = re.match(pattern, stem)
        if match:
            return description.format(*match.groups())
    return 'Unknown'


_GROUP_PATTERNS = [
    (r"row_field_delimiter_\d+_.+", "Row uses space as field delimiter"),
    (r"row_extra_quote\d+_col\d+",  "Extra unescaped quote"),
    (r"row_less_sep_row\d+_col\d+", "Missing delimiter"),
    (r"row_more_sep_row\d+_col\d+", "Extra delimiter"),
]


def pollution_group(filename):
    """Like pollution_type but collapses row/col-index variants into a single label."""
    stem = filename.removesuffix('.csv')
    for pattern, description in _GROUP_PATTERNS:
        if re.fullmatch(pattern, stem):
            return description
    return pollution_type(filename)


def save_run_df(time_dir, sut_name, run_dict):
    if not run_dict:
        print("No run changes to update")
        return

    rows = []
    for filename, records in run_dict.items():
        row = {
            'filename': filename,
            'pollution': pollution_group(filename),
            'model': MODEL,
        }
        for idx, record in enumerate(records):
            row[f"time_{idx}"] = record.get('time')
            row[f"uncached_input_tokens_{idx}"] = record.get('uncached_input_tokens')
            row[f"cached_input_tokens_{idx}"] = record.get('cached_input_tokens')
            row[f"completion_tokens_{idx}"] = record.get('completion_tokens')
        rows.append(row)

    update_run_df = pd.DataFrame(rows)
    run_path = join(time_dir, f"{sut_name}_time.csv")
    try:
        existing_run_df = pd.read_csv(run_path)
        if 'filename' not in existing_run_df.columns:
            existing_run_df = existing_run_df.rename(columns={existing_run_df.columns[0]: 'filename'})
        if 'pollution' not in existing_run_df.columns:
            existing_run_df['pollution'] = existing_run_df['filename'].map(pollution_group)
        if 'model' not in existing_run_df.columns:
            existing_run_df['model'] = MODEL
        run_df = pd.concat([existing_run_df, update_run_df], ignore_index=True)
        run_df = run_df.drop_duplicates(subset=['filename', 'pollution', 'model'], keep='last')
    except FileNotFoundError:
        run_df = update_run_df
    run_df.to_csv(run_path, index=False)


run_dict = {}
for idx, file in enumerate(tqdm(benchmark_files, total=len(benchmark_files), desc="Benchmark files", unit="file")):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    if not args.overwrite and not args.file and os.path.exists(out_filepath):
        continue
    print(f"({idx + 1}/{len(benchmark_files)}) {f}")

    for time_rep in range(N_REPETITIONS):
        start = time.time()
        try:
            # This is where the full_llm_parser is being called
            df = parse_csv(
                in_filepath,
                nrows=args.nrows,
                prompt_version=args.version,
                encoding=args.encoding,
                verbose=args.verbose,
            )
            end = time.time()
            fixed_csv = df.attrs["llm_fixed_csv"]
            with open(out_filepath, 'w', encoding='utf-8', newline='') as text_file:
                text_file.write(fixed_csv)
                newline = chr(10)
                if fixed_csv and not fixed_csv.endswith(newline):
                    text_file.write(newline)
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
