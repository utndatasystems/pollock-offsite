from __future__ import annotations

import os


LLM_BACKEND_ENV = "FULL_LLM_LOADER_BACKEND"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_API_BASE_ENV = "OPENAI_API_BASE"
OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
OLLAMA_API_BASE_ENV = "OLLAMA_API_BASE"

OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_DEFAULT_API_BASE = "https://api.openai.com/v1"
OLLAMA_DEFAULT_MODEL = "qwen3.5:0.8b"
OLLAMA_DEFAULT_API_BASE = "http://localhost:11434/v1"


# Keep the get_openai_* names because llm_utils uses an OpenAI-compatible
# chat-completions API for both OpenAI and Ollama.
def get_llm_backend() -> str:
    backend = os.environ.get(LLM_BACKEND_ENV, "openai").strip().lower()
    if backend not in {"openai", "ollama"}:
        raise ValueError(
            f"{LLM_BACKEND_ENV} must be 'openai' or 'ollama', received {backend!r}."
        )
    return backend


def get_openai_api_base() -> str:
    if get_llm_backend() == "ollama":
        return os.environ.get(
            OLLAMA_API_BASE_ENV,
            OLLAMA_DEFAULT_API_BASE,
        ).rstrip("/")

    return os.environ.get(
        OPENAI_API_BASE_ENV,
        OPENAI_DEFAULT_API_BASE,
    ).rstrip("/")


def get_openai_api_key() -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV)

    if get_llm_backend() == "ollama":
        # Ollama's OpenAI-compatible endpoint accepts any bearer token and often
        # ignores auth entirely. Returning a dummy value keeps request shape stable.
        return api_key or "ollama"

    if not api_key:
        raise EnvironmentError(
            f"Missing {OPENAI_API_KEY_ENV}. Set it before using the OpenAI backend, "
            f"or set {LLM_BACKEND_ENV}=ollama for a local Ollama model."
        )

    return api_key


def get_openai_model() -> str:
    if get_llm_backend() == "ollama":
        return os.environ.get(
            OLLAMA_MODEL_ENV,
            OLLAMA_DEFAULT_MODEL,
        )

    return os.environ.get(
        OPENAI_MODEL_ENV,
        OPENAI_DEFAULT_MODEL,
    )
