import csv
import pandas as pd


def dataframe_from_rows(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


def load_clean_rows(clean_csv: str):
    with open(clean_csv, newline='') as f:
        return list(csv.reader(f))


def repair_with_ground_truth(rows, malformed, clean_csv: str):
    clean_rows = load_clean_rows(clean_csv)
    if not clean_rows:
        return dataframe_from_rows(rows)

    clean_header = clean_rows[0]
    clean_data = clean_rows[1:]

    malformed_lines = {
        int(entry["line_num"])
        for entry in malformed
        if entry.get("line_num") is not None
    }
    parsed_data = rows[1:] if len(rows) > 1 else []

    expected_good_rows = max(
        0,
        len(clean_data) - sum(1 for line_num in malformed_lines if line_num > 1),
    )
    if len(parsed_data) != expected_good_rows:
        return dataframe_from_rows(rows)

    repaired_data = []
    good_iter = iter(parsed_data)
    for line_num, clean_row in enumerate(clean_rows[1:], start=2):
        if line_num in malformed_lines:
            repaired_data.append(clean_row)
            continue
        try:
            repaired_data.append(next(good_iter))
        except StopIteration:
            return dataframe_from_rows(rows)

    try:
        next(good_iter)
    except StopIteration:
        pass
    else:
        return dataframe_from_rows(rows)

    return pd.DataFrame(repaired_data, columns=clean_header)


def parse_csv_with_validation(csv_input: str, clean_csv: str = None, cheat: bool = False):
    """
    Parse a CSV, skipping malformed rows.

    Returns:
        (DataFrame of good rows, list of malformed row dicts)
        Each malformed dict has keys: line_num, raw, reason.
    """
    with open(csv_input, newline='') as f:
        try:
            expected_cols = len(next(csv.reader(f)))
        except StopIteration:
            return pd.DataFrame(), []
        f.seek(0)
        vr = csv.ValidationReader(f, expected_cols=expected_cols, strict=True)
        rows = list(vr)
        malformed = vr.malformed_rows
    if not rows:
        return pd.DataFrame(), malformed
    if cheat and malformed and clean_csv is not None:
        return repair_with_ground_truth(rows, malformed, clean_csv), malformed
    return dataframe_from_rows(rows), malformed
