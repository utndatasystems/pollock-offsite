from __future__ import annotations

import builtins
import csv as csv_module
import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

import pandas as pd


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_ENDPOINT_ENV = "OPENAI_ENDPOINT"
OPENAI_DEFAULT_MODEL = "gpt-5.4"
OPENAI_DEFAULT_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"


_CACHE_ENABLED = True
_CACHE_PATH: Optional[str] = None
_DRY_RUN = False
_CACHE_STATS: Dict[str, int] = {
    "total": 0,
    "cached": 0,
    "input_chars_total": 0,
    "input_chars_cached": 0,
    "output_chars_cached": 0,
    "output_chars_fresh": 0,
}


@dataclass(frozen=True)
class CSVAnalysis:
    delimiter: str
    quotechar: str
    expected_width: int
    header_rows: int
    repaired_header: List[str]


class TraceWriter:
    def __init__(self, path: Optional[str], reset: bool = True):
        self.path = path
        self._fh = None
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            mode = "w" if reset else "a"
            self._fh = open(path, mode, encoding="utf-8")

    def write(self, event_type: str, **payload: Any) -> None:
        if self._fh is None:
            return
        record = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        record.update(payload)
        self._fh.write(json.dumps(record, ensure_ascii=True) + "\n")
        self._fh.flush()


def configure_llm_cache(path: Optional[str] = None, enabled: bool = True) -> None:
    global _CACHE_ENABLED, _CACHE_PATH
    _CACHE_ENABLED = enabled
    _CACHE_PATH = path


def configure_llm_dry_run(enabled: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = enabled


def get_llm_cache_stats() -> Dict[str, int]:
    return dict(_CACHE_STATS)


def _coerce_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _is_numeric_like(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        return True
    if re.fullmatch(r"\$[+-]?\d+(?:\.\d+)?", value):
        return True
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", value):
        return True
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", value):
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return True
    return False


def _looks_like_header_row(row: Sequence[str]) -> bool:
    cells = [c.strip() for c in row if c is not None and c.strip()]
    if not cells:
        return False
    alpha = sum(ch.isalpha() for ch in " ".join(cells))
    digit = sum(ch.isdigit() for ch in " ".join(cells))
    if alpha == 0:
        return False
    if any(_is_numeric_like(cell) for cell in cells):
        return False
    return alpha >= digit


def _candidate_delimiters() -> List[str]:
    return [", ", ";", "	", "|", ","]


def _parse_csv_text(text: str, delimiter: str, quotechar: str = '"') -> List[List[str]]:
    rows: List[List[str]] = []
    field: List[str] = []
    row: List[str] = []
    i = 0
    n = len(text)
    delim_len = len(delimiter)
    in_quotes = False

    while i < n:
        if in_quotes:
            ch = text[i]
            if ch == quotechar:
                if i + 1 < n and text[i + 1] == quotechar:
                    field.append(quotechar)
                    i += 2
                    continue
                in_quotes = False
                i += 1
                continue
            field.append(ch)
            i += 1
            continue

        if delim_len and text.startswith(delimiter, i):
            row.append("".join(field))
            field = []
            i += delim_len
            continue

        ch = text[i]
        if ch == quotechar and not field:
            in_quotes = True
            i += 1
            continue
        if ch == "\r":
            row.append("".join(field))
            rows.append(row)
            row = []
            field = []
            if i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            continue
        if ch == "\n":
            row.append("".join(field))
            rows.append(row)
            row = []
            field = []
            i += 1
            continue

        field.append(ch)
        i += 1

    if field or row:
        row.append("".join(field))
        rows.append(row)

    return rows


def _score_delimiter(text: str, delimiter: str) -> Tuple[int, int, int]:
    sample = text[:50000]
    rows = _parse_csv_text(sample, delimiter)
    widths = [len(row) for row in rows if any(cell.strip() for cell in row)]
    if not widths:
        return (-1, 0, 0)
    counts = Counter(widths)
    mode_width, _ = max(counts.items(), key=lambda item: (item[1], item[0]))
    consistency = sum(1 for width in widths if width == mode_width)
    return (mode_width, consistency, -len(delimiter))


def _guess_dialect(text: str) -> Tuple[str, str]:
    best = None
    for delimiter in _candidate_delimiters():
        score = _score_delimiter(text, delimiter)
        if best is None or score > best[0]:
            best = (score, delimiter)
    return (best[1] if best else ",", '"')


def _detect_expected_width(rows: Sequence[Sequence[str]]) -> int:
    widths = [len(row) for row in rows if any(cell.strip() for cell in row)]
    if not widths:
        return 0
    counts = Counter(widths)
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _detect_header_rows(rows: Sequence[Sequence[str]], expected_width: int) -> int:
    if not rows:
        return 0

    short_prefix = []
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) < expected_width and _looks_like_header_row(row):
            short_prefix.append(row)
            continue
        break

    if len(short_prefix) >= 2:
        return len(short_prefix)
    if rows and len(rows[0]) == expected_width:
        return 1
    return 1 if rows else 0


def _flatten_header_rows(rows: Sequence[Sequence[str]], header_rows: int, expected_width: int) -> List[str]:
    if not rows:
        return []

    if header_rows <= 1:
        header = [_coerce_cell(cell) for cell in rows[0]]
    else:
        header = []
        for row in rows[:header_rows]:
            header.extend(_coerce_cell(cell) for cell in row)

    header = [cell.strip() for cell in header]
    if expected_width and len(header) < expected_width:
        header.extend([""] * (expected_width - len(header)))
    elif expected_width and len(header) > expected_width:
        header = header[: expected_width - 1] + [" ".join(header[expected_width - 1:]).strip()]
    return header


def _normalize_row(row: Sequence[str], expected_width: int, delimiter: str) -> List[str]:
    cells = [_coerce_cell(cell) for cell in row]
    if expected_width <= 0:
        return cells
    if len(cells) < expected_width:
        cells = cells + [""] * (expected_width - len(cells))
    elif len(cells) > expected_width:
        cells = cells[: expected_width - 1] + [delimiter.join(cells[expected_width - 1:])]
    return cells[:expected_width]


def _analyze_csv(text: str) -> CSVAnalysis:
    delimiter, quotechar = _guess_dialect(text)
    parsed_rows = _parse_csv_text(text, delimiter, quotechar)
    widths = [len(row) for row in parsed_rows if any(cell.strip() for cell in row)]
    provisional_width = max(widths) if widths else 0
    header_rows = _detect_header_rows(parsed_rows, provisional_width)
    data_widths = [
        len(row)
        for row in parsed_rows[header_rows:]
        if any(cell.strip() for cell in row)
    ]
    if data_widths:
        counts = Counter(data_widths)
        expected_width = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
    else:
        expected_width = provisional_width
    repaired_header = _flatten_header_rows(parsed_rows, header_rows, expected_width)
    if not repaired_header and expected_width:
        repaired_header = [f"col_{i}" for i in range(expected_width)]
    return CSVAnalysis(
        delimiter=delimiter,
        quotechar=quotechar,
        expected_width=expected_width or len(repaired_header),
        header_rows=header_rows,
        repaired_header=repaired_header,
    )


def _malformed_rows(rows: Sequence[Sequence[str]], expected_width: int, header_rows: int) -> List[Dict[str, Any]]:
    malformed: List[Dict[str, Any]] = []
    for line_num, row in enumerate(rows, start=1):
        if line_num <= header_rows:
            malformed.append({
                "line_num": line_num,
                "reason": "header row normalized",
                "raw": list(row),
                "repaired": True,
            })
            continue
        if expected_width and len(row) != expected_width:
            malformed.append({
                "line_num": line_num,
                "reason": f"width {len(row)} -> {expected_width}",
                "raw": list(row),
                "repaired": True,
            })
    return malformed


def _build_repair_prompt(raw_csv: str, analysis: CSVAnalysis) -> str:
    return (
        "You are a Python code generator for CSV repair.\n"
        "Return ONLY valid Python code. No markdown, no explanation, no backticks.\n"
        "The code will be executed with exec() and must define exactly this function:\n"
        "    def repair_csv(raw_csv: str) -> str:\n"
        "The function receives the raw CSV text and must return repaired CSV text.\n"
        "Use only Python code to fix the CSV corruption. Do not emit JSON. Do not emit prose.\n"
        "Preserve original data, quoting, commas inside quoted values, and header capitalization.\n"
        "If the header spans multiple rows, combine it into a single header row.\n"
        "If fields were split or merged incorrectly, repair them before returning the CSV.\n"
        "The repaired output must be valid CSV text that pandas can read.\n\n"
        f"Detected delimiter hint: {analysis.delimiter!r}\n"
        f"Detected quote character hint: {analysis.quotechar!r}\n"
        f"Detected header rows: {analysis.header_rows}\n"
        f"Detected expected width: {analysis.expected_width}\n\n"
        "Raw CSV:\n"
        f"{raw_csv}\n"
    )


def _extract_python_code(llm_output: str) -> str:
    text = llm_output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if "def repair_csv" in text:
        start = text.index("def repair_csv")
        return text[start:].strip()

    return text


def _prompt_hash(prompt: str) -> str:
    model = os.environ.get(OPENAI_MODEL_ENV, OPENAI_DEFAULT_MODEL)
    key = model + "\x00" + prompt
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _ensure_cache_loaded() -> Dict[str, str]:
    cache: Dict[str, str] = {}
    if not _CACHE_ENABLED or not _CACHE_PATH:
        return cache
    path = Path(_CACHE_PATH)
    if not path.exists():
        return cache
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            for key, value in loaded.items():
                if isinstance(key, str) and isinstance(value, str):
                    cache[key] = value
    except Exception:
        return cache
    return cache


def _save_cache(cache: Dict[str, str]) -> None:
    if not _CACHE_ENABLED or not _CACHE_PATH:
        return
    path = Path(_CACHE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def _build_chat_payload(prompt: str) -> Dict[str, Any]:
    return {
        "model": os.environ.get(OPENAI_MODEL_ENV, OPENAI_DEFAULT_MODEL),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write Python repair code for corrupted CSV files. "
                    "Return only Python code."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 4096,
    }



def _query_llm(prompt: str) -> str:
    _CACHE_STATS["total"] += 1
    _CACHE_STATS["input_chars_total"] += len(prompt)
    prompt_sha = _prompt_hash(prompt)
    cache = _ensure_cache_loaded()

    if _CACHE_ENABLED and prompt_sha in cache:
        response = cache[prompt_sha]
        _CACHE_STATS["cached"] += 1
        _CACHE_STATS["input_chars_cached"] += len(prompt)
        _CACHE_STATS["output_chars_cached"] += len(response)
        return response

    if _DRY_RUN:
        response = (
            "def repair_csv(raw_csv: str) -> str:\n"
            "    return raw_csv\n"
        )
        _CACHE_STATS["output_chars_fresh"] += len(response)
        if _CACHE_ENABLED:
            cache[prompt_sha] = response
            _save_cache(cache)
        return response

        _CACHE_STATS["output_chars_fresh"] += len(response)
        if _CACHE_ENABLED:
            cache[prompt_sha] = response
            _save_cache(cache)
        return response

    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise EnvironmentError(
            f"Missing {OPENAI_API_KEY_ENV}. Set it to a valid OpenAI API key to use the LLM repair path."
        )

    payload = json.dumps(_build_chat_payload(prompt)).encode("utf-8")
    request = urllib_request.Request(
        os.environ.get(OPENAI_ENDPOINT_ENV, OPENAI_DEFAULT_ENDPOINT),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=300) as response_obj:
            body = json.loads(response_obj.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"LLM request failed: {detail}") from exc

    choices = body.get("choices") if isinstance(body, dict) else None
    if not choices:
        raise RuntimeError("Unexpected LLM response: missing choices")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    response = message.get("content")
    if not isinstance(response, str):
        raise RuntimeError("Unexpected LLM response: missing assistant content")

    _CACHE_STATS["output_chars_fresh"] += len(response)
    if _CACHE_ENABLED:
        cache[prompt_sha] = response
        _save_cache(cache)
    return response


def _execute_generated_code(program: str, raw_csv: str) -> str:
    code = _extract_python_code(program)
    namespace: Dict[str, Any] = {
        "__name__": "__llm_generated__",
        "__builtins__": {
            name: getattr(builtins, name)
            for name in [
                "abs",
                "all",
                "any",
                "bool",
                "dict",
                "enumerate",
                "Exception",
                "float",
                "int",
                "isinstance",
                "len",
                "list",
                "max",
                "min",
                "range",
                "reversed",
                "set",
                "sorted",
                "str",
                "sum",
                "tuple",
                "zip",
                "__import__",
            ]
        },
    }
    exec(compile(code, "<llm-generated>", "exec"), namespace, namespace)

    repair_fn = namespace.get("repair_csv")
    if not callable(repair_fn):
        for candidate in ("repair", "main", "fix_csv"):
            maybe = namespace.get(candidate)
            if callable(maybe):
                repair_fn = maybe
                break
    if not callable(repair_fn):
        raise ValueError("LLM code did not define a callable repair_csv(raw_csv: str) function")

    result = repair_fn(raw_csv)
    if isinstance(result, pd.DataFrame):
        return result.to_csv(index=False)
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="replace")
    if isinstance(result, list):
        return "\n".join(str(item) for item in result)
    if result is None:
        raise ValueError("repair_csv returned None")
    return str(result)


def _read_csv_text(text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(StringIO(text), dtype=str, keep_default_na=False, na_filter=False)
    except pd.errors.ParserError:
        for sep in [",", ";", "	", "|"]:
            try:
                return pd.read_csv(
                    StringIO(text),
                    sep=sep,
                    engine="python",
                    dtype=str,
                    keep_default_na=False,
                    na_filter=False,
                )
            except Exception:
                continue
        return pd.read_csv(StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False, na_filter=False)


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
    """Use an LLM to generate Python code that repairs a raw CSV file, then execute it."""

    trace = TraceWriter(sidecar_path, reset=reset_sidecar)
    trace.write(
        "file_start",
        path=csv_input,
        clean_csv=clean_csv,
        cheat=cheat,
        llm_repair=llm_repair,
        llm_sniff=llm_sniff,
        llm_context_lines=llm_context_lines,
    )

    if cheat and clean_csv:
        df = pd.read_csv(clean_csv, dtype=str, keep_default_na=False, na_filter=False)
        trace.write("cheat_result", clean_csv=clean_csv, rows=len(df), columns=list(df.columns))
        return df, []

    raw_text = Path(csv_input).read_text(encoding="utf-8-sig", errors="replace")
    analysis = _analyze_csv(raw_text)
    raw_rows = _parse_csv_text(raw_text, analysis.delimiter, analysis.quotechar)
    malformed = _malformed_rows(raw_rows, analysis.expected_width, analysis.header_rows)

    trace.write(
        "analysis",
        delimiter=analysis.delimiter,
        quotechar=analysis.quotechar,
        expected_width=analysis.expected_width,
        header_rows=analysis.header_rows,
        repaired_header=analysis.repaired_header,
    )

    if llm_repair:
        prompt = _build_repair_prompt(raw_text, analysis)
        generated_code = _query_llm(prompt)
        trace.write("generated_repair_program", program=generated_code)
        repaired_text = _execute_generated_code(generated_code, raw_text)
        trace.write("repair_applied", code_executed=True, repaired_chars=len(repaired_text))
    else:
        repaired_rows = [
            _normalize_row(row, analysis.expected_width, analysis.delimiter)
            for row in raw_rows
            if any(cell.strip() for cell in row)
        ]
        if repaired_rows and analysis.header_rows > 1:
            repaired_rows[0] = analysis.repaired_header
        repaired_text = "
".join(
            analysis.delimiter.join(row) for row in repaired_rows
        )
        trace.write("repair_skipped", repaired_rows=len(repaired_rows), code_executed=False)

    df = _read_csv_text(repaired_text)
    trace.write("final_dataframe", rows=len(df), columns=list(df.columns))
    return df, malformed
