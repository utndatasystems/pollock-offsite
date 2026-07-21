from __future__ import print_function
import builtins as __builtin__
import csv
import chardet
import numpy as np
import time

from collections import Counter
from joblib import Parallel, delayed
from multiset import Multiset
from datetime import datetime
from .data_types import normalize_cell


def print(*args, **kwargs):
    return __builtin__.print(f"\033[94m{datetime.fromtimestamp(time.time() + 3600).strftime('%H:%M:%S')}:\033[0m", *args, **kwargs)


def successful_csv(filepath):
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = f.read()
    except Exception as e:
        with open(filepath, "rb") as f:
            data = f.read()
        encoding = chardet.detect(data)["encoding"]
        data = data.decode(encoding)

    if not len(data):
        return 1
    if data.splitlines()[0] == "Application Error":
        return 0
    else:
        return 1


def header_record_cell_measures_csv(source_csv, loaded_csv, n_jobs=1):
    # Both files are parsed as normal comma-delimited CSV after conversion:
    # source_csv is the expected clean file, loaded_csv is the SUT output.
    with open(source_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"', doublequote=True)
        source_rows = [row for row in reader]

    try:
        with open(loaded_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"', doublequote=True)
            loaded_rows = [row for row in reader]
    except Exception as e:
        with open(loaded_csv, "rb") as f:
            data = f.read()
        encoding = chardet.detect(data)["encoding"]
        with open(loaded_csv, "r", encoding=encoding) as f:
            reader = csv.reader(f, delimiter=",", quotechar='"', doublequote=True)
            loaded_rows = [row for row in reader]

    if not len(source_rows):
        return 1., 1., 1., 1., 1., 1., 1., 1., 1.

    source_header = list(map(normalize_cell, source_rows[0]))
    if len(source_header) == 0:
        header_p = header_r = header_f1 = 1.0
    else:
        if not len(loaded_rows):
            header_p = header_r = header_f1 = 0.0
        else:
            loaded_header = list(map(normalize_cell, loaded_rows[0]))
            # Header comparison ignores column order but preserves duplicates by
            # using multisets, so repeated names must appear the right number of times.
            s = Multiset(source_header)
            l = Multiset(loaded_header)
            i = s.intersection(l)
            if not len(i):
                header_p = header_r = header_f1 = 0.0
            else:
                #TODO: conventionally precision divided predicted / source
                header_p = np.sum([v for k, v in i.items()]) / len(source_header)
                #TODO: conventionally recall divides expected / source
                header_r = np.sum([v for k, v in i.items()]) / len(loaded_header)
                header_f1 = (header_p * header_r) / (header_p + header_r) * 2

    if n_jobs == 1:
        normalized_source_cells = [list(map(normalize_cell, r)) for r in source_rows]
        normalized_loaded_cells = [list(map(normalize_cell, r)) for r in loaded_rows]
    else:
        func = lambda x: list(map(normalize_cell, x))
        normalized_source_cells = Parallel(n_jobs=n_jobs)(delayed(func)(r) for r in source_rows)
        normalized_loaded_cells = Parallel(n_jobs=n_jobs)(delayed(func)(r) for r in loaded_rows)

    source_records = list(map(lambda x: "".join(x), normalized_source_cells[1:]))
    loaded_records = list(map(lambda x: "".join(x), normalized_loaded_cells[1:]))

    # Record comparison also ignores row order. Each data row is normalized and
    # collapsed to one string, then compared as a multiset entry.
    rec_s = Multiset(source_records)
    rec_l = Multiset(loaded_records)
    rec_i = rec_s.intersection(rec_l)

    if not len(source_records):
        rec_p = rec_r = rec_f1 = 1.0
    elif not len(rec_i):
        rec_p = rec_r = rec_f1 = 0.0
    else:
        #TODO: conventionally recall / precision divides expected/source 
        rec_p = np.sum([v for k, v in rec_i.items()]) / len(source_records)
        rec_r = np.sum([v for k, v in rec_i.items()]) / len(loaded_records)
        rec_f1 = (rec_p * rec_r) / (rec_p + rec_r) * 2

    source_cells = [c for r in source_rows for c in r]
    loaded_cells = [c for r in loaded_rows for c in r]

    # Cell comparison ignores both row and column position. It only checks that
    # the same raw cell values appear the same number of times.
    cell_s = Multiset(source_cells)
    cell_l = Multiset(loaded_cells)
    cell_i = cell_s.intersection(cell_l)

    if not len(source_cells):
        cell_p = cell_r = cell_f1 = 1.0
    elif not len(cell_i):
        cell_p = cell_r = cell_f1 = 0.0
    else:
        #TODO: conventionally recall / precision divides expected/source 
        cell_p = np.sum([v for k, v in cell_i.items()]) / len(source_cells)
        cell_r = np.sum([v for k, v in cell_i.items()]) / len(loaded_cells)
        cell_f1 = (cell_p * cell_r) / (cell_p + cell_r) * 2

    return header_p, header_r, header_f1, rec_p, rec_r, rec_f1, cell_p, cell_r, cell_f1


def _read_csv_rows(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter=",", quotechar='"', doublequote=True))


def _rows_match(expected_rows, loaded_rows, row_order_invariant):
    # Whole-file comparison of the loaded output against a single expected version.
    # row_order_invariant compares the rows as a multiset so any ordering of rows
    # is accepted, while cells within a row keep their order.
    if len(expected_rows) != len(loaded_rows):
        return False
    if row_order_invariant:
        return (Counter(tuple(map(normalize_cell, r)) for r in expected_rows) ==
                Counter(tuple(map(normalize_cell, r)) for r in loaded_rows))
    for r1, r2 in zip(expected_rows, loaded_rows):
        if len(r1) != len(r2):
            return False
        if any(normalize_cell(c1) != normalize_cell(c2) for c1, c2 in zip(r1, r2)):
            return False
    return True


def compare_files(source_csv, loaded_csv, n_jobs=1, origin_csv=None, row_order_invariant=False):
    # Both files are parsed as normal comma-delimited CSV after conversion:
    # source_csv is the expected clean file, loaded_csv is the SUT output.
    # The output is accepted if it matches the clean file as a whole, or (when
    # origin_csv is given) the pre-pollution origin file as a whole -- never a mix
    # of the two, so once one version fits the output must match all of it.
    # row_order_invariant (optional) accepts the rows in any order.
    source_rows = _read_csv_rows(source_csv)

    try:
        loaded_rows = _read_csv_rows(loaded_csv)
    except Exception:
        return False

    if _rows_match(source_rows, loaded_rows, row_order_invariant):
        return True

    if origin_csv is not None:
        try:
            origin_rows = _read_csv_rows(origin_csv)
        except Exception:
            return False
        return _rows_match(origin_rows, loaded_rows, row_order_invariant)

    return False
