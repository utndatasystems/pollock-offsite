import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_API_KEY_FILE = Path(__file__).resolve().parents[2] / "local.key"
LLM_API_KEY_FILE_ENV_VAR = "CUSTOM_CSV_LLM_KEY_FILE"
MAX_LLM_SAMPLE_CHARS = 12000


@dataclass(frozen=True)
class CsvDialectConfig:
    delimiter: str = ","
    quotechar: str | None = '"'
    escapechar: str | None = None
    doublequote: bool = True
    skipinitialspace: bool = False
    has_header: bool = True


def infer_csv_dialect(file_content: str) -> CsvDialectConfig:
    llm = _load_chat_model()
    response = llm.invoke(_build_dialect_prompt(file_content))
    raw_config = _extract_json_object(_llm_response_text(response))

    default = CsvDialectConfig()
    return CsvDialectConfig(
        delimiter=_decode_char(raw_config.get("delimiter"), default.delimiter)
        or default.delimiter,
        quotechar=_decode_char(raw_config.get("quotechar"), default.quotechar),
        escapechar=_decode_char(raw_config.get("escapechar"), default.escapechar),
        doublequote=_coerce_bool(raw_config.get("doublequote"), default.doublequote),
        skipinitialspace=_coerce_bool(
            raw_config.get("skipinitialspace"), default.skipinitialspace
        ),
        has_header=_coerce_bool(raw_config.get("has_header"), default.has_header),
    )


def repair_csv_row(
    row_number: int,
    row: list[str],
    neighboring_rows: dict[int, list[str]],
    expected_column_count: int,
) -> list[str]:
    llm = _load_chat_model()
    print("---")
    print(
        _build_row_repair_prompt(
            row_number,
            row,
            neighboring_rows,
            expected_column_count,
        )
    )
    print("---")
    response = llm.invoke(
        _build_row_repair_prompt(
            row_number,
            row,
            neighboring_rows,
            expected_column_count,
        )
    )
    raw_result = _extract_json_object(_llm_response_text(response))
    fixed_csv_row = raw_result.get("fixed_csv_row")
    if not isinstance(fixed_csv_row, str):
        raise ValueError("LLM row repair did not return fixed_csv_row.")
    print(f"LLM repaired row: {fixed_csv_row}")

    repaired_rows = _parse_standard_csv_rows(fixed_csv_row)
    if len(repaired_rows) != 1:
        raise ValueError("LLM row repair must return exactly one CSV row.")

    repaired_row = repaired_rows[0]
    if len(repaired_row) != expected_column_count:
        raise ValueError(
            "LLM row repair returned "
            f"{len(repaired_row)} columns, expected {expected_column_count}."
        )
    return repaired_row


def _load_chat_model():
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "langchain-openai is required for custom CSV parsing. "
            f"Install it and put your key in {DEFAULT_LLM_API_KEY_FILE}."
        ) from exc

    model = os.environ.get("CUSTOM_CSV_LLM_MODEL", DEFAULT_LLM_MODEL)
    return ChatOpenAI(model=model, temperature=0, api_key=_load_api_key())


def _load_api_key() -> str:
    key_file = Path(
        os.environ.get(LLM_API_KEY_FILE_ENV_VAR, DEFAULT_LLM_API_KEY_FILE)
    ).expanduser()

    try:
        api_key = key_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Create {key_file} and put your OpenAI API key in it, or set "
            f"{LLM_API_KEY_FILE_ENV_VAR} to another key file path."
        ) from exc

    if not api_key or api_key.startswith("replace-me"):
        raise RuntimeError(f"Put your real OpenAI API key in {key_file}.")
    return api_key


def _build_dialect_prompt(file_content: str) -> str:
    sample = file_content[:MAX_LLM_SAMPLE_CHARS]
    return f"""
You are configuring Python's csv.reader for an unknown delimited text file.
Inspect the file content and return only one JSON object with these keys:
delimiter, quotechar, escapechar, doublequote, skipinitialspace, has_header.

Rules:
- delimiter, quotechar, and escapechar must be single characters, escaped
  strings like "\\t", or null.
- delimiter is required; use "," if genuinely unsure.
- quotechar may be null if there is no quoting.
- escapechar may be null if there is no escape character.
- doublequote, skipinitialspace, and has_header must be booleans.

File content:
```csv
{sample}
```
""".strip()


def _build_row_repair_prompt(
    row_number: int,
    row: list[str],
    neighboring_rows: dict[int, list[str]],
    expected_column_count: int,
) -> str:
    return f"""
You are repairing one malformed CSV row.

The parsed row below has the wrong number of columns. Infer what local row-level
dialect mistake happened, using the neighboring rows as examples of the intended
shape, then convert the malformed row into one standard CSV record.

Malformed row number: {row_number}
Expected column count: {expected_column_count}
Current malformed row column count: {len(row)}

Standard CSV record means:
- comma delimiter
- double quote quotechar
- double quotes escaped by doubling them
- exactly {expected_column_count} columns
- no surrounding markdown or explanation

Return only one JSON object with these keys:
- row_dialect: short description of the row-level delimiter/quote issue
- fixed_csv_row: the repaired row as one standard CSV record string

Important:
- fixed_csv_row must parse into exactly {expected_column_count} columns.
- Do not drop data to reach {expected_column_count} columns.
- Do not add empty placeholder columns unless the row is genuinely missing data.

Neighboring rows, keyed by row number:
{json.dumps(neighboring_rows, ensure_ascii=True)}

Malformed parsed row:
{json.dumps(row, ensure_ascii=True)}
""".strip()


def _parse_standard_csv_rows(csv_content: str) -> list[list[str]]:
    import csv
    from io import StringIO

    return list(csv.reader(StringIO(csv_content), delimiter=",", quotechar='"'))


def _decode_char(value: Any, default: str | None) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str):
        return default

    normalized = value.strip()
    if normalized.lower() in {"", "none", "null"}:
        return None

    aliases = {
        "\\t": "\t",
        "tab": "\t",
        "\\n": "\n",
        "newline": "\n",
        "\\r": "\r",
        "carriage return": "\r",
        "\\r\\n": "\r\n",
        "crlf": "\r\n",
        "space": " ",
    }
    normalized = aliases.get(normalized.lower(), normalized)
    return normalized if len(normalized) == 1 else default


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return default


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _llm_response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)
