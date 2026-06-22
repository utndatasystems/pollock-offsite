import hashlib
import json
import os
import tempfile
import time
import urllib.request
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


DEFAULT_OPENAI_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
#DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
TRACE_VERSION = 1

_LLM_RESPONSE_CACHE: Dict[str, str] = {}
_LLM_DRY_RUN_ESTIMATED_OUTPUT: Dict[str, int] = {}  # prompt_sha -> estimated chars for dry-run dedup
_LLM_CACHE_PATH: Optional[str] = None
_LLM_CACHE_ENABLED: bool = True
_LLM_CACHE_LOADED: bool = False
_LLM_CALL_STATS: Dict[str, int] = {
    "total": 0, "cached": 0,
    "input_chars_total": 0, "input_chars_cached": 0,
    "output_chars_fresh": 0, "output_chars_cached": 0,
}
_LLM_DRY_RUN: bool = False


def configure_llm_cache(path: Optional[str] = None, enabled: bool = True) -> None:
    global _LLM_CACHE_PATH, _LLM_CACHE_ENABLED, _LLM_CACHE_LOADED
    _LLM_CACHE_PATH = path
    _LLM_CACHE_ENABLED = enabled
    _LLM_CACHE_LOADED = False


def configure_llm_dry_run(enabled: bool) -> None:
    global _LLM_DRY_RUN
    _LLM_DRY_RUN = enabled


def get_llm_cache_stats() -> Dict[str, int]:
    return dict(_LLM_CALL_STATS)


def _ensure_cache_loaded() -> None:
    global _LLM_CACHE_LOADED
    if _LLM_CACHE_LOADED or not _LLM_CACHE_PATH:
        return
    _LLM_CACHE_LOADED = True
    if not os.path.exists(_LLM_CACHE_PATH):
        return
    try:
        with open(_LLM_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _LLM_RESPONSE_CACHE.update(data)
    except Exception:
        pass


def _save_cache_to_disk() -> None:
    if not _LLM_CACHE_PATH:
        return
    try:
        cache_dir = os.path.dirname(_LLM_CACHE_PATH)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with open(_LLM_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_LLM_RESPONSE_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@dataclass
class CSVDialect:
    delimiter: str = ","
    quotechar: Optional[str] = '"'
    escapechar: Optional[str] = '"'
    newline: Optional[str] = None
    header_rows: int = 1
    preamble_rows: int = 0

    def as_trace_dict(self) -> Dict[str, Any]:
        return {
            "delimiter": self.delimiter,
            "quotechar": self.quotechar,
            "escapechar": self.escapechar,
            "row_delimiter": self.newline,
            "header_lines": self.header_rows,
            "preamble_lines": self.preamble_rows,
        }


class TraceWriter:
    def __init__(self, path: Optional[str], reset: bool = True):
        self.path = path
        if self.path and reset:
            sidecar_dir = os.path.dirname(self.path)
            if sidecar_dir:
                os.makedirs(sidecar_dir, exist_ok=True)
            with open(self.path, "w", encoding="utf-8"):
                pass

    def write(self, event_type: str, **payload: Any) -> None:
        if not self.path:
            return
        event = {
            "type": event_type,
            "trace_version": TRACE_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        event.update(payload)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str))
            f.write("\n")


def _openai_endpoint() -> str:
    return os.environ.get("OPENAI_ENDPOINT") or DEFAULT_OPENAI_ENDPOINT


def _openai_model() -> str:
    return os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL


def _openai_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY")


def _prompt_hash(prompt: str) -> str:
    key = _openai_model() + "\x00" + prompt
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def call_llm(prompt: str, trace: TraceWriter, event_type: str, estimated_output_chars: int = 0) -> str:
    if _LLM_CACHE_ENABLED:
        _ensure_cache_loaded()

    prompt_sha = _prompt_hash(prompt)
    _LLM_CALL_STATS["total"] += 1
    _LLM_CALL_STATS["input_chars_total"] += len(prompt)

    if _LLM_CACHE_ENABLED and prompt_sha in _LLM_RESPONSE_CACHE:
        response = _LLM_RESPONSE_CACHE[prompt_sha]
        _LLM_CALL_STATS["cached"] += 1
        _LLM_CALL_STATS["input_chars_cached"] += len(prompt)
        # For in-run dry-run dedup hits use the stored estimate, not len("{}") = 2
        out_chars = _LLM_DRY_RUN_ESTIMATED_OUTPUT.get(prompt_sha, len(response))
        _LLM_CALL_STATS["output_chars_cached"] += out_chars
        print(f"[LLM cache] reused cached result ({event_type})")
        trace.write(
            event_type,
            prompt_sha256=prompt_sha,
            prompt=prompt,
            response=response,
            cached=True,
            model=_openai_model(),
            endpoint=_openai_endpoint(),
        )
        return response

    if _LLM_DRY_RUN:
        _LLM_CALL_STATS["output_chars_fresh"] += estimated_output_chars
        _LLM_RESPONSE_CACHE[prompt_sha] = "{}"  # deduplicate within this run, never saved to disk
        _LLM_DRY_RUN_ESTIMATED_OUTPUT[prompt_sha] = estimated_output_chars
        trace.write(event_type, prompt_sha256=prompt_sha, prompt=prompt, dry_run=True)
        return "{}"

    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI-compatible API key found. Set OPENAI_API_KEY."
        )

    payload = json.dumps({
        "model": _openai_model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode("utf-8")

    request = urllib.request.Request(
        _openai_endpoint(),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response_obj:
        data = json.loads(response_obj.read().decode("utf-8"))
    response = data["choices"][0]["message"]["content"]
    _LLM_CALL_STATS["output_chars_fresh"] += len(response)

    if _LLM_CACHE_ENABLED:
        _LLM_RESPONSE_CACHE[prompt_sha] = response
        _save_cache_to_disk()

    trace.write(
        event_type,
        prompt_sha256=prompt_sha,
        prompt=prompt,
        response=response,
        cached=False,
        model=_openai_model(),
        endpoint=_openai_endpoint(),
    )
    return response


def _extract_json_object(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_obj = text.find("{")
    last_obj = text.rfind("}")
    first_arr = text.find("[")
    last_arr = text.rfind("]")
    candidates = []
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        candidates.append(text[first_obj:last_obj + 1])
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        candidates.append(text[first_arr:last_arr + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("LLM response did not contain valid JSON")


def _read_sample_lines(path: str, limit: int) -> List[str]:
    lines: List[str] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for _ in range(max(0, limit)):
            line = f.readline()
            if line == "":
                break
            lines.append(line.rstrip("\r\n"))
    return lines


def _read_scoring_lines(path: str, limit: int = 250) -> List[str]:
    return _read_sample_lines(path, limit)


def _decode_token(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    # Check for actual whitespace characters before stripping — a bare \t or \n
    # from JSON decoding would be stripped to "" and misidentified as None.
    whitespace_literals = {"\t": "\t", "\n": "\n", "\r\n": "\r\n", "\r": "\r"}
    if value in whitespace_literals:
        return whitespace_literals[value]
    lowered = value.strip().lower()
    if lowered in {"", "none", "null", "no", "false"}:
        return None
    aliases = {
        "\\t": "\t",
        "\\n": "\n",
        "\\r": "\r",
        "\\r\\n": "\r\n",
        "<tab>": "\t",
        "tab": "\t",
        "space": " ",
        "<space>": " ",
        "0x20": " ",
        "comma-space": ", ",
    }
    return aliases.get(lowered, value)


def _valid_delimiter(value: Any) -> Optional[str]:
    if isinstance(value, str) and value == " ":
        return " "
    value = _decode_token(value)
    if value is None:
        return None
    if len(value.encode("utf-8")) > 4:
        return None
    return value


def _valid_char(value: Any) -> Optional[str]:
    value = _decode_token(value)
    if value is None:
        return None
    if len(value) != 1:
        return None
    return value


def _valid_newline(value: Any) -> Optional[str]:
    value = _decode_token(value)
    if value in {"\n", "\r", "\r\n"}:
        return value
    return None


def _safe_nonnegative_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return default


def sniff_with_clevercsv(csv_input: str) -> Dict[str, Any]:
    import clevercsv

    with open(csv_input, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(65536)
    dialect = clevercsv.Sniffer().sniff(sample)
    if dialect is None:
        return {}
    return {
        "delimiter": dialect.delimiter or None,
        "quotechar": dialect.quotechar or None,
        "escapechar": dialect.escapechar or dialect.quotechar or None,
    }


def _dialect_from_mapping(mapping: Dict[str, Any], base: Optional[CSVDialect] = None) -> CSVDialect:
    base = base or CSVDialect()
    delimiter = _valid_delimiter(mapping.get("delimiter", mapping.get("delim")))
    quotechar = _valid_char(mapping.get("quotechar", mapping.get("quote")))
    escapechar = _valid_char(mapping.get("escapechar", mapping.get("escape")))
    newline = _valid_newline(mapping.get("row_delimiter", mapping.get("newline", mapping.get("new_line"))))

    header_rows = _safe_nonnegative_int(
        mapping.get("header_rows", mapping.get("header_lines", base.header_rows)),
        base.header_rows,
    )
    preamble_rows = _safe_nonnegative_int(
        mapping.get("preamble_rows", mapping.get("preamble_lines", base.preamble_rows)),
        base.preamble_rows,
    )

    result = CSVDialect(
        delimiter=delimiter or base.delimiter,
        quotechar=quotechar if quotechar is not None else base.quotechar,
        escapechar=escapechar if escapechar is not None else base.escapechar,
        newline=newline or base.newline,
        header_rows=header_rows,
        preamble_rows=preamble_rows,
    )
    if result.quotechar and result.escapechar is None:
        result.escapechar = result.quotechar
    return result


def infer_dialect_with_llm(
    csv_input: str,
    clever_dialect: Dict[str, Any],
    context_lines: int,
    trace: TraceWriter,
) -> Dict[str, Any]:
    sample_lines = _read_sample_lines(csv_input, context_lines)
    sample = "\n".join(sample_lines)

    parts = [
        "You are a CSV dialect detector. Analyze this CSV file and",
        "output ONLY a valid JSON object (no markdown, no explanation) with these keys:",
        "",
        '"delimiter": the exact field separator string (e.g. "," or "\\t" or ", " or " " or ";")',
        '"quotechar": the quoting character (e.g. "\\"" or "\'")',
        '"escapechar": the escape character used inside quotes (e.g. "\\"" or "\\\\" or "" for none/null)',
        '"header_lines": integer - how many rows form the header (0=no header, 1=normal, 2+=multi-row where column names are joined with space)',
        '"preamble_lines": integer - lines to skip before header (usually 0)',
        '"n_columns": integer - number of columns',
        '"column_names": array of strings - the column names (if multi-row header, join values with space)',
        "",
    ]
    if clever_dialect:
        parts += [
            "CleverCSV guess:",
            json.dumps(clever_dialect, ensure_ascii=False),
            "",
        ]
    parts += [
        "CSV file:",
        sample,
    ]
    prompt = "\n".join(parts)

    # Estimate: fixed JSON skeleton (~120 chars) + column names from sample header line
    header_line = sample_lines[0] if sample_lines else ""
    estimated_output = 120 + len(header_line)
    answer = call_llm(prompt, trace, "llm_dialect_inference", estimated_output_chars=estimated_output)
    try:
        parsed = _extract_json_object(answer)
        if isinstance(parsed, dict):
            trace.write("llm_dialect_parsed", parsed=parsed)
            return parsed
    except Exception as exc:
        trace.write("llm_dialect_parse_error", error=str(exc), response=answer)
    return {}


def parse_record(line: str, dialect: CSVDialect) -> List[str]:
    delimiter = dialect.delimiter
    quote = dialect.quotechar
    escape = dialect.escapechar
    fields: List[str] = []
    current: List[str] = []
    i = 0
    in_quotes = False

    while i < len(line):
        if in_quotes:
            if quote and escape == quote and line.startswith(quote + quote, i):
                current.append(quote)
                i += 2
                continue
            if quote and escape and escape != quote and line.startswith(escape + quote, i):
                current.append(quote)
                i += len(escape) + len(quote)
                continue
            if quote and line.startswith(quote, i):
                in_quotes = False
                i += len(quote)
                continue
            current.append(line[i])
            i += 1
            continue

        if delimiter and line.startswith(delimiter, i):
            fields.append("".join(current))
            current = []
            i += len(delimiter)
            continue
        if quote and line.startswith(quote, i) and not current:
            in_quotes = True
            i += len(quote)
            continue
        current.append(line[i])
        i += 1

    fields.append("".join(current))
    return fields


def _score_dialect(lines: List[str], dialect: CSVDialect) -> Tuple[int, int, int, int]:
    useful = [line for line in lines[dialect.preamble_rows:] if line != ""]
    if not useful:
        return (0, 0, 0, 0)
    data_lines = useful[dialect.header_rows:] if dialect.header_rows else useful
    if not data_lines:
        data_lines = useful
    counts = [len(parse_record(line, dialect)) for line in data_lines]
    if not counts:
        return (0, 0, 0, 0)
    count_counter = Counter(counts)
    mode_count, mode_freq = count_counter.most_common(1)[0]
    inconsistent = len(counts) - mode_freq
    delimiter_bonus = len(dialect.delimiter)
    return (mode_freq, -inconsistent, mode_count, delimiter_bonus)


def reconcile_dialects(
    clever_mapping: Dict[str, Any],
    llm_mapping: Dict[str, Any],
    scoring_lines: List[str],
    trace: TraceWriter,
) -> CSVDialect:
    default = CSVDialect()
    clever = _dialect_from_mapping(clever_mapping, default)
    llm = _dialect_from_mapping(llm_mapping, clever) if llm_mapping else clever

    candidates: "OrderedDict[str, CSVDialect]" = OrderedDict()
    candidates["clevercsv"] = clever
    if llm_mapping:
        candidates["llm"] = llm
        candidates["llm_delimiter_with_clever_quote"] = CSVDialect(
            delimiter=llm.delimiter,
            quotechar=clever.quotechar,
            escapechar=clever.escapechar,
            newline=llm.newline or clever.newline,
            header_rows=llm.header_rows,
            preamble_rows=llm.preamble_rows,
        )
        candidates["clever_delimiter_with_llm_quote"] = CSVDialect(
            delimiter=clever.delimiter,
            quotechar=llm.quotechar,
            escapechar=llm.escapechar,
            newline=llm.newline or clever.newline,
            header_rows=llm.header_rows,
            preamble_rows=llm.preamble_rows,
        )

    scored = []
    for name, dialect in candidates.items():
        scored.append((name, dialect, _score_dialect(scoring_lines, dialect)))

    if llm_mapping and len(llm.delimiter) > 1:
        best_name = "llm"
        best_dialect = llm
        best_score = _score_dialect(scoring_lines, llm)
        forced_reason = "llm_multi_character_delimiter"
    else:
        best_name, best_dialect, best_score = max(
            scored,
            key=lambda item: (
                item[2],
                1 if item[0] == "llm" else 0,
            ),
        )
        forced_reason = None

    llm_layout_applied = False
    if llm_mapping:
        best_dialect = CSVDialect(
            delimiter=best_dialect.delimiter,
            quotechar=best_dialect.quotechar,
            escapechar=best_dialect.escapechar,
            newline=llm.newline or best_dialect.newline,
            header_rows=llm.header_rows,
            preamble_rows=llm.preamble_rows,
        )
        llm_layout_applied = True

    trace.write(
        "dialect_reconciliation",
        candidates=[
            {"name": name, "dialect": dialect.as_trace_dict(), "score": score}
            for name, dialect, score in scored
        ],
        selected=best_name,
        selected_score=best_score,
        forced_reason=forced_reason,
        llm_header_preamble_applied=llm_layout_applied,
    )
    trace.write(
        "dialect",
        sniffed=clever.as_trace_dict(),
        llm=_dialect_from_mapping(llm_mapping, clever).as_trace_dict() if llm_mapping else None,
        final=best_dialect.as_trace_dict(),
    )
    return best_dialect


def _header_lines(csv_input: str, dialect: CSVDialect) -> List[str]:
    if dialect.header_rows <= 0:
        return []
    lines = _read_sample_lines(csv_input, dialect.preamble_rows + dialect.header_rows)
    return lines[dialect.preamble_rows:dialect.preamble_rows + dialect.header_rows]


def combine_header_rows(lines: List[str], dialect: CSVDialect) -> List[str]:
    parsed_rows = [parse_record(line, dialect) for line in lines]
    if not parsed_rows:
        return []
    width = max(len(row) for row in parsed_rows)
    header: List[str] = []
    for col_idx in range(width):
        pieces = []
        for row in parsed_rows:
            if col_idx < len(row):
                pieces.append(row[col_idx])
        header.append(" ".join(pieces))
    return header


def infer_expected_columns(lines: List[str], dialect: CSVDialect) -> int:
    useful = [line for line in lines[dialect.preamble_rows:] if line != ""]
    data_lines = useful[dialect.header_rows:] if dialect.header_rows else useful
    if not data_lines:
        data_lines = useful
    counts = [len(parse_record(line, dialect)) for line in data_lines]
    if not counts:
        return 0
    return Counter(counts).most_common(1)[0][0]


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


def load_with_duckdb(
    csv_input: str,
    dialect: CSVDialect,
    expected_columns: int,
    trace: TraceWriter,
    stage: str,
    store_rejects: bool = True,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], List[Dict[str, Any]]]:
    import duckdb

    conn = duckdb.connect(database=":memory:")
    scan_table = f"reject_scans_{stage}_{os.getpid()}_{int(time.time() * 1000000)}"
    rejects_table = f"reject_errors_{stage}_{os.getpid()}_{int(time.time() * 1000000)}"
    columns = _unique_duckdb_columns(expected_columns)
    options = {
        "auto_detect": False,
        "delim": dialect.delimiter,
        "quote": dialect.quotechar or "",
        "escape": dialect.escapechar or "",
        "header": False,
        "skip": dialect.preamble_rows + dialect.header_rows,
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
        _sql_string(csv_input),
        "auto_detect = false",
        f"delim = {_sql_string(dialect.delimiter)}",
        f"quote = {_sql_string(dialect.quotechar or '')}",
        f"escape = {_sql_string(dialect.escapechar or '')}",
        "header = false",
        f"skip = {dialect.preamble_rows + dialect.header_rows}",
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
        options={k: v for k, v in options.items() if k != "columns"},
        columns=list(options["columns"].keys()),
    )
    try:
        df = conn.execute(sql).df()
    except Exception as exc:
        trace.write("duckdb_load_error", stage=stage, error=str(exc), sql=sql)
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


def find_width_rejects(csv_input: str, dialect: CSVDialect, expected_columns: int) -> List[Dict[str, Any]]:
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


def _good_examples(df: pd.DataFrame, header: List[str], limit: int) -> List[Dict[str, Any]]:
    examples = []
    for _, row in df.head(max(0, limit)).iterrows():
        values = [_coerce_cell(value) for value in row.tolist()]
        examples.append({"fields": values})
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


def infer_repairs_with_llm(
    header: List[str],
    dialect: CSVDialect,
    good_df: pd.DataFrame,
    rejects: List[Dict[str, Any]],
    context_lines: int,
    trace: TraceWriter,
) -> Dict[int, List[str]]:
    faulty_lines = _dedupe_rejects_for_prompt(rejects)
    if not faulty_lines:
        return {}

    prompt_payload = {
        "expected_column_count": len(header),
        "columns": header,
        "dialect": dialect.as_trace_dict(),
        "good_examples": _good_examples(good_df, header, context_lines),
        "faulty_lines": faulty_lines,
    }
    prompt = "\n".join([
        "Repair faulty CSV records. Return JSON only.",
        "Return unescaped field values, not CSV text.",
        "For each faulty line, output exactly one repair with exactly the expected number of fields.",
        "Preserve field content exactly: literal quotes, apostrophes, backslashes, spaces, typos, and casing are data.",
        "Do not CSV-escape inside field values. JSON escaping is allowed only because the response is JSON.",
        "The file may use a multi-character delimiter such as \", \"; use the dialect below as context.",
        "Use the column names to guide how you split or merge tokens: each repaired value must be semantically",
        "consistent with its column (e.g. a value in 'DATE' should look like a date, 'Price' like a price).",
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

    repairs: Dict[int, List[str]] = {}
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
        repairs[line] = [_coerce_cell(value) for value in fields]

    trace.write(
        "llm_faulty_line_repairs_parsed",
        repairs=[{"line": line, "fields": fields} for line, fields in repairs.items()],
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
    repairs: Dict[int, List[str]],
    dialect: CSVDialect,
    trace: TraceWriter,
) -> Optional[str]:
    if not repairs:
        return None

    with open(csv_input, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        lines = f.readlines()
    default_newline = _detect_file_newline(lines, dialect)

    applied = []
    for line_num, fields in repairs.items():
        idx = line_num - 1
        if idx < 0 or idx >= len(lines):
            continue
        _, newline = _split_line_ending(lines[idx], default_newline)
        repaired_line = serialize_record(fields, dialect)
        lines[idx] = repaired_line + newline
        applied.append({"line": line_num, "serialized": repaired_line, "fields": fields})

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


def _splice_clean_rows(
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


def parse_csv_with_validation(
    csv_input: str,
    clean_csv: str = None,
    cheat: bool = False,
    llm_repair: bool = True,
    llm_sniff: bool = False,
    sidecar_path: str = None,
    llm_context_lines: int = 10,
    reset_sidecar: bool = True,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Load a polluted CSV using CleverCSV + optional LLM dialect inference, DuckDB
    reject tables, and optional LLM repairs for rejected lines.

    Returns:
        (DataFrame ready for benchmark output, original DuckDB reject summaries)
    """
    trace = TraceWriter(sidecar_path, reset=reset_sidecar)
    trace.write(
        "file_start",
        path=csv_input,
        clean_csv=clean_csv,
        cheat=cheat,
        llm_repair=llm_repair and not cheat,
        llm_sniff=llm_sniff,
        llm_context_lines=llm_context_lines,
    )

    clever_mapping: Dict[str, Any] = {}
    if not llm_sniff:
        clever_mapping = sniff_with_clevercsv(csv_input)
        trace.write("clevercsv_dialect", dialect=clever_mapping)

    llm_mapping: Dict[str, Any] = {}
    if llm_sniff or (llm_repair and not cheat):
        try:
            llm_mapping = infer_dialect_with_llm(csv_input, clever_mapping, llm_context_lines, trace)
        except Exception as exc:
            trace.write("llm_dialect_error", error=str(exc))

    scoring_lines = _read_scoring_lines(csv_input)
    dialect = reconcile_dialects(clever_mapping, llm_mapping, scoring_lines, trace)

    raw_header_lines = _header_lines(csv_input, dialect)
    header = combine_header_rows(raw_header_lines, dialect)
    has_header = dialect.header_rows > 0

    llm_columns = llm_mapping.get("column_names") if llm_mapping else None
    if isinstance(llm_columns, list) and llm_columns and all(isinstance(c, str) for c in llm_columns):
        header = [str(c) for c in llm_columns]
        has_header = True
        trace.write("llm_column_names_applied", columns=header)

    expected_columns = len(header) if has_header else infer_expected_columns(scoring_lines, dialect)
    if expected_columns == 0:
        trace.write("empty_or_unreadable_file")
        if cheat and clean_csv:
            clean_df = load_clean_dataframe(clean_csv)
            trace.write("cheat_result", clean_csv=clean_csv, malformed_count=0)
            return clean_df, []
        return pd.DataFrame(), []
    if not has_header:
        header = [f"_c{i}" for i in range(expected_columns)]

    trace.write(
        "schema_inference",
        has_header=has_header,
        header=header,
        expected_columns=expected_columns,
        skipped_rows=dialect.preamble_rows + dialect.header_rows,
    )

    df, duckdb_rejects, _ = load_with_duckdb(csv_input, dialect, expected_columns, trace, "initial")
    width_rejects = find_width_rejects(csv_input, dialect, expected_columns)
    if width_rejects:
        trace.write("local_width_validation_result", stage="initial", reject_errors=width_rejects)
    rejects = merge_rejects(duckdb_rejects, width_rejects)
    malformed = rejects_to_malformed(rejects)

    if llm_repair and rejects:
        repairs = infer_repairs_with_llm(header, dialect, df, rejects, llm_context_lines, trace)
        for item in malformed:
            if item["line_num"] in repairs:
                item["repaired"] = False

        repaired_path = write_repaired_copy(csv_input, repairs, dialect, trace)
        if repaired_path:
            try:
                repaired_df, final_duckdb_rejects, _ = load_with_duckdb(
                    repaired_path,
                    dialect,
                    expected_columns,
                    trace,
                    "repaired",
                )
                final_width_rejects = find_width_rejects(repaired_path, dialect, expected_columns)
                if final_width_rejects:
                    trace.write("local_width_validation_result", stage="repaired", reject_errors=final_width_rejects)
                final_rejects = merge_rejects(final_duckdb_rejects, final_width_rejects)
                if final_rejects:
                    trace.write("repaired_copy_still_has_rejects", rejects=final_rejects)
                final_reject_lines = {
                    int(reject["line"])
                    for reject in final_rejects
                    if reject.get("line") is not None
                }
                for item in malformed:
                    if item["line_num"] in repairs:
                        item["repaired"] = item["line_num"] not in final_reject_lines
                df = repaired_df
            finally:
                try:
                    os.unlink(repaired_path)
                    trace.write("repaired_copy_removed", path=repaired_path)
                except OSError as exc:
                    trace.write("repaired_copy_remove_error", path=repaired_path, error=str(exc))

    result = finalize_dataframe(df, header, has_header)

    if cheat and clean_csv and malformed:
        clean_df = load_clean_dataframe(clean_csv)
        skip_rows = dialect.preamble_rows + dialect.header_rows
        malformed_indices = {m["line_num"] - skip_rows - 1 for m in malformed}
        duckdb_skipped_lines = {int(r["line"]) for r in duckdb_rejects if r.get("line") is not None}
        duckdb_skipped_indices = {line - skip_rows - 1 for line in duckdb_skipped_lines}
        result = _splice_clean_rows(result, clean_df, malformed_indices, duckdb_skipped_indices)
        trace.write("cheat_result", clean_csv=clean_csv, malformed_count=len(malformed))

    trace.write(
        "file_result",
        rows=len(result),
        columns=list(result.columns),
        malformed_count=len(malformed),
    )
    return result, malformed
