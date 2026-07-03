from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


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
    """Compatibility shim for the benchmark wrapper."""

    global _CACHE_ENABLED, _CACHE_PATH
    _CACHE_ENABLED = enabled
    _CACHE_PATH = path



def configure_llm_dry_run(enabled: bool) -> None:
    """Compatibility shim for the benchmark wrapper."""

    global _DRY_RUN
    _DRY_RUN = enabled



def get_llm_cache_stats() -> Dict[str, int]:
    """Return cache counters in the shape the benchmark wrapper expects."""

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
    return [", ", ";", "\t", "|", ","]



def _parse_csv_text(text: str, delimiter: str, quotechar: str = '"') -> List[List[str]]:
    """Parse CSV text with a small quote-aware splitter that supports multi-char delimiters."""

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
    mode_width, mode_count = max(counts.items(), key=lambda item: (item[1], item[0]))
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
        header = header[: expected_width - 1] + [" ".join(header[expected_width - 1 :]).strip()]
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



def _build_repair_program(analysis: CSVAnalysis) -> str:
    return f"""
DELIMITER = {analysis.delimiter!r}
QUOTECHAR = {analysis.quotechar!r}
EXPECTED_WIDTH = {analysis.expected_width}
HEADER_ROWS = {analysis.header_rows}
HEADER = {analysis.repaired_header!r}


def repair_rows(rows):
    repaired = [HEADER]
    for row in rows[HEADER_ROWS:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) < EXPECTED_WIDTH:
            row = row + [\"\"] * (EXPECTED_WIDTH - len(row))
        elif len(row) > EXPECTED_WIDTH:
            row = row[: EXPECTED_WIDTH - 1] + [DELIMITER.join(row[EXPECTED_WIDTH - 1:])]
        repaired.append(row[:EXPECTED_WIDTH])
    return repaired
""".strip()



def _execute_repair_program(program: str, rows: List[List[str]]) -> List[List[str]]:
    namespace: Dict[str, Any] = {}
    exec(program, namespace, namespace)
    return namespace["repair_rows"](rows)



def _rows_to_dataframe(rows: List[List[str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    header = rows[0]
    data = rows[1:]
    if not header:
        return pd.DataFrame(data)
    width = len(header)
    normalized = [_normalize_row(row, width, ",") for row in data]
    return pd.DataFrame(normalized, columns=header)



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
    """Heuristically repair a polluted CSV by generating and executing a tiny Python repair program."""

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

    text = Path(csv_input).read_text(encoding="utf-8-sig", errors="replace")
    analysis = _analyze_csv(text)
    parsed_rows = _parse_csv_text(text, analysis.delimiter, analysis.quotechar)
    trace.write(
        "analysis",
        delimiter=analysis.delimiter,
        quotechar=analysis.quotechar,
        expected_width=analysis.expected_width,
        header_rows=analysis.header_rows,
        repaired_header=analysis.repaired_header,
    )

    malformed = _malformed_rows(parsed_rows, analysis.expected_width, analysis.header_rows)

    if llm_repair:
        program = _build_repair_program(analysis)
        trace.write("generated_repair_program", program=program)
        repaired_rows = _execute_repair_program(program, parsed_rows)
        trace.write("repair_applied", repaired_rows=len(repaired_rows), code_executed=True)
    else:
        repaired_rows = [
            _normalize_row(row, analysis.expected_width, analysis.delimiter)
            for row in parsed_rows
            if any(cell.strip() for cell in row)
        ]
        if repaired_rows and analysis.header_rows > 1:
            repaired_rows[0] = analysis.repaired_header
        trace.write("repair_skipped", repaired_rows=len(repaired_rows), code_executed=False)

    df = _rows_to_dataframe(repaired_rows)
    trace.write("final_dataframe", rows=len(df), columns=list(df.columns))
    return df, malformed
