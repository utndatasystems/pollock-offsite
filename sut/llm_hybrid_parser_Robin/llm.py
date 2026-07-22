import hashlib
import json
import math
import os
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_OPENAI_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
#DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_MAX_LLM_TOKENS = 100_000

_LLM_RESPONSE_CACHE: Dict[str, str] = {}
_LLM_DRY_RUN_ESTIMATED_OUTPUT: Dict[str, int] = {}  # prompt_sha -> estimated chars for dry-run dedup
_LLM_CACHE_PATH: Optional[str] = None
_LLM_CACHE_ENABLED: bool = True
_LLM_CACHE_LOADED: bool = False
_LLM_CALL_STATS: Dict[str, int] = {
    "total": 0, "cached": 0,
    "input_chars_total": 0, "input_chars_cached": 0,
    "output_chars_fresh": 0, "output_chars_cached": 0,
}
_LLM_DRY_RUN: bool = False
_LLM_VERBOSE: bool = False
_LLM_MAX_ESTIMATED_TOKENS: int = DEFAULT_MAX_LLM_TOKENS


def configure_llm_cache(path: Optional[str] = None, enabled: bool = True) -> None:
    global _LLM_CACHE_PATH, _LLM_CACHE_ENABLED, _LLM_CACHE_LOADED
    _LLM_CACHE_PATH = path
    _LLM_CACHE_ENABLED = enabled
    _LLM_CACHE_LOADED = False


def configure_llm_dry_run(enabled: bool) -> None:
    global _LLM_DRY_RUN

    _LLM_DRY_RUN = enabled


def configure_llm_verbose(enabled: bool) -> None:
    global _LLM_VERBOSE

    _LLM_VERBOSE = enabled


def configure_llm_token_limit(max_tokens: int) -> None:
    """Set the approximate per-call token cap; zero disables the guard."""
    global _LLM_MAX_ESTIMATED_TOKENS

    _LLM_MAX_ESTIMATED_TOKENS = max(0, int(max_tokens))


def _estimate_tokens(input_chars: int, output_chars: int = 0) -> int:
    """Match the benchmark's existing rough estimate of four chars per token."""
    return math.ceil((max(0, input_chars) + max(0, output_chars)) / 4)


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


def _prompt_hash(prompt: str) -> str:
    key = _openai_model() + "\x00" + prompt
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def call_llm(prompt: str, trace: Any, event_type: str, estimated_output_chars: int = 0) -> str:
    if _LLM_CACHE_ENABLED:
        _ensure_cache_loaded()

    prompt_sha = _prompt_hash(prompt)
    _LLM_CALL_STATS["total"] += 1
    _LLM_CALL_STATS["input_chars_total"] += len(prompt)

    if _LLM_CACHE_ENABLED and prompt_sha in _LLM_RESPONSE_CACHE:
        response = _LLM_RESPONSE_CACHE[prompt_sha]
        _LLM_CALL_STATS["cached"] += 1
        _LLM_CALL_STATS["input_chars_cached"] += len(prompt)
        # For in-run dry-run dedup hits use the stored estimate, not len("{}") = 2
        out_chars = _LLM_DRY_RUN_ESTIMATED_OUTPUT.get(prompt_sha, len(response))
        _LLM_CALL_STATS["output_chars_cached"] += out_chars
        print(f"[LLM cache] reused cached result ({event_type})")
        trace.write(
            event_type,
            prompt_sha256=prompt_sha,
            prompt=prompt,
            response=response,
            cached=True,
            model=_openai_model(),
            endpoint=_openai_endpoint(),
        )
        _print_verbose(event_type, prompt, response, cached=True)
        return response

    if _LLM_DRY_RUN:
        _LLM_CALL_STATS["output_chars_fresh"] += estimated_output_chars
        _LLM_RESPONSE_CACHE[prompt_sha] = "{}"  # deduplicate within this run, never saved to disk
        _LLM_DRY_RUN_ESTIMATED_OUTPUT[prompt_sha] = estimated_output_chars
        trace.write(event_type, prompt_sha256=prompt_sha, prompt=prompt, dry_run=True)
        return "{}"

    estimated_tokens = _estimate_tokens(len(prompt), estimated_output_chars)
    if (
        _LLM_MAX_ESTIMATED_TOKENS > 0
        and estimated_tokens > _LLM_MAX_ESTIMATED_TOKENS
    ):
        print(
            f"[LLM skipped] {event_type}: estimated {estimated_tokens:,} tokens "
            f"exceeds the {_LLM_MAX_ESTIMATED_TOKENS:,}-token limit"
        )
        trace.write(
            event_type,
            prompt_sha256=prompt_sha,
            skipped=True,
            skip_reason="estimated_token_limit",
            estimated_tokens=estimated_tokens,
            max_estimated_tokens=_LLM_MAX_ESTIMATED_TOKENS,
            model=_openai_model(),
        )
        return "{}"

    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI-compatible API key found. Set OPENAI_API_KEY."
        )

    payload = json.dumps({
        "model": _openai_model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode("utf-8")

    request = urllib.request.Request(
        _openai_endpoint(),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response_obj:
        data = json.loads(response_obj.read().decode("utf-8"))
    response = data["choices"][0]["message"]["content"]
    _LLM_CALL_STATS["output_chars_fresh"] += len(response)

    if _LLM_CACHE_ENABLED:
        _LLM_RESPONSE_CACHE[prompt_sha] = response
        _save_cache_to_disk()

    trace.write(
        event_type,
        prompt_sha256=prompt_sha,
        prompt=prompt,
        response=response,
        cached=False,
        model=_openai_model(),
        endpoint=_openai_endpoint(),
    )
    _print_verbose(event_type, prompt, response, cached=False)
    return response


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
