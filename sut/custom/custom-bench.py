import sys
import os
import json
import argparse
from os.path import join, abspath, dirname

# make sure this script can be invoked from anywhere by finding repo root
REPO_ROOT = abspath(join(dirname(__file__), '..', '..'))
sys.path.insert(0, join(REPO_ROOT, 'sut'))

import time
from utils import print, save_time_df
from solution import parse_csv_with_validation

parser = argparse.ArgumentParser()
parser.add_argument(
    "--cheat",
    action="store_true",
    help="When malformed rows are detected, replace them with the ground-truth rows from data/<dataset>/clean",
)
args = parser.parse_args()

sut = 'custom'
DATASET = os.environ.get('DATASET', 'polluted_files')
IN_DIR = join(REPO_ROOT, 'data', DATASET, 'csv')
CLEAN_DIR = join(REPO_ROOT, 'data', DATASET, 'clean')
OUT_DIR = join(REPO_ROOT, 'results', sut, DATASET, 'loading')
TIME_DIR = join(REPO_ROOT, 'results', sut, DATASET)
CHEAT = args.cheat

os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TIME_DIR, exist_ok=True)

N_REPETITIONS = int(os.environ.get("N_REPETITIONS", 3))


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
            text_file.write(json.dumps({
                "line_num": row.get("line_num"),
                "reason": row.get("reason"),
                "raw": _json_safe_raw(row.get("raw")),
            }, ensure_ascii=True))
            text_file.write("\n")

times_dict = {}
benchmark_files = os.listdir(IN_DIR)
for idx, file in enumerate(benchmark_files):
    f = os.path.basename(file)
    in_filepath = join(IN_DIR, f)
    out_filename = f'{f}_converted.csv'
    out_filepath = join(OUT_DIR, out_filename)
    malformed_path = malformed_report_path(f)
    if not CHEAT and os.path.exists(out_filepath) and os.path.exists(malformed_path):
        continue
    print(f"({idx}/{len(benchmark_files)}) {f}")

    for time_rep in range(N_REPETITIONS):
        malformed = []
        try:
            start = time.time()
            clean_filepath = join(CLEAN_DIR, f)
            df, malformed = parse_csv_with_validation(
                in_filepath,
                clean_csv=clean_filepath,
                cheat=CHEAT,
            )
            end = time.time()
            if malformed:
                print(f"\t{len(malformed)} malformed row(s):")
                for row in malformed:
                    print(f"\t  line {row['line_num']}: {row['reason']} — {row['raw']!r}")
                if CHEAT:
                    print("\t  cheat mode: swapped malformed row(s) with ground truth")
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
