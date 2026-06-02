"""LLM-call backends for Tier 2/3 triage.

Two backends:

- ``anthropic`` — Anthropic Python SDK. Default. Supports prompt caching
  (system prompt with ``cache_control``), reports input/output/cache token
  counts, computes USD cost from per-million-token prices.
- ``sf-claude`` — shells out to ``sf ai claude -b -- ...``. Used when an
  ``ANTHROPIC_API_KEY`` is unavailable. The system prompt is passed via
  ``--append-system-prompt`` and the user text via ``--print``. No token
  counts are returned, so the cost ledger only tracks call counts under
  this backend (the ``--budget-usd`` cap can't gate per-USD).

Both backends share:
- Persisted cost / call ledger at ``<out-dir>/triage_costs.json``.
- ``BudgetExceeded`` raised by :func:`call_triage` when the running USD
  total (anthropic backend) crosses ``budget_usd``.
- ``_extract_json`` to strip code fences / preamble around the model's
  JSON reply.

``call_triage`` is the single public entry point. The caller picks a
backend via :func:`build_backend` (selectable through
``SURVEY_LLM_BACKEND`` env var or the ``--backend`` CLI flag).
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


# Per-million-token pricing (USD), from claude-api skill / shared/models.md.
_PRICING = {
    "claude-haiku-4-5":  {"input": 1.00, "cached_in": 0.10, "cache_write": 1.25, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "cached_in": 0.30, "cache_write": 3.75, "output": 15.00},
    "claude-opus-4-7":   {"input": 5.00, "cached_in": 0.50, "cache_write": 6.25, "output": 25.00},
}

# Default ``sf ai claude`` invocation. The user passes the actual model and
# effort flags; this skeleton just declares the wrapper command + the bits
# that don't change per-call.
_DEFAULT_SF_CLAUDE_CMD = (
    "sf ai claude -b -- --dangerously-skip-permissions"
)

# Cap the per-call user-text size. Claude Code's stdin path is generous,
# but pathological CSVs (millions of rows, no newlines) shouldn't crash
# the subprocess layer. 200 KB is a comfortable buffer for our head/tail
# samples.
_MAX_PROMPT_CHARS = 200_000


class BudgetExceeded(RuntimeError):
    """Raised when the running cost ledger crosses the user-supplied cap."""


class PolicyRefusal(RuntimeError):
    """Raised when the upstream model refuses the prompt on policy grounds.

    Caller is expected to catch this and skip the file (don't retry — the
    refusal is deterministic on the prompt content).
    """


@dataclass
class TriageResult:
    parsed: dict
    model: str
    backend: str
    cost_usd: float
    input_tokens: int
    cached_input_tokens: int
    cache_creation_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Cost ledger
# ---------------------------------------------------------------------------


def _ledger_path(out_dir: Path) -> Path:
    return out_dir / "triage_costs.json"


def _load_ledger(out_dir: Path) -> dict:
    p = _ledger_path(out_dir)
    if not p.exists():
        return {"total_usd": 0.0, "by_model": {}, "n_calls": 0}
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return {"total_usd": 0.0, "by_model": {}, "n_calls": 0}


def _save_ledger(out_dir: Path, ledger: dict) -> None:
    p = _ledger_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(ledger, f, sort_keys=True, indent=2)


_LEDGER_LOCK = threading.Lock()


def _record_cost(out_dir: Path, model: str, cost_usd: float, budget_usd: float) -> None:
    """Append to the ledger and raise if the budget is exceeded."""
    with _LEDGER_LOCK:
        ledger = _load_ledger(out_dir)
        ledger["total_usd"] = round(float(ledger.get("total_usd", 0.0)) + cost_usd, 6)
        by_model = ledger.setdefault("by_model", {})
        by_model[model] = round(by_model.get(model, 0.0) + cost_usd, 6)
        ledger["n_calls"] = int(ledger.get("n_calls", 0)) + 1
        _save_ledger(out_dir, ledger)
        if ledger["total_usd"] > budget_usd:
            raise BudgetExceeded(
                f"triage budget exceeded: ${ledger['total_usd']:.4f} > ${budget_usd:.2f}"
            )


def _compute_cost(model: str, usage) -> float:
    p = _PRICING.get(model)
    if not p:
        return 0.0
    return round(
        (getattr(usage, "input_tokens", 0) or 0) * p["input"] / 1_000_000
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * p["cached_in"] / 1_000_000
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * p["cache_write"] / 1_000_000
        + (getattr(usage, "output_tokens", 0) or 0) * p["output"] / 1_000_000,
        6,
    )


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


class _Backend:
    """Backend protocol — overridden by Anthropic / sf-claude implementations."""

    name: str

    def call(
        self,
        *,
        model: str,
        system_prompt: list[dict],
        user_text: str,
        max_tokens: int,
        max_retries: int,
    ) -> tuple[str, dict]:
        """Return ``(raw_response_text, usage_dict)``.

        ``usage_dict`` keys: ``input_tokens``, ``cache_read_input_tokens``,
        ``cache_creation_input_tokens``, ``output_tokens``, ``cost_usd``.
        Backends that can't supply token counts should return zeros and
        a best-effort ``cost_usd``.
        """
        raise NotImplementedError


class AnthropicBackend(_Backend):
    name = "anthropic"

    def __init__(self) -> None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; cannot use the 'anthropic' backend."
            )
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic()

    def call(
        self,
        *,
        model: str,
        system_prompt: list[dict],
        user_text: str,
        max_tokens: int,
        max_retries: int,
    ) -> tuple[str, dict]:
        anthropic = self._anthropic
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_text}],
                )
                break
            except anthropic.RateLimitError as exc:
                last_exc = exc
                time.sleep(min(2 ** attempt, 30))
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                    time.sleep(min(2 ** attempt, 30))
                else:
                    raise
        else:
            raise last_exc  # type: ignore[misc]

        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        raw_text = "\n".join(text_blocks).strip()
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
            "cost_usd": _compute_cost(model, response.usage),
        }
        return raw_text, usage


class SfClaudeBackend(_Backend):
    """Shell out to ``sf ai claude -b -- ...``.

    The user's invocation:

        sf ai claude -b -- --dangerously-skip-permissions \\
            --model 'us.anthropic.claude-haiku-4-5' --effort medium

    The ``-b`` flag puts ``sf ai claude`` in batch mode; the rest are
    forwarded to Claude Code itself. We add ``--append-system-prompt``
    for the prompt-cached system text and ``--print "<user-text>"`` for
    the actual prompt.

    Override the wrapper command via ``SURVEY_SF_CLAUDE_CMD``.
    Override the model + effort by passing ``--model`` / ``--effort`` on
    the survey CLI.
    """

    name = "sf-claude"

    def __init__(self, effort: str | None = None) -> None:
        wrapper = os.environ.get("SURVEY_SF_CLAUDE_CMD", _DEFAULT_SF_CLAUDE_CMD)
        # Sanity-check the binary exists so we fail fast.
        head = shlex.split(wrapper)[0]
        if not shutil.which(head):
            raise RuntimeError(
                f"'{head}' not on PATH; cannot use the 'sf-claude' backend "
                f"(set SURVEY_SF_CLAUDE_CMD to override)."
            )
        self._wrapper_argv = shlex.split(wrapper)
        self._effort = effort or os.environ.get("SURVEY_SF_CLAUDE_EFFORT") or "medium"

    def call(
        self,
        *,
        model: str,
        system_prompt: list[dict],
        user_text: str,
        max_tokens: int,
        max_retries: int,
    ) -> tuple[str, dict]:
        # Flatten the structured system prompt to a plain string (the
        # subprocess can't carry cache_control breakpoints).
        flat_system = "\n\n".join(
            block.get("text", "") for block in system_prompt if isinstance(block, dict)
        )

        # Strip NULs — they make subprocess refuse to encode argv/stdin and
        # are never meaningful in our prompts. Cap user_text so we don't
        # blow past kernel limits on really pathological CSVs even via
        # stdin (Claude Code's own input cap is well under 1 MB).
        flat_system = flat_system.replace("\x00", "")
        user_text = user_text.replace("\x00", "")
        if len(user_text) > _MAX_PROMPT_CHARS:
            user_text = (
                user_text[: _MAX_PROMPT_CHARS // 2]
                + "\n\n[... snippet truncated to fit prompt budget ...]\n\n"
                + user_text[-(_MAX_PROMPT_CHARS // 2):]
            )

        # Pass user text via stdin instead of argv. Linux ARG_MAX (~128 KB)
        # caps total argv+envp; a 100 KB CSV snippet on `--print "<text>"`
        # raises ``OSError(7, 'Argument list too long')`` before the wrapper
        # spawns. With ``--print`` flag-only, Claude Code reads from stdin.
        argv = list(self._wrapper_argv) + [
            "--model", model,
            "--effort", self._effort,
            "--append-system-prompt", flat_system,
            "--print",
        ]

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                proc = subprocess.run(
                    argv,
                    input=user_text,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                last_exc = exc
                time.sleep(min(2 ** attempt, 30))
                continue
            if proc.returncode == 0:
                break
            last_exc = RuntimeError(
                f"sf-claude exit={proc.returncode}: {proc.stderr.strip()[:300]}"
            )
            time.sleep(min(2 ** attempt, 30))
        else:
            raise last_exc  # type: ignore[misc]

        raw_text = proc.stdout.strip()
        # Detect usage-policy refusals deterministically: Claude Code emits a
        # specific "API Error: ... violate our Usage Policy ..." string.
        # Retrying won't help — the prompt content is the trigger. Surface
        # this as a typed exception so the caller can skip silently.
        low = raw_text.lower()
        if "usage policy" in low or "violate our" in low and "policy" in low:
            raise PolicyRefusal(raw_text[:200])
        # No token counts available; ledger only sees call counts.
        usage = {
            "input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }
        return raw_text, usage


def build_backend(name: str | None = None, *, effort: str | None = None) -> _Backend:
    """Construct a backend by name (defaults to ``$SURVEY_LLM_BACKEND`` or auto).

    Auto-selection: prefer ``anthropic`` when ``ANTHROPIC_API_KEY`` is set,
    otherwise fall back to ``sf-claude`` when the wrapper is on PATH.
    ``effort`` is only consumed by the sf-claude backend.
    """
    chosen = name or os.environ.get("SURVEY_LLM_BACKEND") or "auto"
    if chosen == "auto":
        if os.environ.get("ANTHROPIC_API_KEY"):
            return AnthropicBackend()
        wrapper_head = shlex.split(
            os.environ.get("SURVEY_SF_CLAUDE_CMD", _DEFAULT_SF_CLAUDE_CMD)
        )[0]
        if shutil.which(wrapper_head):
            return SfClaudeBackend(effort=effort)
        raise RuntimeError(
            "no LLM backend available: set ANTHROPIC_API_KEY or install the "
            "'sf' CLI (or set SURVEY_SF_CLAUDE_CMD)."
        )
    if chosen == "anthropic":
        return AnthropicBackend()
    if chosen == "sf-claude":
        return SfClaudeBackend(effort=effort)
    raise ValueError(f"unknown LLM backend {chosen!r}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def call_triage(
    *,
    backend: _Backend,
    model: str,
    system_prompt: list[dict],
    user_text: str,
    out_dir: Path,
    budget_usd: float,
    max_tokens: int = 1500,
    max_retries: int = 3,
) -> TriageResult:
    """Send one triage prompt, parse the structured-output JSON, log cost.

    ``system_prompt`` is expected to be a list of content blocks with
    ``cache_control`` set on the *last* block — caller's responsibility.
    """
    raw_text, usage = backend.call(
        model=model,
        system_prompt=system_prompt,
        user_text=user_text,
        max_tokens=max_tokens,
        max_retries=max_retries,
    )

    parsed = _extract_json(raw_text)

    cost = float(usage.get("cost_usd") or 0.0)
    _record_cost(out_dir, model, cost, budget_usd)

    return TriageResult(
        parsed=parsed,
        model=model,
        backend=backend.name,
        cost_usd=cost,
        input_tokens=int(usage.get("input_tokens") or 0),
        cached_input_tokens=int(usage.get("cache_read_input_tokens") or 0),
        cache_creation_tokens=int(usage.get("cache_creation_input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of ``text``.

    Models sometimes wrap the answer in a code fence or add a brief
    preamble even when the prompt asks for raw JSON. We tolerate that.
    """
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json … ```
        stripped = text.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        text = stripped.strip()
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ValueError(f"No JSON object found in model response: {text[:200]!r}")
    return json.loads(text[first : last + 1])
