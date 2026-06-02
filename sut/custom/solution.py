import csv
import pandas as pd


def parse_csv_with_validation(csv_input: str):
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
    return pd.DataFrame(rows[1:], columns=rows[0]), malformed
