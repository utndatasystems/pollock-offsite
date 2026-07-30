import argparse
import csv
from os import listdir
from os.path import join, dirname
import os
import sys
import time

sys.path.insert(0, join(dirname(__file__), '..'))
from utils import print, save_time_df

parser = argparse.ArgumentParser()
parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Re-process files even if output already exists (default: skip already-processed files)",
)
args = parser.parse_args()

sut = 'pycsv'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = f'data/{DATASET}/csv/'
OUT_DIR = f'results/{sut}/{DATASET}/loading/'
TIME_DIR = f'results/{sut}/{DATASET}/'

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)
N_REPETITIONS = int(os.environ.get("N_REPETITIONS", 3))

# csv.Sniffer is quadratic in the sample length, so sniffing a multi-MB file takes
# minutes. Sniff a prefix instead; files below this size are still sniffed whole.
SNIFF_SAMPLE_CHARS = int(os.environ.get("SNIFF_SAMPLE_CHARS", 64 * 1024))

TO_SKIP = []

times_dict = {}
benchmark_files = listdir(IN_DIR)

for idx, f in enumerate(benchmark_files):
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    if not args.overwrite and os.path.exists(out_filepath):
        continue
    print(f'Processing file ({idx + 1}/{len(benchmark_files)}) {f}')

    for time_rep in range(N_REPETITIONS):
        start = time.time()
        try:
            with open(in_filepath, newline='') as in_csvfile:
                sample = in_csvfile.read(SNIFF_SAMPLE_CHARS)
                if len(sample) == SNIFF_SAMPLE_CHARS and '\n' in sample:
                    sample = sample[:sample.rindex('\n') + 1]
                dialect = csv.Sniffer().sniff(sample)
                in_csvfile.seek(0)
                reader = csv.reader(in_csvfile, dialect)
                rows = list(reader)
            end = time.time()
            with open(out_filepath, 'w', newline='') as out_csvfile:
                csv.writer(out_csvfile).writerows(rows)

        except Exception as e:
            end = time.time()
            print("Application error on file", f)
            print("\t", e)
            with open(out_filepath, "w") as out_csvfile:
                out_csvfile.write("Application Error\n")
                out_csvfile.write(str(e))

        times_dict[f] = times_dict.get(f, []) + [(end - start)]

        try:
            del start, end, in_csvfile, dialect, reader, rows, out_csvfile
        except:
            pass

save_time_df(TIME_DIR, sut, times_dict)
