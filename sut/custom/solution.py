import csv
from io import StringIO
from typing import Any

import pandas as pd

try:
    from .dialect_inference import CsvDialectConfig, infer_csv_dialect, repair_csv_row
except ImportError:
    from dialect_inference import CsvDialectConfig, infer_csv_dialect, repair_csv_row


def get_file_as_string(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return f.read()


def _reader_kwargs(config: CsvDialectConfig) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "delimiter": config.delimiter,
        "doublequote": config.doublequote,
        "skipinitialspace": config.skipinitialspace,
    }
    if config.quotechar is not None:
        kwargs["quotechar"] = config.quotechar
    else:
        kwargs["quoting"] = csv.QUOTE_NONE
    if config.escapechar is not None:
        kwargs["escapechar"] = config.escapechar
    return kwargs


def _read_rows(file_content: str, config: CsvDialectConfig) -> list[list[str]]:
    reader = csv.reader(StringIO(file_content), **_reader_kwargs(config))
    return [row for row in reader]


def _rows_to_dataframe(rows: list[list[str]], has_header: bool) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    if has_header:
        max_width = max(len(row) for row in rows)
        columns = rows[0] + [
            f"column_{index}" for index in range(len(rows[0]), max_width)
        ]
        data_rows = [row + [None] * (max_width - len(row)) for row in rows[1:]]
        return pd.DataFrame(data_rows, columns=columns)
    return pd.DataFrame(rows)


def _neighboring_rows(
    rows_by_number: dict[int, list[str]],
    row_number: int,
) -> dict[int, list[str]]:
    neighbor_numbers = (
        row_number - 2,
        row_number - 1,
        row_number + 1,
        row_number + 2,
    )
    return {
        neighbor_number: rows_by_number[neighbor_number]
        for neighbor_number in neighbor_numbers
        if neighbor_number != 0 and neighbor_number in rows_by_number
    }


def parse_csv(csv_input: str) -> pd.DataFrame:
    print(f"Parsing {csv_input}...")

    file_content = get_file_as_string(csv_input)
    dialect_config = infer_csv_dialect(file_content)
    print(f"Detected dialect config: {dialect_config}")
    rows = _read_rows(file_content, dialect_config)

    column_counts = {}
    for row in rows:
        column_counts[len(row)] = column_counts.get(len(row), 0) + 1
    if len(column_counts) > 1:
        print("Warning: Detected varying number of columns across rows:")
        max_key, max_value = max(column_counts.items(), key=lambda item: item[1])

        if max_value > len(rows) * 0.9:
            print(
                "90% of rows have the same number of columns, "
                "likely indicating a header row."
            )
            fixed_rows: dict[int, list[str]] = {}
            broken_rows: dict[int, list[str]] = {}

            for row_number, row in enumerate(rows):
                fixed_rows[row_number] = row
                if len(row) == max_key:
                    continue
                broken_rows[row_number] = row

            for row_number, row in broken_rows.items():
                if row_number == 0:
                    print("Skipping repair for row 0.")
                    continue
                print(f"Row {row_number} with {len(row)} columns: {row}")
                fixed_row = repair_csv_row(
                    row_number=row_number,
                    row=row,
                    neighboring_rows=_neighboring_rows(fixed_rows, row_number),
                    expected_column_count=max_key,
                )
                print(f"Fixed row {row_number}: {fixed_row}")
                fixed_rows[row_number] = fixed_row

            rows = [fixed_rows[row_number] for row_number in sorted(fixed_rows)]

    return _rows_to_dataframe(rows, dialect_config.has_header)
