from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

import pytest

from sut.code_generation_llm import solution


FAKE_LLM_CODE = r"""
def repair_csv(raw_csv: str) -> str:
    lines = raw_csv.splitlines()
    if (
        len(lines) >= 4
        and lines[0].startswith("DATE,TIME,Qty")
        and lines[1].startswith("PRODUCTID,Price,ProductType")
        and lines[2].lstrip(chr(34)).startswith("ProductDescription")
    ):
        header = [
            "DATE",
            "TIME",
            "Qty",
            "PRODUCTID",
            "Price",
            "ProductType",
            "ProductDescription",
            "URL",
            "Comments",
        ]
        return ",".join(header) + "\n" + "\n".join(lines[3:])
    return raw_csv
"""


def test_parse_csv_with_validation_normal_csv(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "simple.csv"
    csv_path.write_text("name,city,amount\nAlice,Berlin,10\nBob,Munich,20\n", encoding="utf-8")
    monkeypatch.setattr(solution, "_query_llm", lambda prompt: FAKE_LLM_CODE)

    df, malformed = solution.parse_csv_with_validation(str(csv_path), llm_repair=True)

    assert list(df.columns) == ["name", "city", "amount"]
    assert df.shape == (2, 3)
    assert malformed


def test_parse_csv_with_validation_multiline_header(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "multiline.csv"
    csv_path.write_text(
        "DATE,TIME,Qty\n"
        "PRODUCTID,Price,ProductType\n"
        '"ProductDescription","URL",Comments\n'
        "2024-01-01,00:00,1,SKU-1,$9.99,Widget,Small widget,https://example.com,ok\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(solution, "_query_llm", lambda prompt: FAKE_LLM_CODE)

    df, malformed = solution.parse_csv_with_validation(str(csv_path), llm_repair=True)

    assert len(df.columns) == 9
    assert list(df.columns)[:3] == ["DATE", "TIME", "Qty"]
    assert list(df.columns)[6:9] == ["ProductDescription", "URL", "Comments"]
    assert df.shape == (1, 9)
    assert len(malformed) >= 3


def test_select_csv_samples_uses_prefix_and_spreads_remainder():
    raw = "header\n" + "\n".join(f"row-{number}" for number in range(10)) + "\n"

    sample = solution.select_csv_samples(
        raw, first_line_count=2, remaining_row_count=3
    )

    assert sample.first_lines == ["header", "row-0"]
    assert sample.sampled_rows == ["row-1", "row-5", "row-9"]
    assert sample.remaining_rows == 9
    assert sample.total_lines == 11


def test_prompt_contains_samples_but_not_complete_file(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "sampled.csv"
    csv_path.write_text(
        "name;value\nfirst;1\nsecond;2\nthird;3\nfourth;4\nfifth;5\n",
        encoding="utf-8",
    )
    prompts = []
    generated_parser = """
import csv
import io

def parse_csv(raw_csv: str):
    reader = csv.reader(io.StringIO(raw_csv), delimiter=";")
    rows = list(reader)
    return {"columns": rows[0], "rows": rows[1:]}
"""

    def fake_query(prompt):
        prompts.append(prompt)
        return generated_parser

    monkeypatch.setattr(solution, "_query_llm", fake_query)
    dataframe, _ = solution.parse_csv_with_validation(
        str(csv_path), llm_context_lines=2, llm_sample_rows=2
    )

    assert dataframe.to_dict("records") == [
        {"name": "first", "value": "1"},
        {"name": "second", "value": "2"},
        {"name": "third", "value": "3"},
        {"name": "fourth", "value": "4"},
        {"name": "fifth", "value": "5"},
    ]
    assert "first;1" in prompts[0]
    assert "second;2" in prompts[0]
    assert "fifth;5" in prompts[0]
    assert "third;3" not in prompts[0]
    assert "fourth;4" not in prompts[0]


def test_sample_rows_keep_quoted_newline_together():
    raw = "name,notes\nAlice,\"line one\nline two\"\nBob,plain\n"

    sample = solution.select_csv_samples(
        raw, first_line_count=1, remaining_row_count=2
    )

    assert sample.sampled_rows == ["Alice,\"line one\nline two\"", "Bob,plain"]


def test_generated_parser_rejects_unsafe_import():
    program = "import os\ndef parse_csv(raw_csv):\n    return raw_csv\n"

    try:
        solution._execute_generated_code(program, "a,b\n1,2\n")
    except ValueError as error:
        assert "disallowed module" in str(error)
    else:
        raise AssertionError("unsafe generated parser was executed")


def test_chat_payload_uses_completion_tokens_for_gpt5(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://example.test/v1/chat/completions")

    payload = solution._build_chat_payload("prompt")

    assert payload["max_completion_tokens"] == 4096
    assert "max_tokens" not in payload
    assert payload["temperature"] == 0
    assert "reasoning_effort" not in payload


def test_chat_payload_uses_ollama_reasoning_control(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "qwen3.5:0.8b")
    monkeypatch.setenv(
        "OPENAI_ENDPOINT", "http://localhost:11434/v1/chat/completions"
    )

    payload = solution._build_chat_payload("prompt")

    assert payload["max_tokens"] == 4096
    assert payload["reasoning_effort"] == "none"


def test_api_usage_and_local_cache_costs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://example.test/v1/chat/completions")
    monkeypatch.setattr(solution, "_CACHE_ENABLED", True)
    monkeypatch.setattr(solution, "_CACHE_PATH", str(tmp_path / "llm_cache.json"))
    monkeypatch.setattr(solution, "_DRY_RUN", False)
    solution.reset_llm_cost_records()
    calls = []
    response = {
        "choices": [{"message": {"content": "def parse_csv(raw_csv): return raw_csv"}}],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 40,
            "total_tokens": 160,
            "prompt_tokens_details": {"cached_tokens": 20},
            "completion_tokens_details": {"reasoning_tokens": 12},
        },
    }

    def fake_urlopen(request, timeout):
        calls.append(request)
        return BytesIO(json.dumps(response).encode("utf-8"))

    monkeypatch.setattr(solution.urllib_request, "urlopen", fake_urlopen)
    assert solution._query_llm("test prompt") == response["choices"][0]["message"]["content"]
    assert solution._query_llm("test prompt") == response["choices"][0]["message"]["content"]

    records = solution.get_llm_cost_records()
    summary = solution.get_llm_cost_summary()
    assert len(calls) == 1
    assert records[0]["usage"] == response["usage"]
    assert records[0]["reasoning_tokens"] == 12
    assert records[1]["local_cache_hit"] is True
    assert records[1]["billable_cost_usd"] == 0
    assert summary["api_requests"] == 1
    assert summary["usage_recorded_calls"] == 1
    assert summary["uncached_input_tokens"] == 100
    assert summary["cached_input_tokens"] == 20
    assert summary["completion_tokens"] == 40
    assert summary["billable_cost_usd"] == pytest.approx(0.0000302)


def test_no_content_response_keeps_billable_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://example.test/v1/chat/completions")
    monkeypatch.setattr(solution, "_CACHE_ENABLED", False)
    monkeypatch.setattr(solution, "_DRY_RUN", False)
    solution.reset_llm_cost_records()
    response = {
        "choices": [{"message": {"content": None, "reasoning": "thinking"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
    }
    monkeypatch.setattr(
        solution.urllib_request, "urlopen",
        lambda request, timeout: BytesIO(json.dumps(response).encode("utf-8")),
    )

    with pytest.raises(RuntimeError, match="missing assistant content"):
        solution._query_llm("failing prompt")

    record = solution.get_llm_cost_records()[0]
    assert record["status"] == "missing_assistant_content"
    assert record["completion_tokens"] == 30
    assert record["billable_cost_usd"] == pytest.approx(0.000025)


def test_missing_usage_does_not_become_zero_cost(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://example.test/v1/chat/completions")
    monkeypatch.setattr(solution, "_CACHE_ENABLED", False)
    monkeypatch.setattr(solution, "_DRY_RUN", False)
    solution.reset_llm_cost_records()
    response = {"choices": [{"message": {"content": "def parse_csv(raw_csv): return raw_csv"}}]}
    monkeypatch.setattr(
        solution.urllib_request, "urlopen",
        lambda request, timeout: BytesIO(json.dumps(response).encode("utf-8")),
    )

    solution._query_llm("prompt without reported usage")

    summary = solution.get_llm_cost_summary()
    assert summary["usage_missing_calls"] == 1
    assert summary["completion_tokens"] is None
    assert summary["billable_cost_usd"] is None
