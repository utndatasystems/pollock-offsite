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


def llm_repair_row(header, examples, malformed, sidecar_path=None, dialect_kwargs=None):
    raw = malformed.get("raw")
    reason = malformed.get("reason", "unknown")

    if dialect_kwargs:
        dialect_desc = ", ".join(f"{k}={repr(v)}" for k, v in dialect_kwargs.items())
        dialect_lines = [
            f"The raw row below was read using this auto-inferred file dialect: {dialect_desc}",
            'Your repaired output MUST use standard CSV: double-quote (") as quotechar, "" to escape a literal quote inside a field.',
            "",
        ]
    else:
        dialect_lines = []

    content = "\n".join([
        "Repair one malformed CSV row. Fix only the CSV structural problem — nothing else.",
        "Return exactly one CSV row and nothing else.",
        "The row must have exactly the same number of fields as the header.",
        "",
        *dialect_lines,
        "CRITICAL — preserving field content is the highest priority:",
        "Every character that belongs to a field value MUST appear in your output.",
        "For quote characters specifically, apply this rule:",
        "  - A quote in the MIDDLE of a field value is always content — preserve and encode it (e.g. as \"\").",
        "  - A quote at the END of a field with no matching opening quote at the start is content — preserve it.",
        "  - A quote at the START of a field with no matching closing quote at the end is content — preserve it.",
        "  - Only a MATCHED pair (quote at the start AND a corresponding quote at the end) is structural",
        "    (it is the field's own quoting mechanism) — do not treat those boundary quotes as literal content.",
        "Silently dropping any character from a field — including a mid-field quote, a backslash,",
        "a space, or a typo — is a worse outcome than leaving the row malformed.",
        "When in doubt, keep the character and encode it properly rather than remove it.",
        "",
        "Also do NOT fix or normalise anything else inside field content: preserve typos,",
        "double spaces, unusual capitalisation, and backslash characters that are part of the",
        "field value but are not causing the structural CSV error.",
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

    if sidecar_path:
        with open(sidecar_path, "a", encoding="utf-8") as sf:
            sf.write(json.dumps({
                "line_num": malformed.get("line_num"),
                "prompt": content,
                "response": answer,
            }) + "\n")

    repaired = parse_single_csv_row(answer)
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


def llm_inspect_header(csv_input: str, dialect_kwargs: dict, sidecar_path: str = None) -> dict:
    """Ask the LLM how many leading rows are header, whether the header has structural errors,
    and whether the auto-inferred quotechar/escapechar look correct.

    Returns dict with:
      header_rows  – int >= 1, number of leading rows that are header material
      header_error – str describing a structural CSV error in the header, or None
      quotechar    – str to override the sniffed quotechar, or None to keep it unchanged
      escapechar   – str to override the sniffed escapechar, or None to keep it unchanged
                     (use "" for either to mean "no quotechar/escapechar")
    """
    with open(csv_input, encoding='utf-8', errors='replace') as f:
        first_lines = [f.readline() for _ in range(6)]
    first_lines = [line.rstrip('\n\r') for line in first_lines if line]

    dialect_desc = (
        ", ".join(f"{k}={repr(v)}" for k, v in dialect_kwargs.items())
        if dialect_kwargs else "none detected"
    )

    prompt = "\n".join([
        "You are analyzing the beginning of a CSV file.",
        "",
        "Auto-inferred dialect (treat as a hint only — not confirmed correct):",
        f"  {dialect_desc}",
        "",
        "First rows of the file (raw, unprocessed lines):",
        *[f"  row {i + 1}: {line}" for i, line in enumerate(first_lines)],
        "",
        "Answer four questions:",
        "1. How many of these leading rows are part of the header (column names, sub-headers,",
        "   or descriptive rows before actual data begins)? Typically 1.",
        "2. Is there a structural CSV error in any header row — for example a missing delimiter,",
        "   malformed quoting, or a field count that does not match the rest of the file?",
        "   If so, describe it concisely. Otherwise return null.",
        "3. Does the auto-inferred quotechar look correct given the raw lines?",
        "   If not, return the correct character (e.g. \"'\" or '\"').",
        "   Return \"\" if there is no quote character. Return null to leave it unchanged.",
        "   Only override if you are confident from the raw data.",
        "4. Does the auto-inferred escapechar look correct given the raw lines?",
        "   If not, return the correct character (e.g. \"\\\\\").",
        "   Return \"\" if there is no escape character. Return null to leave it unchanged.",
        "   Only override if you are confident from the raw data.",
        "",
        "Respond with JSON only, no prose.",
        'Format: {"header_rows": <int>, "header_error": <string or null>, "quotechar": <string or null>, "escapechar": <string or null>}',
    ])

    answer = call_llm([{"role": "user", "content": prompt}])

    if sidecar_path:
        with open(sidecar_path, "a", encoding="utf-8") as sf:
            sf.write(json.dumps({
                "type": "header_inspection",
                "prompt": prompt,
                "response": answer,
            }) + "\n")

    try:
        start = answer.find('{')
        end = answer.rfind('}')
        result = json.loads(answer[start:end + 1])
        return {
            "header_rows": max(1, int(result.get("header_rows", 1))),
            "header_error": result.get("header_error") or None,
            "quotechar": result.get("quotechar"),
            "escapechar": result.get("escapechar"),
        }
    except Exception:
        return {"header_rows": 1, "header_error": None, "quotechar": None, "escapechar": None}


def sniff_dialect(csv_input):
    import clevercsv
    with open(csv_input, newline='', encoding='utf-8', errors='replace') as f:
        sample = f.read(8192)
    dialect = clevercsv.Sniffer().sniff(sample)
    if dialect is None:
        return {}
    kwargs = {}
    if dialect.delimiter:
        kwargs['delimiter'] = dialect.delimiter
    if dialect.quotechar:
        kwargs['quotechar'] = dialect.quotechar
    if dialect.escapechar:
        kwargs['escapechar'] = dialect.escapechar
    return kwargs


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


def repair_with_llm(rows, malformed, sidecar_path=None, dialect_kwargs=None):
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
            repaired = llm_repair_row(header, examples, entry, sidecar_path=sidecar_path, dialect_kwargs=dialect_kwargs)
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


def parse_csv_with_validation(csv_input: str, clean_csv: str = None, cheat: bool = False, llm_repair: bool = False, sidecar_path: str = None):
    """
    Parse a CSV, skipping malformed rows.

    Returns:
        (DataFrame of good rows, list of malformed row dicts)
        Each malformed dict has keys: line_num, raw, reason.
    """
    dialect_kwargs = sniff_dialect(csv_input)
    sniffed_dialect = dict(dialect_kwargs)
    if llm_repair and sidecar_path is None:
        sidecar_path = csv_input + ".llm.jsonl"

    header_info = (
        llm_inspect_header(csv_input, dialect_kwargs, sidecar_path=sidecar_path)
        if llm_repair
        else {"header_rows": 1, "header_error": None, "quotechar": None, "escapechar": None}
    )

    for key in ("quotechar", "escapechar"):
        val = header_info.get(key)
        if val is None:
            continue
        if val == "":
            dialect_kwargs.pop(key, None)
        else:
            dialect_kwargs[key] = val

    if sidecar_path:
        with open(sidecar_path, "a", encoding="utf-8") as sf:
            sf.write(json.dumps({
                "type": "dialect",
                "sniffed": sniffed_dialect,
                "final": dict(dialect_kwargs),
                "llm_corrections": {
                    k: header_info.get(k)
                    for k in ("quotechar", "escapechar")
                    if header_info.get(k) is not None
                },
            }) + "\n")

    with open(csv_input, newline='') as f:
        try:
            expected_cols = len(next(custom_csv.reader(f, **dialect_kwargs)))
        except StopIteration:
            return pd.DataFrame(), []
        f.seek(0)
        vr = ValidationReader(f, expected_cols=expected_cols, strict=True, **dialect_kwargs)
        rows = list(vr)
        malformed = vr.malformed_rows

    if not rows:
        return pd.DataFrame(), malformed

    extra_header_rows = header_info["header_rows"] - 1
    if extra_header_rows > 0 and len(rows) > extra_header_rows:
        rows = [rows[0]] + rows[1 + extra_header_rows:]

    if header_info["header_error"]:
        malformed = [{
            "line_num": 1,
            "raw": rows[0],
            "reason": f"header: {header_info['header_error']}",
        }] + malformed

    if cheat and malformed and clean_csv is not None:
        return repair_with_ground_truth(rows, malformed, clean_csv), malformed
    if llm_repair and malformed and len(malformed) < 10:
        return repair_with_llm(rows, malformed, sidecar_path=sidecar_path, dialect_kwargs=dialect_kwargs), malformed
    return dataframe_from_rows(rows), malformed
