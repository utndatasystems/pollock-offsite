import json
import os
import tempfile
import time
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from dialect import CSVDialect, parse_record
from llm import _extract_json_object, call_llm


DEFAULT_REPAIR_PROMPT = """
Repair faulty CSV records. Return JSON only, no Markdown, no commentary.
For each input line, output the repaired content as a list of field values, not as CSV text.
Return unescaped field values.
Do not CSV-escape inside field values.
JSON escaping is allowed only because the response is JSON.
""".strip()

SPECIAL_REPAIR_PROMPT = """
Repair faulty CSV records. Return JSON only, no Markdown, no commentary.
For each input line, return the respective field values, not CSV text.
Do not CSV-escape inside field values; JSON escaping is allowed only because the response is JSON.

Use the good examples as a guide for alignment, order of the data cells by looking at patterns and semantics.
Don't do cleaning of cell data, so keep accidental double whitespaces, typos etc.
Dialect delimiters at the start or end of a row as well as double delimiters in the middle of a row denote empty fields. These should be preserved and included as an empty string in your output list. Only drop them if they shift the columns in a way that would not be consistent with the example rows or that would break the expected number of columns.
Keep in mind that literal quote characters in field text are escaped with the escape character that can also be a quote. In this case, keep one as literal field text. 
Also keep faulty non-escaped quote characters e.g. those that are just opened and never closed.

Priority order: exactly hit the expected column count; each value fits its column semantically (e.g. from header or example rows); preserve original cell text.
""".strip()


def _repair_instruction_text(special_prompt: bool) -> str:
    if not special_prompt:
        return DEFAULT_REPAIR_PROMPT

    return SPECIAL_REPAIR_PROMPT


def _unique_duckdb_columns(count: int) -> Dict[str, str]:
    return {f"_c{i}": "VARCHAR" for i in range(count)}


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_bool(value: bool) -> str:
    return "true" if value else "false"


def _sql_columns(columns: Dict[str, str]) -> str:
    parts = [f"{_sql_string(name)}: {_sql_string(dtype)}" for name, dtype in columns.items()]
    return "{" + ", ".join(parts) + "}"


def _records_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    clean_df = df.astype(object).where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def _strip_leading_lines(csv_input: str, n_lines: int) -> str:
    """Write a temp copy of csv_input with the first n_lines physical lines removed.

    The remainder is copied byte-for-byte (line endings, later-line content, etc.
    preserved) so DuckDB parses the data region identically to the original minus the
    skipped rows.
    """
    with open(csv_input, "rb") as fh:
        data = fh.read()
    idx = 0
    for _ in range(n_lines):
        nl = data.find(b"\n", idx)
        if nl == -1:
            idx = len(data)
            break
        idx = nl + 1
    tmp = tempfile.NamedTemporaryFile(
        "wb", prefix="pollock_stripped_", suffix=".csv", delete=False
    )
    try:
        tmp.write(data[idx:])
    finally:
        tmp.close()
    return tmp.name


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def load_with_duckdb(
    csv_input: str,
    dialect: CSVDialect,
    expected_columns: int,
    trace: Any,
    stage: str,
    store_rejects: bool = True,
    strip_skipped: bool = False,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], List[Dict[str, Any]]]:
    import duckdb

    conn = duckdb.connect(database=":memory:")
    scan_table = f"reject_scans_{stage}_{os.getpid()}_{int(time.time() * 1000000)}"
    rejects_table = f"reject_errors_{stage}_{os.getpid()}_{int(time.time() * 1000000)}"
    columns = _unique_duckdb_columns(expected_columns)
    skip_rows = dialect.preamble_rows + dialect.header_rows
    # DuckDB's `skip` still tokenizes the skipped lines, so a malformed (e.g. unterminated
    # quote) preamble/header can bleed into the first data rows or silently drop everything.
    # When asked, physically remove those lines and read the remainder with skip=0 instead.
    stripped_path = (
        _strip_leading_lines(csv_input, skip_rows) if strip_skipped and skip_rows > 0 else None
    )
    read_path = stripped_path if stripped_path is not None else csv_input
    effective_skip = 0 if stripped_path is not None else skip_rows
    options = {
        "auto_detect": False,
        "delim": dialect.delimiter,
        "quote": dialect.quotechar or "",
        "escape": dialect.escapechar or "",
        "header": False,
        "skip": effective_skip,
        "columns": columns,
        "store_rejects": bool(store_rejects),
        "rejects_scan": scan_table,
        "rejects_table": rejects_table,
        "rejects_limit": 0,
        "strict_mode": True,
        "null_padding": False,
        "parallel": False,
    }
    csv_args = [
        _sql_string(read_path),
        "auto_detect = false",
        f"delim = {_sql_string(dialect.delimiter)}",
        f"quote = {_sql_string(dialect.quotechar or '')}",
        f"escape = {_sql_string(dialect.escapechar or '')}",
        "header = false",
        f"skip = {effective_skip}",
        f"columns = {_sql_columns(columns)}",
        f"store_rejects = {_sql_bool(bool(store_rejects))}",
        f"rejects_scan = {_sql_string(scan_table)}",
        f"rejects_table = {_sql_string(rejects_table)}",
        "rejects_limit = 0",
        "strict_mode = true",
        "null_padding = false",
        "parallel = false",
    ]
    if dialect.newline:
        options["new_line"] = dialect.newline
        csv_args.append(f"new_line = {_sql_string(dialect.newline)}")
    sql = "SELECT * FROM read_csv(" + ", ".join(csv_args) + ")"

    trace.write(
        "duckdb_load_start",
        stage=stage,
        path=csv_input,
        stripped=stripped_path is not None,
        options={k: v for k, v in options.items() if k != "columns"},
        columns=list(options["columns"].keys()),
    )
    try:
        df = conn.execute(sql).df()
    except Exception as exc:
        trace.write("duckdb_load_error", stage=stage, error=str(exc), sql=sql)
        if stripped_path is not None:
            _safe_unlink(stripped_path)
        raise

    scans: List[Dict[str, Any]] = []
    rejects: List[Dict[str, Any]] = []
    if store_rejects:
        try:
            scans = _records_from_df(conn.execute(f"SELECT * FROM {scan_table}").df())
        except Exception as exc:
            trace.write("duckdb_reject_scans_error", stage=stage, error=str(exc))
        try:
            rejects_df = conn.execute(
                f"SELECT * FROM {rejects_table} ORDER BY line, byte_position, column_idx"
            ).df()
            rejects = _records_from_df(rejects_df)
        except Exception as exc:
            trace.write("duckdb_reject_errors_error", stage=stage, error=str(exc))

    if stripped_path is not None:
        # Reject line numbers are relative to the stripped copy (read with skip=0). Shift
        # them back by skip_rows so downstream reject/repair bookkeeping matches the
        # original file, exactly as if we had read it with skip=skip_rows.
        for reject in rejects:
            if reject.get("line") is not None:
                try:
                    reject["line"] = int(reject["line"]) + skip_rows
                except (TypeError, ValueError):
                    pass
        _safe_unlink(stripped_path)

    trace.write(
        "duckdb_load_result",
        stage=stage,
        rows=len(df),
        columns=list(df.columns),
        reject_scans=scans,
        reject_errors=rejects,
    )
    return df, rejects, scans


def _coerce_cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def finalize_dataframe(df: pd.DataFrame, header: List[str], has_header: bool) -> pd.DataFrame:
    df = df.copy()
    df = df.astype(object).where(pd.notna(df), "")

    if has_header:
        if len(header) == len(df.columns):
            df.columns = header
        return df

    if df.empty:
        return pd.DataFrame()

    first_row = [_coerce_cell(value) for value in df.iloc[0].tolist()]
    output = df.iloc[1:].reset_index(drop=True)
    output.columns = first_row
    return output


def _clean_duckdb_csv_line(value: Any) -> Any:
    if isinstance(value, str):
        return value.lstrip("\r\n")
    return value


def rejects_to_malformed(rejects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_line: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
    for reject in rejects:
        line = reject.get("line")
        if line is None:
            continue
        line_num = int(line)
        entry = by_line.setdefault(
            line_num,
            {
                "line_num": line_num,
                "raw": _clean_duckdb_csv_line(reject.get("csv_line")),
                "errors": [],
            },
        )
        error_type = reject.get("error_type") or "CSV"
        message = reject.get("error_message") or ""
        entry["errors"].append(f"{error_type}: {message}".strip())
        if entry.get("raw") is None and reject.get("csv_line") is not None:
            entry["raw"] = _clean_duckdb_csv_line(reject.get("csv_line"))

    malformed = []
    for entry in by_line.values():
        malformed.append({
            "line_num": entry["line_num"],
            "raw": entry.get("raw"),
            "reason": "; ".join(entry["errors"]) or "CSV reject",
        })
    return malformed


def _scan_rows_by_width(
    csv_input: str, dialect: CSVDialect, expected_columns: int
) -> Tuple[List[Tuple[int, List[str]]], List[Dict[str, Any]]]:
    """Single pass over data lines, classifying each by parse_record width.

    Returns (good_rows, rejects): good_rows are (line_num, fields) with exactly
    expected_columns; rejects are the width-mismatch reject dicts.
    """
    good_rows: List[Tuple[int, List[str]]] = []
    rejects: List[Dict[str, Any]] = []
    skip_rows = dialect.preamble_rows + dialect.header_rows
    with open(csv_input, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for line_num, line in enumerate(f, start=1):
            if line_num <= skip_rows:
                continue
            raw, _ = _split_line_ending(line, "")
            if raw == "":
                continue
            fields = parse_record(raw, dialect)
            if len(fields) == expected_columns:
                good_rows.append((line_num, fields))
                continue
            error_type = "TOO MANY COLUMNS" if len(fields) > expected_columns else "MISSING COLUMNS"
            rejects.append({
                "line": line_num,
                "line_byte_position": None,
                "byte_position": None,
                "column_idx": None,
                "column_name": None,
                "error_type": error_type,
                "csv_line": raw,
                "error_message": f"Expected Number of Columns: {expected_columns} Found: {len(fields)}",
                "source": "local_width_validation",
            })
    return good_rows, rejects


def find_width_rejects(csv_input: str, dialect: CSVDialect, expected_columns: int) -> List[Dict[str, Any]]:
    _, rejects = _scan_rows_by_width(csv_input, dialect, expected_columns)
    return rejects


def merge_rejects(*reject_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for rejects in reject_groups:
        for reject in rejects:
            key = (
                int(reject["line"]) if reject.get("line") is not None else None,
                reject.get("error_type"),
                reject.get("error_message"),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(reject)
    merged.sort(key=lambda item: (
        int(item["line"]) if item.get("line") is not None else 10**12,
        str(item.get("error_type") or ""),
        str(item.get("error_message") or ""),
    ))
    return merged


def _good_examples(
    csv_input: str,
    dialect: CSVDialect,
    expected_columns: int,
    reject_lines: set,
    limit: int,
) -> List[Dict[str, Any]]:
    """LLM alignment examples: rows both parsers accept.

    _scan_rows_by_width already width-verifies each line (shared with
    find_width_rejects); we additionally drop any line in reject_lines (the merged
    reject set), which for a width-matched row means DuckDB rejected it. So a
    lucky-count misparse DuckDB accepts but the width check rejects (e.g. a
    space-split "Tropic Cap") never reaches the prompt as a good example.
    """
    if limit <= 0:
        return []
    good_rows, _ = _scan_rows_by_width(csv_input, dialect, expected_columns)
    examples: List[Dict[str, Any]] = []
    for line_num, fields in good_rows:
        if line_num in reject_lines:
            continue
        examples.append({"fields": [_coerce_cell(value) for value in fields]})
        if len(examples) >= limit:
            break
    return examples


def _dedupe_rejects_for_prompt(rejects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
    for reject in rejects:
        if reject.get("line") is None:
            continue
        line = int(reject["line"])
        item = grouped.setdefault(
            line,
            {
                "line": line,
                "raw": _clean_duckdb_csv_line(reject.get("csv_line")),
                "errors": [],
            },
        )
        item["errors"].append({
            "type": reject.get("error_type"),
            "message": reject.get("error_message"),
            "column_idx": reject.get("column_idx"),
            "column_name": reject.get("column_name"),
        })
    return list(grouped.values())


def _record_line_span(raw: str, dialect: CSVDialect, errors: List[Dict[str, Any]]) -> int:
    # How many physical lines of the file the record occupies. A line break
    # inside a quoted field belongs to that field and is not a line of its own.
    # We cannot tell that from the text once quoting is broken, so we rely on
    # DuckDB reporting an unterminated quote: from there the quote state is
    # meaningless and every break really is a separate line of the file.
    unterminated = any(
        str(error.get("type") or "").upper() == "UNQUOTED VALUE" for error in errors
    )
    quote = dialect.quotechar
    escape = dialect.escapechar
    breaks = 0
    in_quotes = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in "\r\n":
            if ch == "\r" and raw[i + 1:i + 2] == "\n":
                i += 1
            if unterminated or not in_quotes:
                breaks += 1
        elif quote and ch == quote:
            if in_quotes and escape == quote and raw[i + 1:i + 2] == quote:
                i += 1  # doubled quote is literal text, not a delimiter
            else:
                in_quotes = not in_quotes
        elif escape and escape != quote and ch == escape:
            i += 1  # skip the escaped character
        i += 1
    return breaks + 1


def infer_repairs_with_llm(
    header: List[str],
    dialect: CSVDialect,
    csv_input: str,
    rejects: List[Dict[str, Any]],
    context_lines: int,
    trace: Any,
    special_prompt: bool = False,
) -> Dict[int, Dict[str, Any]]:
    faulty_lines = _dedupe_rejects_for_prompt(rejects)
    if not faulty_lines:
        return {}

    reject_lines = {int(r["line"]) for r in rejects if r.get("line") is not None}
    prompt_payload = {
        "expected_column_count": len(header),
        "columns": header,
        "dialect": dialect.as_trace_dict(),
        "good_examples": _good_examples(csv_input, dialect, len(header), reject_lines, context_lines),
        "faulty_lines": faulty_lines,
    }
    prompt = "\n".join([
        _repair_instruction_text(special_prompt),
        "",
        "Response shape:",
        '{"repairs": [{"line": <line number>, "fields": [<string>, ...]}]}',
        "",
        "Input:",
        json.dumps(prompt_payload, ensure_ascii=False),
    ])

    # Estimate: output is repaired fields ≈ size of raw faulty lines + JSON overhead per item
    estimated_output = sum(len(fl.get("raw") or "") for fl in faulty_lines) + len(faulty_lines) * 30
    answer = call_llm(prompt, trace, "llm_faulty_line_repair", estimated_output_chars=estimated_output)
    try:
        parsed = _extract_json_object(answer)
    except Exception as exc:
        trace.write("llm_faulty_line_parse_error", error=str(exc), response=answer)
        return {}

    repairs_raw: Iterable[Any]
    if isinstance(parsed, dict):
        repairs_raw = parsed.get("repairs", [])
    elif isinstance(parsed, list):
        repairs_raw = parsed
    else:
        repairs_raw = []

    # One faulty record can cover several physical lines (an unterminated quote
    # swallows the following line), and the LLM then returns one repair per
    # recovered row. Remember how many lines the original record covered so the
    # whole span can be replaced.
    spans = {
        int(item["line"]): _record_line_span(
            str(item.get("raw") or ""), dialect, item.get("errors") or []
        )
        for item in faulty_lines
    }

    repairs: Dict[int, Dict[str, Any]] = {}
    rejected_repairs = []
    for item in repairs_raw:
        if not isinstance(item, dict):
            rejected_repairs.append({"item": item, "reason": "not an object"})
            continue
        try:
            line = int(item.get("line"))
        except Exception:
            rejected_repairs.append({"item": item, "reason": "missing integer line"})
            continue
        fields = item.get("fields")
        if not isinstance(fields, list):
            rejected_repairs.append({"item": item, "reason": "fields is not a list"})
            continue
        if len(fields) != len(header):
            rejected_repairs.append({
                "line": line,
                "reason": f"expected {len(header)} fields, got {len(fields)}",
                "fields": fields,
            })
            continue
        entry = repairs.setdefault(line, {"records": [], "span": spans.get(line, 1)})
        entry["records"].append([_coerce_cell(value) for value in fields])

    trace.write(
        "llm_faulty_line_repairs_parsed",
        repairs=[
            {"line": line, "fields": fields}
            for line, entry in repairs.items()
            for fields in entry["records"]
        ],
        rejected=rejected_repairs,
    )
    return repairs

def _needs_quotes(value: str, dialect: CSVDialect) -> bool:
    if value == "":
        return False
    if dialect.delimiter and dialect.delimiter in value:
        return True
    if dialect.quotechar and dialect.quotechar in value:
        return True
    if "\n" in value or "\r" in value:
        return True
    if value != value.strip(" "):
        return True
    return False


def serialize_record(fields: List[str], dialect: CSVDialect) -> str:
    delimiter = dialect.delimiter
    quote = dialect.quotechar
    escape = dialect.escapechar or dialect.quotechar
    serialized = []
    for field in fields:
        value = _coerce_cell(field)
        if not quote or not _needs_quotes(value, dialect):
            serialized.append(value)
            continue
        if escape == quote:
            escaped = value.replace(quote, quote + quote)
        else:
            escaped = value.replace(quote, (escape or "") + quote)
        serialized.append(f"{quote}{escaped}{quote}")
    return delimiter.join(serialized)


def _split_line_ending(line: str, default_newline: str) -> Tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, default_newline


def _detect_file_newline(lines: List[str], dialect: CSVDialect) -> str:
    if dialect.newline:
        return dialect.newline
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
        if line.endswith("\r"):
            return "\r"
    return "\n"


def write_repaired_copy(
    csv_input: str,
    repairs: Dict[int, Dict[str, Any]],
    dialect: CSVDialect,
    trace: Any,
) -> Optional[str]:
    if not repairs:
        return None

    with open(csv_input, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        lines = f.readlines()
    default_newline = _detect_file_newline(lines, dialect)

    applied = []
    # Bottom-up: a record can expand into a different number of lines, which
    # would shift the indexes of the repairs still to come.
    for line_num in sorted(repairs, reverse=True):
        entry = repairs[line_num]
        idx = line_num - 1
        if idx < 0 or idx >= len(lines):
            continue
        _, newline = _split_line_ending(lines[idx], default_newline)
        span = max(1, int(entry.get("span", 1)))
        repaired_lines = [serialize_record(fields, dialect) for fields in entry["records"]]
        lines[idx:idx + span] = [line + newline for line in repaired_lines]
        for repaired_line, fields in zip(repaired_lines, entry["records"]):
            applied.append({"line": line_num, "serialized": repaired_line, "fields": fields})
    applied.sort(key=lambda item: item["line"])

    if not applied:
        return None

    tmp = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        prefix="pollock_custom_repaired_",
        suffix=".csv",
        delete=False,
    )
    try:
        tmp.writelines(lines)
    finally:
        tmp.close()
    trace.write("repaired_copy_written", path=tmp.name, applied=applied)
    return tmp.name


def load_clean_dataframe(clean_csv: str) -> pd.DataFrame:
    try:
        return pd.read_csv(clean_csv, dtype=str, keep_default_na=False, na_filter=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def splice_clean_rows(
    df: pd.DataFrame,
    clean_df: pd.DataFrame,
    malformed_indices: set,
    duckdb_skipped_indices: set,
) -> pd.DataFrame:
    """Replace rows at malformed_indices with rows from clean_df.

    duckdb_skipped_indices: subset of malformed_indices where DuckDB actually
    excluded the row from df. For rows only caught by find_width_rejects, DuckDB
    still loaded them, so they ARE in df and must be skipped (replaced in-place)
    rather than inserted.
    """
    if not malformed_indices or clean_df.empty:
        return df

    total = len(clean_df)
    valid_malformed = {i for i in malformed_indices if 0 <= i < total}
    rows = []
    good_idx = 0
    for i in range(total):
        if i in valid_malformed:
            rows.append(clean_df.iloc[i].tolist())
            if i not in duckdb_skipped_indices:
                # Row is present in df (loaded by DuckDB despite the error) — skip over it
                good_idx += 1
        else:
            if good_idx < len(df):
                rows.append(df.iloc[good_idx].tolist())
                good_idx += 1
            else:
                rows.append(clean_df.iloc[i].tolist())

    return pd.DataFrame(rows, columns=clean_df.columns)
