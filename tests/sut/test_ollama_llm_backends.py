import json

import pytest

from sut.full_llm_loader import llm_config
from sut.llm_hybrid_parser_Robin import llm


class _Trace:
    def write(self, *_args, **_kwargs):
        pass


class _Response:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def read(self):
        return json.dumps(self._body).encode()


def test_full_loader_resolves_ollama_without_api_key(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert llm_config.get_llm_backend() == "ollama"
    assert llm_config.get_openai_api_base() == "http://localhost:11434/v1"
    assert llm_config.get_openai_api_key() == "ollama"
    assert llm_config.get_openai_model() == "qwen3:8b"


def test_hybrid_sends_ollama_compatible_request(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm.configure_llm_cache(enabled=False)
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"choices": [{"message": {"content": '{"ok": true}'}}]})

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)

    response = llm.call_llm("hello", _Trace(), "test")

    assert response == '{"ok": true}'
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["payload"]["model"] == "qwen3:8b"
    assert captured["payload"]["reasoning_effort"] == "none"
    assert captured["timeout"] == 300
    assert captured["headers"]["Authorization"] == "Bearer ollama"


@pytest.mark.parametrize("backend", ["other", ""])
def test_hybrid_rejects_unknown_backend(monkeypatch, backend):
    monkeypatch.setenv("LLM_BACKEND", backend)
    with pytest.raises(RuntimeError, match="LLM_BACKEND"):
        llm._llm_backend()
