from __future__ import annotations

import os

OPENAI_API_BASE_ENV = "OPENAI_API_BASE"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"

OPENAI_DEFAULT_API_BASE = "http://localhost:11434/v1"
OPENAI_DEFAULT_MODEL = "qwen3.5:0.8b"


def get_openai_api_base() -> str:
    return os.environ.get(
        OPENAI_API_BASE_ENV,
        OPENAI_DEFAULT_API_BASE,
    ).rstrip("/")


def get_openai_api_key() -> str:
    # Ollama ignores this value for local requests.
    return os.environ.get(OPENAI_API_KEY_ENV, "ollama")


def get_openai_model() -> str:
    return os.environ.get(
        OPENAI_MODEL_ENV,
        OPENAI_DEFAULT_MODEL,
    )