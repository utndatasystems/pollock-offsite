from os import listdir
import argparse
import os
import sys
from os.path import join, dirname

sys.path.insert(0, join(dirname(__file__), '..'))
from utils import print, save_time_df
import clevercsv
import time

from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Re-process files even if output already exists (default: skip already-processed files)",
)
args = parser.parse_args()

sut = 'clevercs'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = f'data/{DATASET}/csv/'
OUT_DIR = f'results/{sut}/{DATASET}/loading/'
TIME_DIR = f'results/{sut}/{DATASET}'

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)
N_REPETITIONS = int(os.environ.get("N_REPETITIONS", 3))

times_dict = {}
benchmark_files = listdir(IN_DIR)

for idx, f in enumerate(benchmark_files):
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    if not args.overwrite and os.path.exists(out_filepath):
        continue
    print(f'Processing file ({idx + 1}/{len(benchmark_files)}) {f}')

    for time_rep in list(range(N_REPETITIONS)):
        start = time.time()
        try:
            with open(in_filepath, newline='') as in_csvfile:
                dialect = clevercsv.Sniffer().sniff(in_csvfile.read())
                in_csvfile.seek(0)
                reader = clevercsv.reader(in_csvfile, dialect)
                rows = list(reader)
            end = time.time()
            with open(out_filepath, 'w', newline='') as out_csvfile:
                clevercsv.write.writer(out_csvfile).writerows(rows)

        except Exception as e:
            end = time.time()
            print("Application error on file", f)
            print("\t", e)
            with open(out_filepath, "w") as out_csvfile:
                out_csvfile.write("Application Error\n")
                out_csvfile.write(str(e))

        times_dict[f] = times_dict.get(f, []) + [(end - start)]
        print("\tProcessing complete in", (end - start) * 1000, "ms")

        del dialect, reader, rows, start, end, in_csvfile, out_csvfile

save_time_df(TIME_DIR, sut, times_dict)
