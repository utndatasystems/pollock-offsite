import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


DEFAULT_OPENAI_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
#DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

DEFAULT_MODEL_PRICES_USD_PER_1M = {
    # Short-context prices. Long-context pricing requires separate context-tier
    # handling and is intentionally not inferred here.
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
    "gpt-5.4": {
        "input": 2.50,
        "cached_input": 0.25,
        "output": 15.00,
    },
    "gpt-5.4-mini": {
        "input": 0.75,
        "cached_input": 0.075,
        "output": 4.50,
    },
    "gpt-5.5": {
        "input": 5.00,
        "cached_input": 0.50,
        "output": 30.00,
    },
}

_LLM_RESPONSE_CACHE: Dict[str, Any] = {}
_LLM_CACHE_PATH: Optional[str] = None
_LLM_CACHE_ENABLED: bool = True
_LLM_CACHE_LOADED: bool = False
_LLM_CALL_STATS: Dict[str, int] = {"total": 0, "cached": 0}
_LLM_COST_RECORDS: List[Dict[str, Any]] = []
_LLM_VERBOSE: bool = False


def configure_llm_cache(path: Optional[str] = None, enabled: bool = True) -> None:
    global _LLM_CACHE_PATH, _LLM_CACHE_ENABLED, _LLM_CACHE_LOADED
    _LLM_CACHE_PATH = path
    _LLM_CACHE_ENABLED = enabled
    _LLM_CACHE_LOADED = False


def configure_llm_verbose(enabled: bool) -> None:
    global _LLM_VERBOSE

    _LLM_VERBOSE = enabled


def _print_verbose(event_type: str, prompt: str, response: str, cached: bool) -> None:
    if not _LLM_VERBOSE:
        return
    tag = "cached" if cached else "fresh"
    print(f"\n===== LLM {event_type} ({tag}) =====")
    print("----- prompt -----")
    print(prompt)
    print("----- response -----")
    print(response)
    print("===== end =====\n")


def get_llm_cache_stats() -> Dict[str, int]:
    return dict(_LLM_CALL_STATS)


def reset_llm_cost_records() -> None:
    """Start a new accounting scope, normally one benchmark file repetition."""
    _LLM_COST_RECORDS.clear()


def get_llm_cost_records() -> List[Dict[str, Any]]:
    """Return actual API token/cost metadata for calls in the current scope."""
    return [dict(record) for record in _LLM_COST_RECORDS]


def get_llm_cost_summary() -> Dict[str, Any]:
    """Aggregate all LLM calls made since ``reset_llm_cost_records``."""
    records = get_llm_cost_records()
    token_fields = (
        "prompt_tokens",
        "cached_input_tokens",
        "uncached_input_tokens",
        "completion_tokens",
        "total_tokens",
    )
    cost_fields = (
        "input_cost_usd",
        "cached_input_cost_usd",
        "output_cost_usd",
        "estimated_api_cost_usd",
        "billable_cost_usd",
    )
    summary: Dict[str, Any] = {
        "llm_calls": len(records),
        "local_cache_hits": sum(bool(record.get("local_cache_hit")) for record in records),
    }
    for field in token_fields:
        summary[field] = sum(_int_or_zero(record.get(field)) for record in records)
    for field in cost_fields:
        values = [record.get(field) for record in records]
        summary[field] = (
            None if any(value is None for value in values) else sum(values, 0.0)
        )
    return summary


def _ensure_cache_loaded() -> None:
    global _LLM_CACHE_LOADED
    if _LLM_CACHE_LOADED or not _LLM_CACHE_PATH:
        return
    _LLM_CACHE_LOADED = True
    if not os.path.exists(_LLM_CACHE_PATH):
        return
    try:
        with open(_LLM_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _LLM_RESPONSE_CACHE.update(data)
    except Exception:
        pass


def _save_cache_to_disk() -> None:
    if not _LLM_CACHE_PATH:
        return
    try:
        cache_dir = os.path.dirname(_LLM_CACHE_PATH)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with open(_LLM_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_LLM_RESPONSE_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _openai_endpoint() -> str:
    return os.environ.get("OPENAI_ENDPOINT") or DEFAULT_OPENAI_ENDPOINT


def _openai_model() -> str:
    return os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL


def _openai_api_key() -> Optional[str]:
    return os.environ.get("OPENAI_API_KEY")


def _supports_temperature(model: str) -> bool:
    normalized = model.lower()
    # New GPT-5.6 chat-completions models reject configurable temperature.
    return not normalized.startswith("gpt-5.6")


def _prompt_hash(prompt: str) -> str:
    key = _openai_model() + "\x00" + prompt
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _cached_response(entry: Any) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Read both the new structured cache and legacy hash-to-string entries."""
    if isinstance(entry, str):
        return entry, None
    if isinstance(entry, dict) and isinstance(entry.get("content"), str):
        usage = entry.get("usage")
        return entry["content"], usage if isinstance(usage, dict) else None
    return None, None


def call_llm(prompt: str, trace: Any, event_type: str) -> str:
    if _LLM_CACHE_ENABLED:
        _ensure_cache_loaded()

    prompt_sha = _prompt_hash(prompt)
    _LLM_CALL_STATS["total"] += 1

    if _LLM_CACHE_ENABLED and prompt_sha in _LLM_RESPONSE_CACHE:
        response, usage = _cached_response(_LLM_RESPONSE_CACHE[prompt_sha])
        if response is not None:
            _LLM_CALL_STATS["cached"] += 1
            cost_record = _build_cost_record(
                model=_openai_model(),
                endpoint=_openai_endpoint(),
                usage=usage,
                local_cache_hit=True,
            )
            _LLM_COST_RECORDS.append(cost_record)
            print(f"[LLM cache] reused cached result ({event_type})")
            trace.write(
                event_type,
                prompt_sha256=prompt_sha,
                prompt=prompt,
                response=response,
                cached=True,
                usage=usage,
                cost=cost_record,
                model=_openai_model(),
                endpoint=_openai_endpoint(),
            )
            _print_verbose(event_type, prompt, response, cached=True)
            return response

    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI-compatible API key found. Set OPENAI_API_KEY."
        )

    model = _openai_model()
    payload_dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if _supports_temperature(model):
        payload_dict["temperature"] = 0
    payload = json.dumps(payload_dict).encode("utf-8")

    request = urllib.request.Request(
        _openai_endpoint(),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response_obj:
            data = json.loads(response_obj.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP Error {exc.code}: {exc.reason}\n{body}") from exc
    response = data["choices"][0]["message"]["content"]
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    cost_record = _build_cost_record(
        model=model,
        endpoint=_openai_endpoint(),
        usage=usage,
        local_cache_hit=False,
    )
    _LLM_COST_RECORDS.append(cost_record)

    if _LLM_CACHE_ENABLED:
        _LLM_RESPONSE_CACHE[prompt_sha] = {
            "content": response,
            "usage": usage,
            "cost": cost_record,
        }
        _save_cache_to_disk()

    trace.write(
        event_type,
        prompt_sha256=prompt_sha,
        prompt=prompt,
        response=response,
        cached=False,
        usage=usage,
        cost=cost_record,
        model=_openai_model(),
        endpoint=_openai_endpoint(),
    )
    _print_verbose(event_type, prompt, response, cached=False)
    return response


def _build_cost_record(
    *,
    model: str,
    endpoint: str,
    usage: Optional[Dict[str, Any]],
    local_cache_hit: bool,
) -> Dict[str, Any]:
    usage = usage if isinstance(usage, dict) else {}
    prompt_tokens = _int_or_zero(usage.get("prompt_tokens"))
    completion_tokens = _int_or_zero(usage.get("completion_tokens"))
    total_tokens = _int_or_zero(usage.get("total_tokens"))
    prompt_details = usage.get("prompt_tokens_details")
    cached_input_tokens = 0
    if isinstance(prompt_details, dict):
        cached_input_tokens = _int_or_zero(prompt_details.get("cached_tokens"))
    uncached_input_tokens = max(prompt_tokens - cached_input_tokens, 0)
    prices = _model_prices_usd_per_1m(model)

    input_cost = _token_cost(uncached_input_tokens, prices.get("input"))
    cached_input_cost = _token_cost(
        cached_input_tokens, prices.get("cached_input")
    )
    output_cost = _token_cost(completion_tokens, prices.get("output"))
    estimated_api_cost = _sum_costs(
        input_cost, cached_input_cost, output_cost
    )

    return {
        "model": model,
        "endpoint": endpoint,
        "local_cache_hit": local_cache_hit,
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


def _model_prices_usd_per_1m(model: str) -> Dict[str, Optional[float]]:
    input_override = os.environ.get("HYBRID_LLM_INPUT_USD_PER_1M")
    cached_input_override = os.environ.get(
        "HYBRID_LLM_CACHED_INPUT_USD_PER_1M"
    )
    output_override = os.environ.get("HYBRID_LLM_OUTPUT_USD_PER_1M")
    if input_override or cached_input_override or output_override:
        input_price = _float_or_none(input_override)
        cached_input_price = _float_or_none(cached_input_override)
        return {
            "input": input_price,
            "cached_input": (
                cached_input_price
                if cached_input_price is not None
                else input_price
            ),
            "output": _float_or_none(output_override),
        }

    prices = DEFAULT_MODEL_PRICES_USD_PER_1M.get(model.lower())
    if prices is not None:
        return dict(prices)
    return {"input": None, "cached_input": None, "output": None}


def _token_cost(tokens: int, usd_per_1m: Optional[float]) -> Optional[float]:
    if usd_per_1m is None:
        return None
    return tokens * usd_per_1m / 1_000_000


def _sum_costs(*costs: Optional[float]) -> Optional[float]:
    if any(cost is None for cost in costs):
        return None
    return sum(costs)


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_json_object(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_obj = text.find("{")
    last_obj = text.rfind("}")
    first_arr = text.find("[")
    last_arr = text.rfind("]")
    candidates = []
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        candidates.append(text[first_obj:last_obj + 1])
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        candidates.append(text[first_arr:last_arr + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("LLM response did not contain valid JSON")
