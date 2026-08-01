import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sut.llm_hybrid_parser.llm import _LLM_RESPONSE_CACHE
from sut.llm_hybrid_parser.solution import TRACE_VERSION


# --- JSON utils ---
class TraceWriter:
    """A simple trace writer that writes events to a JSONL file."""
    def __init__(self, path: Optional[str], reset: bool = True):
        self.path = path
        if self.path and reset:
            sidecar_dir = os.path.dirname(self.path)
            if sidecar_dir:
                os.makedirs(sidecar_dir, exist_ok=True)
            with open(self.path, "w", encoding="utf-8"):
                pass

    def write(self, event_type: str, **payload: Any) -> None:
        if not self.path:
            return
        event = {
            "type": event_type,
            "trace_version": TRACE_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        event.update(payload)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str))
            f.write("\n")


# --- LLM cache and state helpers ---
def configure_llm_cache(path: Optional[str] = None, enabled: bool = True) -> None:
    """Configure the on-disk cache used for LLM responses.

    Args:
        path: Optional path to a JSON cache file. If provided, cached LLM
            responses are loaded from and saved to this file.
        enabled: Whether LLM response caching should be enabled.

    Side effects:
        Updates the global cache configuration and marks the cache as not yet
        loaded so it can be reloaded lazily on the next cache access.
    """
    global _LLM_CACHE_PATH, _LLM_CACHE_ENABLED, _LLM_CACHE_LOADED
    _LLM_CACHE_PATH = path
    _LLM_CACHE_ENABLED = enabled
    _LLM_CACHE_LOADED = False


def configure_llm_dry_run(enabled: bool) -> None:
    """Enable or disable dry-run mode for LLM calls.

    Args:
        enabled: If True, LLM calls should avoid making real API requests and
            instead use dry-run behavior. If False, normal LLM calls are allowed.

    Side effects:
        Updates the global dry-run flag used by the LLM call machinery.
    """
    global _LLM_DRY_RUN
    _LLM_DRY_RUN = enabled


def get_llm_cache_stats() -> Dict[str, int]:
    """Enable or disable dry-run mode for LLM calls.

    Args:
        enabled: If True, LLM calls should avoid making real API requests and
            instead use dry-run behavior. If False, normal LLM calls are allowed.

    Side effects:
        Updates the global dry-run flag used by the LLM call machinery.
    """
    return dict(_LLM_CALL_STATS)


def _ensure_cache_loaded() -> None:
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
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
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
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
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
    return os.environ.get("OPENAI_ENDPOINT") or DEFAULT_OPENAI_ENDPOINT


def _openai_model() -> str:
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
    return os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL


def _openai_api_key() -> Optional[str]:
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
    return os.environ.get("OPENAI_API_KEY")


def _prompt_hash(prompt: str) -> str:
    """Load the LLM response cache from disk if it has not already been loaded.

    The cache is loaded lazily from ``_LLM_CACHE_PATH``. If no cache path is
    configured, the cache has already been loaded, the file does not exist, or
    the file cannot be parsed as a dictionary, this function returns without
    raising an exception.

    Side effects:
        Marks the cache as loaded and updates ``_LLM_RESPONSE_CACHE`` with any
        cached responses read from disk.
    """
    key = _openai_model() + "\x00" + prompt
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

