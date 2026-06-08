import custom_csv
import io
import json
import os
import urllib.request
import pandas as pd


LLM_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"
LLM_MODEL = "gpt-5.4"


def dataframe_from_rows(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


def row_to_csv(row):
    if isinstance(row, str):
        return row
    buf = io.StringIO()
    writer = custom_csv.writer(buf, lineterminator="")
    writer.writerow(row)
    return buf.getvalue()


def parse_single_csv_row(text):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return None
    return next(custom_csv.reader([lines[0]]))


def call_llm(messages):
    api_key = os.environ.get("HEIMGARTEN_OPENAI_KEY")
    if not api_key:
        raise RuntimeError("HEIMGARTEN_OPENAI_KEY is not set")

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": messages,
    }).encode("utf-8")
    request = urllib.request.Request(
        LLM_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def example_rows_for_malformed(rows, malformed_line_num, n_examples=6):
    data_rows = rows[1:] if len(rows) > 1 else []
    if not data_rows:
        return []

    # line 2 is data row index 0. Malformed rows are skipped, so nearby parsed
    # rows after the malformed line are usually shifted left by one position.
    target_index = max(0, malformed_line_num - 2)
    before_start = max(0, target_index - n_examples // 2)
    examples = data_rows[before_start:before_start + n_examples]
    if len(examples) < n_examples:
        examples += data_rows[:n_examples - len(examples)]
    return examples[:n_examples]


def llm_repair_row(header, examples, malformed):
    raw = malformed.get("raw")
    reason = malformed.get("reason", "unknown")
    content = "\n".join([
        "Repair one malformed CSV row.",
        "Return exactly one CSV row and nothing else.",
        "The row must have exactly the same number of fields as the header.",
        "",
        f"Header: {row_to_csv(header)}",
        "",
        "Example correct rows:",
        *[row_to_csv(row) for row in examples],
        "",
        f"Malformed row reason: {reason}",
        f"Malformed raw row: {row_to_csv(raw)}",
    ])
    answer = call_llm([{"role": "user", "content": content}])
    repaired = parse_single_csv_row(answer)

    # print(f"content: {content}")
    # repaired = ", , , , , , , , "*len(raw)
    if repaired is None or len(repaired) != len(header):
        return None
    return repaired


def repair_rows_with_replacements(rows, replacements):
    if not rows:
        return pd.DataFrame()

    header = rows[0]
    parsed_data = rows[1:]
    malformed_lines = set(replacements)
    expected_good_rows = max(
        0,
        len(parsed_data) + len([line_num for line_num in malformed_lines if line_num > 1]),
    )

    repaired_data = []
    good_iter = iter(parsed_data)
    for line_num in range(2, expected_good_rows + 2):
        if line_num in replacements:
            repaired_data.append(replacements[line_num])
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

    return pd.DataFrame(repaired_data, columns=header)


def load_clean_rows(clean_csv: str):
    with open(clean_csv, newline='') as f:
        return list(custom_csv.reader(f))


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


def repair_with_llm(rows, malformed):
    if not rows or not malformed:
        return dataframe_from_rows(rows)

    header = rows[0]
    replacements = {}
    for entry in malformed:
        line_num = entry.get("line_num")
        if line_num is None:
            continue
        line_num = int(line_num)
        examples = example_rows_for_malformed(rows, line_num)
        try:
            repaired = llm_repair_row(header, examples, entry)
        except Exception:
            repaired = None
        if repaired is not None:
            replacements[line_num] = repaired

    if not replacements:
        return dataframe_from_rows(rows)
    return repair_rows_with_replacements(rows, replacements)


class ValidationReader:
    """Wraps custom_csv.reader to collect malformed rows instead of raising.

    Yields well-formed rows normally. After iteration, inspect
    ``malformed_rows`` for everything that went wrong:

      - C-level parse errors (unterminated quotes, etc.) come from the
        underlying reader's ``malformed_rows`` attribute.
      - Wrong field count (detected here at the Python level) is appended
        by this wrapper.

    Each entry is a dict with keys:
      ``line_num`` – 1-based line number in the source file
      ``raw``      – the raw line string (parse errors) or parsed field
                     list (wrong-count rows)
      ``reason``   – human-readable description of the problem
    """

    def __init__(self, f, expected_cols=None, dialect="excel", **fmtparams):
        self._reader = custom_csv.reader(f, dialect, **fmtparams)
        self._expected = expected_cols
        self._structural_malformed = []

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            row = next(self._reader)
            n = self._expected
            if n is not None and len(row) != n:
                self._structural_malformed.append({
                    'line_num': self._reader.line_num,
                    'raw': row,
                    'reason': f'expected {n} fields, got {len(row)}',
                })
                continue
            return row

    @property
    def malformed_rows(self):
        """Combined list of all malformed rows (parse errors + wrong column count)."""
        parse_errors = [
            {'line_num': line_num, 'raw': raw, 'reason': reason}
            for line_num, raw, reason in self._reader.malformed_rows
        ]
        return parse_errors + self._structural_malformed


def parse_csv_with_validation(csv_input: str, clean_csv: str = None, cheat: bool = False, llm_repair: bool = False):
    """
    Parse a CSV, skipping malformed rows.

    Returns:
        (DataFrame of good rows, list of malformed row dicts)
        Each malformed dict has keys: line_num, raw, reason.
    """
    with open(csv_input, newline='') as f:
        try:
            expected_cols = len(next(custom_csv.reader(f)))
        except StopIteration:
            return pd.DataFrame(), []
        f.seek(0)
        vr = ValidationReader(f, expected_cols=expected_cols, strict=True)
        rows = list(vr)
        malformed = vr.malformed_rows
    if not rows:
        return pd.DataFrame(), malformed
    if cheat and malformed and clean_csv is not None:
        return repair_with_ground_truth(rows, malformed, clean_csv), malformed
    if llm_repair and malformed and len(malformed) < 10:
        return repair_with_llm(rows, malformed), malformed
    return dataframe_from_rows(rows), malformed
