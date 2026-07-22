import json
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from llm import _extract_json_object, call_llm


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


def _read_sample_lines(path: str, limit: int) -> List[str]:
    lines: List[str] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for _ in range(max(0, limit)):
            line = f.readline()
            if line == "":
                break
            lines.append(line.rstrip("\r\n"))
    return lines

def _header_lines(csv_input: str, dialect: CSVDialect) -> List[str]:
    if dialect.header_rows <= 0:
        return []
    lines = _read_sample_lines(csv_input, dialect.preamble_rows + dialect.header_rows)
    return lines[dialect.preamble_rows:dialect.preamble_rows + dialect.header_rows]


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


def sniff_with_duckdb(csv_input: str) -> Dict[str, Any]:
    """Sniff a dialect with DuckDB's sniff_csv(), returning the same mapping
    shape as sniff_with_clevercsv (delimiter/quotechar/escapechar)."""
    import duckdb

    def _clean(value: Any) -> Optional[str]:
        if value is None:
            return None
        value = str(value)
        # DuckDB reports the literal "(empty)" when no quote/escape was detected.
        if value == "" or value == "(empty)":
            return None
        return value

    conn = duckdb.connect(database=":memory:")
    try:
        row = conn.execute(
            "SELECT Delimiter, Quote, Escape FROM sniff_csv(?, ignore_errors=true)", [csv_input]
        ).fetchone()
    except Exception:
        return {}
    finally:
        conn.close()
    if row is None:
        return {}
    delimiter, quotechar, escapechar = (_clean(v) for v in row)
    return {
        "delimiter": delimiter,
        "quotechar": quotechar,
        "escapechar": escapechar or quotechar,
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
    sniff_dialect: Dict[str, Any],
    context_lines: int,
    trace: Any,
    sniffer_label: str = "CleverCSV",
) -> Dict[str, Any]:
    sample_lines = _read_sample_lines(csv_input, context_lines)
    sample = "\n".join(sample_lines)

    parts = [
        "You are a CSV dialect detector. Analyze this CSV file and return the intended dialect of the file based on the header and example rows.",
        "Making sure the example rows fit the header semantically and in column count after a split on the delimiter is your top priority",
        "Output ONLY a valid JSON object (no markdown, no explanation) with these keys:",
        "",
        '"delimiter": the exact literal separator string that appears between adjacent fields in the file. Can be multi-char (e.g. "," or "\\t" or ", " (comma+space) or " " or ";")',
        '"quotechar": the quoting character (e.g. "\\"" or "\'")',
        '"escapechar": the escape character used inside quotes (e.g. "\\"" or "\\\\" or "" for none/null)',
        '"header_lines": integer - how many rows form the header (0=no header, 1=normal, 2+=multi-row - will be skipped upon read and replaced with column_names)',
        '"preamble_lines": integer - lines to skip before header (usually 0). Also count blank lines',
        '"column_names": array of strings - the column names, ideally consistent with a string split based on the delimiter or if that is not possible because of structure, consistent with semantics of column data. If there are multiple header-hierarchies, take the lowest and most finegrained one',
        '"n_columns": integer - number of columns, consistent with length of column_names',
        "",
    ]
    # if sniff_dialect:
    #     parts += [
    #         f"{sniffer_label} guess:",
    #         json.dumps(sniff_dialect, ensure_ascii=False),
    #         "",
    #     ]
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


def parse_record(line: str, dialect: CSVDialect, quotes_anywhere: bool = False) -> List[str]:
    # quotes_anywhere lets a quote open quoting wherever it appears instead of only
    # at the start of a field. Used by the width check: DuckDB treats a quote inside
    # an unquoted value as literal text, which lets a deleted delimiter hide -- the
    # value after it is no longer quote-wrapped, so a delimiter sitting inside it
    # gets exposed, one separator is lost, one exposed, and the width still matches.
    # It stays off for dialect scoring, where it would sink space-delimited files.
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
        if quote and line.startswith(quote, i) and (quotes_anywhere or not current):
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


def dialect_from_mappings(
    sniff_mapping: Dict[str, Any],
    llm_mapping: Dict[str, Any],
    scoring_lines: List[str],
    trace: Any,
    sniffer_name: str = "clevercsv",
) -> CSVDialect:
    """Build the final CSV dialect from the available dialect sources.

    `sniff_mapping` is a non-LLM sniffer's guess (CleverCSV or DuckDB), labelled
    by `sniffer_name`. Normalizes each raw mapping into a validated CSVDialect,
    then only runs the scoring-based reconciliation when *both* a sniff and an
    LLM guess exist. With a single source there is nothing to choose between, so
    the lone dialect (which already carries its own layout) is returned directly.
    """
    default = CSVDialect()
    sniff = _dialect_from_mapping(sniff_mapping, default)
    llm = _dialect_from_mapping(llm_mapping, sniff) if llm_mapping else sniff

    if sniff_mapping and llm_mapping:
        final = reconcile_dialects(sniff, llm, scoring_lines, trace, sniffer_name)
    else:
        final = llm if llm_mapping else sniff

    trace.write(
        "dialect",
        sniffed=sniff.as_trace_dict() if sniff_mapping else None,
        sniffer=sniffer_name if sniff_mapping else None,
        llm=llm.as_trace_dict() if llm_mapping else None,
        final=final.as_trace_dict(),
    )
    return final


def reconcile_dialects(
    sniff: CSVDialect,
    llm: CSVDialect,
    scoring_lines: List[str],
    trace: Any,
    sniffer_name: str = "clevercsv",
) -> CSVDialect:
    """Pick the best delimiter/quote between a non-LLM sniff and an LLM guess.

    Only called when both sources are present. Scores the two dialects plus two
    cross-combinations against the sample lines; the LLM always owns the
    header/preamble/newline layout of whichever delimiter+quote wins.
    """
    candidates: "OrderedDict[str, CSVDialect]" = OrderedDict()
    candidates[sniffer_name] = sniff
    candidates["llm"] = llm
    candidates[f"llm_delimiter_with_{sniffer_name}_quote"] = CSVDialect(
        delimiter=llm.delimiter,
        quotechar=sniff.quotechar,
        escapechar=sniff.escapechar,
        newline=llm.newline or sniff.newline,
        header_rows=llm.header_rows,
        preamble_rows=llm.preamble_rows,
    )
    candidates[f"{sniffer_name}_delimiter_with_llm_quote"] = CSVDialect(
        delimiter=sniff.delimiter,
        quotechar=llm.quotechar,
        escapechar=llm.escapechar,
        newline=llm.newline or sniff.newline,
        header_rows=llm.header_rows,
        preamble_rows=llm.preamble_rows,
    )

    scored = []
    for name, dialect in candidates.items():
        scored.append((name, dialect, _score_dialect(scoring_lines, dialect)))

    if len(llm.delimiter) > 1:
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

    # LLM owns the header/preamble/newline layout regardless of which
    # delimiter+quote candidate won the scoring.
    best_dialect = CSVDialect(
        delimiter=best_dialect.delimiter,
        quotechar=best_dialect.quotechar,
        escapechar=best_dialect.escapechar,
        newline=llm.newline or best_dialect.newline,
        header_rows=llm.header_rows,
        preamble_rows=llm.preamble_rows,
    )

    trace.write(
        "dialect_reconciliation",
        candidates=[
            {"name": name, "dialect": dialect.as_trace_dict(), "score": score}
            for name, dialect, score in scored
        ],
        selected=best_name,
        selected_score=best_score,
        forced_reason=forced_reason,
        llm_header_preamble_applied=True,
    )
    return best_dialect


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
