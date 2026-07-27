from __future__ import print_function
import builtins as __builtin__
import csv
import re
import chardet
import numpy as np
import time
from pathlib import Path

from collections import Counter
from joblib import Parallel, delayed
from multiset import Multiset
from datetime import datetime
from .data_types import normalize_cell
from .ground_truth import manifest_accepts_origin, single_table_alternatives


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


def header_record_cell_measures_csv(source_csv, loaded_csv, n_jobs=1, nrows=None):
    # Both files are parsed as normal comma-delimited CSV after conversion:
    # source_csv is the expected clean file, loaded_csv is the SUT output.
    if nrows is not None and nrows < 0:
        raise ValueError("nrows must be non-negative or None")

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

    if nrows is not None:
        source_rows = source_rows[: nrows + 1]
        loaded_rows = loaded_rows[: nrows + 1]

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


def _empty_cell_padding_variants(row, width, missing_col=None):
    if len(row) != width - 1:
        return []
    if missing_col is not None:
        if missing_col < 0 or missing_col >= width:
            return []
        indexes = [missing_col]
    else:
        indexes = range(width)
    variants = []
    for idx in indexes:
        padded = list(row)
        padded.insert(idx, "")
        variants.append(padded)
    return variants


def _rows_match_with_deleted_value_padding(expected_rows, loaded_rows, row_order_invariant, missing_col=None):
    """Accept jagged legacy GT when a missing value is restored as an empty cell."""
    if len(expected_rows) != len(loaded_rows) or not expected_rows:
        return False

    width = len(expected_rows[0])
    if width == 0:
        return False

    if any(len(row) not in {width, width - 1} for row in expected_rows):
        return False
    if any(len(row) != width for row in loaded_rows):
        return False
    if not any(len(row) == width - 1 for row in expected_rows):
        return False

    def normalize_row(row):
        return tuple(map(normalize_cell, row))

    def expected_variants(row):
        if len(row) == width:
            return [normalize_row(row)]
        return [normalize_row(variant) for variant in _empty_cell_padding_variants(row, width, missing_col)]

    if not row_order_invariant:
        return all(
            normalize_row(loaded) in expected_variants(expected)
            for expected, loaded in zip(expected_rows, loaded_rows)
        )

    remaining = Counter(normalize_row(row) for row in loaded_rows)
    for expected in expected_rows:
        variants = expected_variants(expected)
        match = next((variant for variant in variants if remaining[variant] > 0), None)
        if match is None:
            return False
        remaining[match] -= 1
        if remaining[match] == 0:
            del remaining[match]
    return not remaining


def _deleted_value_padding_column(path):
    filename = str(path).rsplit("/", 1)[-1]
    if not (
        filename.startswith("file_less_columns_deleted_value_")
        or filename.startswith("file_variable_column_count_")
    ):
        return None
    match = re.search(r"_col_(\d+)\.csv$", filename)
    return int(match.group(1)) if match else None


def compare_files(source_csv, loaded_csv, n_jobs=1, origin_csv=None, row_order_invariant=False, nrows=None):
    # Both files are parsed as normal comma-delimited CSV after conversion:
    # source_csv is the expected clean file, loaded_csv is the SUT output.
    # The output is accepted if it matches the clean file as a whole, or (when
    # origin_csv is given) the pre-pollution origin file as a whole -- never a mix
    # of the two, so once one version fits the output must match all of it.
    # row_order_invariant (optional) accepts the rows in any order.
    if nrows is not None and nrows < 0:
        raise ValueError("nrows must be non-negative or None")

    source_rows = _read_csv_rows(source_csv)

    try:
        loaded_rows = _read_csv_rows(loaded_csv)
    except Exception:
        return False

    if nrows is not None:
        source_rows = source_rows[: nrows + 1]
        loaded_rows = loaded_rows[: nrows + 1]

    if _rows_match(source_rows, loaded_rows, row_order_invariant):
        return True

    missing_col = _deleted_value_padding_column(source_csv)
    if missing_col is not None and _rows_match_with_deleted_value_padding(
        source_rows,
        loaded_rows,
        row_order_invariant,
        missing_col=missing_col,
    ):
        return True

    if origin_csv is not None:
        try:
            origin_rows = _read_csv_rows(origin_csv)
        except Exception:
            return False
        if nrows is not None:
            origin_rows = origin_rows[: nrows + 1]
        return _rows_match(origin_rows, loaded_rows, row_order_invariant)

    return False


def compare_ground_truths(
    manifest_path,
    loaded_csv,
    n_jobs=1,
    origin_csv=None,
    row_order_invariant=False,
    nrows=None,
):
    """Compare one loaded table against every acceptable single-table GT."""
    candidates = single_table_alternatives(manifest_path)
    if not candidates:
        raise ValueError("Ground-truth bundle has no single-table alternatives")

    for alternative_id, expected_path in candidates:
        if compare_files(
            expected_path,
            loaded_csv,
            n_jobs=n_jobs,
            row_order_invariant=row_order_invariant,
            nrows=nrows,
        ):
            return True, alternative_id

    origin_candidate = origin_csv
    if origin_candidate is None and manifest_accepts_origin(manifest_path):
        dataset_root = Path(manifest_path).parent.parent.parent
        inferred_origin = dataset_root / "csv" / "source.csv"
        if inferred_origin.is_file():
            origin_candidate = inferred_origin

    if origin_candidate is not None and compare_files(
        candidates[0][1],
        loaded_csv,
        n_jobs=n_jobs,
        origin_csv=origin_candidate,
        row_order_invariant=row_order_invariant,
        nrows=nrows,
    ):
        return True, "origin"

    return False, None


def best_ground_truth_measures(
    manifest_path,
    loaded_csv,
    n_jobs=1,
    nrows=None,
):
    """Return the strongest metric result across single-table alternatives."""
    candidates = single_table_alternatives(manifest_path)
    if not candidates:
        raise ValueError("Ground-truth bundle has no single-table alternatives")

    measured = [
        (
            header_record_cell_measures_csv(
                expected_path,
                loaded_csv,
                n_jobs=n_jobs,
                nrows=nrows,
            ),
            alternative_id,
        )
        for alternative_id, expected_path in candidates
    ]
    return max(
        measured,
        key=lambda result: (
            result[0][8],
            result[0][5],
            result[0][2],
        ),
    )
