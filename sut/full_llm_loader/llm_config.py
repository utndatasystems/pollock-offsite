from __future__ import annotations
import os


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_API_BASE_ENV = "OPENAI_API_BASE"

OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_DEFAULT_API_BASE = "https://api.openai.com/v1"


# --- OpenAI Configuration Functions ---

def get_openai_api_key() -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV)

    if not api_key:
        raise EnvironmentError(
            f"Missing {OPENAI_API_KEY_ENV}. "
            "Set it before using the LLM parser."
        )

    return api_key


def get_openai_model() -> str:
    return os.environ.get(
        OPENAI_MODEL_ENV,
        OPENAI_DEFAULT_MODEL,
    )


def get_openai_api_base() -> str:
    return os.environ.get(
        OPENAI_API_BASE_ENV,
        OPENAI_DEFAULT_API_BASE,
    ).rstrip("/")