from os.path import join, dirname
import duckdb
import time
import os
import sys

sys.path.insert(0, join(dirname(__file__), '..'))
from utils import print, save_time_df, load_parameters
import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--strict",
    action="store_true",
    help="Enable DuckDB strict_mode (default off). When set, results are written to the "
         "'duckdbauto_strict' folder instead of 'duckdbauto'.",
)
args = parser.parse_args()

sut = 'duckdbauto_strict' if args.strict else 'duckdbauto'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = f'data/{DATASET}/csv/'
PARAM_DIR = f'data/{DATASET}/parameters'
OUT_DIR = f'results/{sut}/{DATASET}/loading/'
TIME_DIR = f'results/{sut}/{DATASET}/'

# Ensure required directories exist
os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(PARAM_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)

N_REPETITIONS = int(os.environ.get("N_REPETITIONS", 3))

times_dict = {}
benchmark_files = os.listdir(IN_DIR)
for idx,file in enumerate(benchmark_files):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    if os.path.exists(out_filepath):
        continue
    print(f"({idx}/{len(benchmark_files)}) {f}")

    kw = {}
    kw["strict_mode"] = args.strict
    kw["ignore_errors"] = True
    kw["null_padding"] = True
    kw["auto_type_candidates"] = ['NULL', 'BOOLEAN', 'BIGINT', 'DECIMAL', 'VARCHAR'] # exclude timestamp type as they get written to the solution file in a different format, leading to an error where semantically everything was correct (Pollock shows an error because "00:00" is a different string from "00:00:00")
    # Decimal over double because of rounding for long sequences after the comma

    for time_rep in range(N_REPETITIONS):
        con = duckdb.connect()
        start = time.time()
        try:
            rel = con.read_csv(in_filepath, **kw)
            end = time.time()
            rel = rel.df()
            rel.to_csv(out_filepath, index=False)
        except Exception as e:
            end = time.time()
            print("\t", e)
            with open(out_filepath, "w") as text_file:
                text_file.write("Application Error\n")
                text_file.write(str(e))

        times_dict[f] = times_dict.get(f, []) + [(end - start)]

        try:
            del start, end, df, text_file
        except:
            pass

save_time_df(TIME_DIR, sut, times_dict)
