from __future__ import annotations

import json
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_llm_cache_dir() -> Path:
    dataset = os.environ.get("DATASET", "polluted_files")
    return REPO_ROOT / "results" / "full_llm_loader" / dataset / "llm_cache"


DEFAULT_LLM_CACHE_DIR = _default_llm_cache_dir()
LLM_CACHE_VERSION = 1
_LAST_LLM_COST_RECORD: dict | None = None

DEFAULT_MODEL_PRICES_USD_PER_1M = {
    "gpt-4o": {
        "input": 2.50,
        "cached_input": 1.25,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "cached_input": 0.075,
        "output": 0.60,
    },
}

try:
    from .llm_config import (
        get_llm_backend,
        get_openai_api_base,
        get_openai_api_key,
        get_openai_model,
    )
except ImportError:
    from llm_config import (
        get_llm_backend,
        get_openai_api_base,
        get_openai_api_key,
        get_openai_model,
    )


def _completion_token_limit_param(model: str) -> str:
    normalized = model.lower()
    if normalized.startswith("gpt-5") or normalized.startswith("o"):
        return "max_completion_tokens"
    return "max_tokens"


def _supports_temperature(model: str) -> bool:
    return not model.lower().startswith("gpt-5.6")


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


def get_last_llm_cost_record() -> dict | None:
    """Return token and cost metadata for the most recent LLM call."""
    return dict(_LAST_LLM_COST_RECORD) if _LAST_LLM_COST_RECORD else None


def _query_llm(
    messages: list[dict[str, str]],
    cache_context: dict | None = None,
    verbose: bool = False,
) -> str:
    """Function that supports both OpenAI and Ollama"""
    global _LAST_LLM_COST_RECORD
    _LAST_LLM_COST_RECORD = None

    # Get environment variables for API base, key, and model
    backend = get_llm_backend()
    api_key = get_openai_api_key()
    api_base = get_openai_api_base().rstrip("/")
    model = get_openai_model()

    # Construct the request URL and headers (Ollama uses the same endpoint structure as OpenAI)
    url = f"{api_base}/chat/completions"

    # Set up the request headers and payload
    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Construct the request payload and limit max tokens.
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    payload[_completion_token_limit_param(model)] = 16000
    if _supports_temperature(model):
        payload["temperature"] = 0.0

    if backend == "ollama":
        payload["reasoning_effort"] = os.environ.get(
            "OLLAMA_REASONING_EFFORT",
            "none",
        )

    cache_path = _llm_cache_path(
        api_base=api_base,
        payload=payload,
        cache_context=cache_context,
    )
    bypass_cache = _env_truthy('FULL_LLM_LOADER_BYPASS_CACHE')
    cached_record = None if bypass_cache else _read_llm_cache(cache_path)
    if cached_record is not None:
        if verbose:
            print(f"Using cached LLM response: {cache_path}")
        _LAST_LLM_COST_RECORD = _build_cost_record(
            backend=backend,
            model=model,
            api_base=api_base,
            cache_path=cache_path,
            usage=cached_record.get("usage"),
            local_cache_hit=True,
        )
        return cached_record["content"]
    if bypass_cache:
        if verbose:
            print(f"Bypassing local LLM response cache: {cache_path}")

    if verbose:
        print(f"Querying {backend} LLM with model: {model} at API base: {api_base}")

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=300,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            error_body = response.json()
            error = error_body.get("error", {})

            if isinstance(error, dict):
                detail = error.get("message") or response.text
                error_type = error.get("type")
                if error_type:
                    detail = f"{error_type}: {detail}"
            else:
                detail = str(error) or response.text
        except ValueError:
            detail = response.text

        raise requests.HTTPError(
            f"{exc}\nLLM API error: {detail}",
            response=response,
        ) from exc

    body = response.json()

    choices = body.get("choices")
    if not choices:
        raise RuntimeError(
            f"Unexpected LLM response: missing choices\nResponse: {body}"
        )

    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        limit_param = _completion_token_limit_param(model)
        limit_value = payload.get(limit_param)
        raise RuntimeError(
            "LLM response was truncated because it reached the configured "
            f"output token limit ({limit_param}={limit_value}). Increase the "
            "limit or reduce the requested output before parsing this result."
        )

    message = choice.get("message", {})
    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        message_reasoning = message.get("reasoning") or message.get("thinking")
        if backend == "ollama" and message_reasoning:
            raise RuntimeError(
                "Ollama returned reasoning/thinking tokens but no final message "
                f"content. finish_reason={finish_reason!r}. This usually means "
                "the model spent its output budget thinking. The request sets "
                "reasoning_effort='none' by default; if this persists, update "
                "Ollama or set OLLAMA_REASONING_EFFORT=none explicitly."
            )

        raise RuntimeError(
            f"Unexpected LLM response: missing message content\nResponse: {body}"
        )

    usage = body.get("usage")
    _LAST_LLM_COST_RECORD = _build_cost_record(
        backend=backend,
        model=model,
        api_base=api_base,
        cache_path=cache_path,
        usage=usage,
        local_cache_hit=False,
    )

    _write_llm_cache(
        cache_path=cache_path,
        api_base=api_base,
        payload=payload,
        content=content,
        usage=usage,
        cost_record=_LAST_LLM_COST_RECORD,
    )

    return content


def _llm_cache_path(
    *,
    api_base: str,
    payload: dict,
    cache_context: dict | None = None,
) -> Path:
    cache_dir = Path(
        os.environ.get(
            "FULL_LLM_LOADER_CACHE_DIR",
            str(DEFAULT_LLM_CACHE_DIR),
        )
    )
    cache_key = {
        "cache_version": LLM_CACHE_VERSION,
        "api_base": api_base,
        "payload": payload,
        "cache_context": cache_context or {},
    }
    digest = hashlib.sha256(
        json.dumps(
            cache_key,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return cache_dir / f"{digest}.json"


def _read_llm_cache(cache_path: Path) -> dict | None:
    if not cache_path.is_file():
        return None

    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Ignoring unreadable LLM cache entry {cache_path}: {exc}")
        return None

    content = cached.get("content")
    if isinstance(content, str) and content.strip():
        return cached

    print(f"Ignoring invalid LLM cache entry {cache_path}: missing content")
    return None


def _write_llm_cache(
    *,
    cache_path: Path,
    api_base: str,
    payload: dict,
    content: str,
    usage: dict | None,
    cost_record: dict | None,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_record = {
        "cache_version": LLM_CACHE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_base": api_base,
        "payload": payload,
        "content": content,
        "usage": usage,
        "cost": cost_record,
    }
    temporary_path = cache_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(cache_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(cache_path)


def _build_cost_record(
    *,
    backend: str,
    model: str,
    api_base: str,
    cache_path: Path,
    usage: dict | None,
    local_cache_hit: bool,
) -> dict:
    usage = usage if isinstance(usage, dict) else {}
    prompt_tokens = _int_or_zero(usage.get("prompt_tokens"))
    completion_tokens = _int_or_zero(usage.get("completion_tokens"))
    total_tokens = _int_or_zero(usage.get("total_tokens"))
    prompt_details = usage.get("prompt_tokens_details")
    cached_input_tokens = 0
    if isinstance(prompt_details, dict):
        cached_input_tokens = _int_or_zero(prompt_details.get("cached_tokens"))
    uncached_input_tokens = max(prompt_tokens - cached_input_tokens, 0)
    prices = _model_prices_usd_per_1m(model, backend)

    input_cost = _token_cost(uncached_input_tokens, prices.get("input"))
    cached_input_cost = _token_cost(cached_input_tokens, prices.get("cached_input"))
    output_cost = _token_cost(completion_tokens, prices.get("output"))
    estimated_api_cost = _sum_costs(input_cost, cached_input_cost, output_cost)

    return {
        "backend": backend,
        "model": model,
        "api_base": api_base,
        "local_cache_hit": local_cache_hit,
        "cache_path": str(cache_path),
        "prompt_tokens": prompt_tokens,
        "cached_input_tokens": cached_input_tokens,
        "uncached_input_tokens": uncached_input_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "input_usd_per_1m": prices.get("input"),
        "cached_input_usd_per_1m": prices.get("cached_input"),
        "output_usd_per_1m": prices.get("output"),
        "input_cost_usd": input_cost,
        "cached_input_cost_usd": cached_input_cost,
        "output_cost_usd": output_cost,
        "estimated_api_cost_usd": estimated_api_cost,
        "billable_cost_usd": 0.0 if local_cache_hit else estimated_api_cost,
    }


def _model_prices_usd_per_1m(model: str, backend: str) -> dict:
    input_override = os.environ.get("FULL_LLM_LOADER_INPUT_USD_PER_1M")
    cached_input_override = os.environ.get("FULL_LLM_LOADER_CACHED_INPUT_USD_PER_1M")
    output_override = os.environ.get("FULL_LLM_LOADER_OUTPUT_USD_PER_1M")
    if input_override or cached_input_override or output_override:
        input_price = _float_or_none(input_override)
        cached_input_price = _float_or_none(cached_input_override)
        return {
            "input": input_price,
            "cached_input": cached_input_price if cached_input_price is not None else input_price,
            "output": _float_or_none(output_override),
        }

    if backend == "ollama":
        return {"input": 0.0, "cached_input": 0.0, "output": 0.0}

    normalized = model.lower()
    for prefix, prices in sorted(
        DEFAULT_MODEL_PRICES_USD_PER_1M.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if normalized == prefix or normalized.startswith(prefix + "-"):
            return prices
    return {"input": None, "cached_input": None, "output": None}


def _token_cost(tokens: int, usd_per_1m: float | None) -> float | None:
    if usd_per_1m is None:
        return None
    return tokens * usd_per_1m / 1_000_000


def _sum_costs(*costs: float | None) -> float | None:
    if any(cost is None for cost in costs):
        return None
    return sum(costs)


def _int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _clean_fixed_csv(raw: str) -> str:
    """Remove a single Markdown code fence around the whole LLM response."""
    text = raw.strip()

    match = re.fullmatch(
        r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n?```",
        text,
        flags=re.S,
    )

    return match.group(1).strip() if match else text


def _extract_sections(llm_output: str) -> tuple[str, dict]:
    """Extract the shared FIXED CSV / ERROR REPORT response format."""
    fixed_csv = _extract_marked_text(
        llm_output,
        "--BEGIN FIXED CSV--",
        "--END FIXED CSV--",
    )
    if fixed_csv is None:
        fixed_csv = _extract_unmarked_csv(llm_output)

    error_report = _extract_marked_json(
        llm_output,
        "--BEGIN ERROR REPORT--",
        "--END ERROR REPORT--",
    )

    return fixed_csv, error_report or _missing_error_report()


def _extract_marked_text(
    text: str,
    begin_marker: str,
    end_marker: str,
) -> str | None:
    match = re.search(
        f"{re.escape(begin_marker)}(.*?){re.escape(end_marker)}",
        text,
        flags=re.S,
    )
    return match.group(1).strip() if match else None


def _extract_unmarked_csv(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if line.strip()
        and not line.strip().startswith("```")
        and not line.strip().startswith("--")
        and not line.strip().startswith("{")
        and not line.strip().startswith("}")
    ]

    if not lines:
        raise ValueError(
            "Could not extract fixed CSV from the LLM output. "
            "The response had no markers and no plausible CSV lines."
        )

    return "\n".join(lines).strip()


def _extract_marked_json(
    text: str,
    begin_marker: str,
    end_marker: str,
) -> dict | None:
    section = _extract_marked_text(text, begin_marker, end_marker)
    if section is None:
        return None

    try:
        parsed = json.loads(section)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Unable to parse JSON section between {begin_marker} and "
            f"{end_marker}: {exc}\n{section}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Expected JSON object between {begin_marker} and {end_marker}, "
            f"received {type(parsed).__name__}."
        )

    return parsed


def _missing_error_report() -> dict:
    return {
        "fixed_errors": [
            {
                "type": "missing_error_report",
                "description": (
                    "The LLM returned fixed CSV content but did not include a "
                    "structured error report."
                ),
                "rows": [],
            }
        ],
        "summary": "No structured error report was returned by the LLM.",
    }
