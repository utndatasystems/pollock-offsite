import pytest

from sut.full_llm_loader import llm_utils


def test_cost_record_includes_cache_writes_and_reasoning_tokens(tmp_path):
    record = llm_utils._build_cost_record(
        backend="openai", model="gpt-5.6-luna", api_base="https://api.openai.com/v1",
        cache_path=tmp_path / "cache.json", local_cache_hit=False,
        usage={
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "total_tokens": 1100,
            "prompt_tokens_details": {"cached_tokens": 200, "cache_write_tokens": 300},
            "completion_tokens_details": {"reasoning_tokens": 70},
        },
    )
    assert record["ordinary_input_tokens"] == 500
    assert record["cache_write_tokens"] == 300
    assert record["input_cost_usd"] == pytest.approx(0.0001)
    assert record["cached_input_cost_usd"] == pytest.approx(0.000004)
    assert record["cache_write_cost_usd"] == pytest.approx(0.000075)
    assert record["output_cost_usd"] == pytest.approx(0.00012)
    assert record["billable_cost_usd"] == pytest.approx(0.000299)


def test_reasoning_only_reply_keeps_billable_usage(monkeypatch, tmp_path):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"finish_reason": "stop", "message": {"content": None}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 80},
            }

    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("FULL_LLM_LOADER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FULL_LLM_LOADER_BYPASS_CACHE", "1")
    monkeypatch.setattr(llm_utils.requests, "post", lambda *_args, **_kwargs: Response())

    with pytest.raises(RuntimeError, match="missing message content"):
        llm_utils._query_llm([{"role": "user", "content": "test"}])
    assert llm_utils.get_last_llm_cost_record()["billable_cost_usd"] == pytest.approx(
        0.000116
    )
