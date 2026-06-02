"""Tier 2 triage driver.

Iterates ``<out-dir>/parameters/*_parameters.json``, finds files whose
``ambiguity_score >= --threshold``, sends each to the LLM along with a
small head/tail snippet of the source CSV, and writes the parsed output
to ``<out-dir>/triage/<file>.csv_triage.json``.

Default model is ``claude-haiku-4-5``; we escalate to
``claude-sonnet-4-6`` once when the model self-reports
``model_confidence < 0.6`` or when JSON parsing fails on the first try.

System prompt is built once and prompt-cached on the *last* block so the
taxonomy + schema (which never change between requests) cost the
~1.25× write premium once and ~0.1× per cached read after that.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sut.utils import print as ts_print
from tqdm import tqdm

from ..config import (
    ALL_ANNOTATION_FIELDS,
    DEFAULT_TRIAGE_ESCALATION_MODEL,
    NEW_CANDIDATE_FLAGS,
    POLLOCK_ORIGINAL_FLAGS,
    SCALAR_ANNOTATION_FIELDS,
)
from ..detect import io_utils
from . import ambiguity, llm_client


_SAMPLE_HEAD = 80
_SAMPLE_TAIL = 30
_LOW_CONFIDENCE = 0.6


def _build_system_prompt() -> list[dict]:
    """Stable taxonomy + JSON-schema instructions; cached on the last block."""
    schema_props = {f: {"type": "boolean"} for f in POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS}
    schema_props["jagged_rows_count"] = {"type": "integer", "minimum": 0}
    schema_props["dimension"] = {"type": "string"}
    schema_props["encoding_flag"] = {"type": "string"}
    schema_props["model_confidence"] = {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": "How confident you are in the flag values (0.0=guess, 1.0=certain).",
    }
    schema_props["comments"] = {
        "type": "string",
        "description": "Brief free-text note on anything unusual in this file.",
    }

    schema = {
        "type": "object",
        "properties": schema_props,
        "required": list(ALL_ANNOTATION_FIELDS) + ["model_confidence"],
        "additionalProperties": False,
    }

    intro = (
        "You are a CSV-pollution annotator. You will receive (a) a head/tail "
        "snippet of one CSV file and (b) the deterministic Tier 1 detector "
        "output for that file. Your job is to refine the boolean flag values "
        "and report a single JSON object that conforms to the schema below.\n\n"
        "The flag definitions match the Pollock paper "
        "(https://www.vldb.org/pvldb/vol16/p1870-vitagliano.pdf) survey, "
        "extended with research-backed candidates from Pytheas, Hypoparsr, "
        "CleverCSV, Muppets, SchemaPile, and SemTab.\n\n"
        "Rules:\n"
        "1. Reply with a single JSON object — no preamble, no code fences.\n"
        "2. Every flag in the schema MUST be present.\n"
        "3. ``model_confidence`` reflects YOUR overall confidence (0.0..1.0). "
        "If you can't determine a value, set the flag to its most plausible "
        "boolean and lower your confidence.\n"
        "4. ``comments`` is one short sentence — note anything weird the "
        "flag list doesn't cover (no more than 200 chars).\n"
        "5. Treat sampled-text artefacts (the literal token ``<SAMPLE_GAP>``) "
        "as a marker, not as content.\n"
    )

    flag_glossary = "\n".join(
        f"  - {flag}" for flag in POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS + SCALAR_ANNOTATION_FIELDS
    )

    return [
        {
            "type": "text",
            "text": intro + "\nFlag list:\n" + flag_glossary,
        },
        {
            "type": "text",
            "text": "JSON schema:\n" + json.dumps(schema, indent=2),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _build_user_text(record: dict, csv_text: str) -> str:
    annotations = record.get("annotations") or {}
    confidences = record.get("confidences") or {}
    return (
        "Tier 1 detector output (deterministic — may be wrong on ambiguous files):\n"
        + json.dumps(
            {
                "annotations": annotations,
                "confidences": confidences,
                "ambiguity_score": record.get("ambiguity_score"),
                "delimiter": record.get("delimiter"),
                "quotechar": record.get("quotechar"),
                "encoding": record.get("encoding"),
                "row_delimiter": record.get("row_delimiter"),
                "header_lines": record.get("header_lines"),
                "preamble_lines": record.get("preamble_lines"),
                "n_columns": record.get("n_columns"),
                "column_names": record.get("column_names"),
            },
            indent=2,
        )
        + "\n\nCSV head/tail snippet (head "
        + str(_SAMPLE_HEAD)
        + " + tail "
        + str(_SAMPLE_TAIL)
        + " lines):\n"
        + csv_text
    )


def _read_head_tail(path: Path, encoding: str) -> str:
    """Decode head/tail of ``path`` for the LLM prompt.

    Reads up to ``_SAMPLE_HEAD`` lines from the start and ``_SAMPLE_TAIL``
    from the end. For ``.zstd`` files this still works because
    ``io_utils`` handles decompression transparently.
    """
    try:
        head_bytes = io_utils.read_head_bytes(path, 1 << 20)
    except FileNotFoundError:
        return "<source file not found at the path the manifest points to>"

    enc = encoding or "utf-8"
    try:
        head_text = head_bytes.decode(enc, errors="replace")
    except LookupError:
        head_text = head_bytes.decode("latin-1", errors="replace")

    head_lines = head_text.splitlines()[: _SAMPLE_HEAD]

    # Best-effort tail: read the whole decompressed content and keep last N
    # lines. Capped at 8 MB to avoid pathological inputs.
    full_bytes = io_utils.read_all_bytes(path, cap=8 * 1024 * 1024)
    try:
        full_text = full_bytes.decode(enc, errors="replace")
    except LookupError:
        full_text = full_bytes.decode("latin-1", errors="replace")
    tail_lines = full_text.splitlines()[-_SAMPLE_TAIL:]

    return "\n".join(head_lines) + "\n# <SAMPLE_GAP> #\n" + "\n".join(tail_lines)


def _resolve_source_path(record: dict) -> Path | None:
    src = (record.get("source_meta") or {}).get("url") or ""
    if src.startswith("file://"):
        return Path(src[len("file://"):])
    # The fetch backends save under <out-dir>/raw/<sha[:2]>/<sha>.csv;
    # the local_path field on the manifest is canonical.
    local = (record.get("source_meta") or {}).get("local_path")
    if local:
        return Path(local)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_triage(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    params_dir = out_dir / "parameters"
    triage_dir = out_dir / "triage"
    triage_dir.mkdir(parents=True, exist_ok=True)

    if not params_dir.is_dir():
        ts_print(f"[triage] no parameters directory at {params_dir}")
        return 1

    # rglob: tier1 outputs may be nested when input data is itself nested
    # (e.g. inside_airbnb mirrors country/region/city/date).
    candidates = sorted(params_dir.rglob("*_parameters.json"))
    show_progress = bool(getattr(args, "progress", True))
    if not candidates:
        ts_print(f"[triage] no Tier 1 outputs under {params_dir}")
        return 0

    threshold = float(args.threshold)
    primary_model = args.model
    escalation_model = getattr(args, "escalation_model", None) or DEFAULT_TRIAGE_ESCALATION_MODEL
    budget_usd = float(args.budget_usd)

    try:
        backend = llm_client.build_backend(
            getattr(args, "backend", None),
            effort=getattr(args, "effort", None),
        )
    except (RuntimeError, ValueError) as exc:
        ts_print(f"[triage] {exc}")
        return 1
    ts_print(
        f"[triage] backend={backend.name}, primary={primary_model}, "
        f"escalation={escalation_model}"
    )

    system_prompt = _build_system_prompt()
    n_seen = n_triaged = n_escalated = n_failed = 0
    t0 = time.time()

    pbar = tqdm(
        candidates,
        desc="[triage]",
        unit="file",
        disable=not show_progress,
    )
    for params_path in pbar:
        rel = params_path.relative_to(params_dir)
        try:
            with open(params_path) as f:
                record = json.load(f)
        except Exception as exc:
            tqdm.write(f"[triage] cannot read {rel}: {exc!r}")
            continue
        n_seen += 1

        score = ambiguity.compute(record)
        if score < threshold:
            continue

        # Mirror the params subtree under triage/ so foo/bar/listings.csv_parameters.json
        # → triage/foo/bar/listings.csv_triage.json (no cross-dir basename collisions).
        out_path = triage_dir / rel.with_name(
            rel.name.replace("_parameters.json", "_triage.json")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not getattr(args, "force", False):
            continue

        source_path = _resolve_source_path(record)
        if source_path is None or not source_path.exists():
            tqdm.write(f"[triage] source missing for {rel}; skipping")
            continue

        encoding = record.get("encoding") or "utf-8"
        csv_text = _read_head_tail(source_path, encoding)
        user_text = _build_user_text(record, csv_text)

        # First attempt: Haiku.
        result = None
        try:
            result = llm_client.call_triage(
                backend=backend,
                model=primary_model,
                system_prompt=system_prompt,
                user_text=user_text,
                out_dir=out_dir,
                budget_usd=budget_usd,
            )
        except llm_client.BudgetExceeded as exc:
            tqdm.write(f"[triage] {exc}; stopping")
            break
        except llm_client.PolicyRefusal as exc:
            # Don't escalate — refusal is deterministic on prompt content.
            tqdm.write(f"[triage] policy-refused {rel}; skipping")
            n_failed += 1
            continue
        except Exception as exc:  # noqa: BLE001
            tqdm.write(f"[triage] primary call failed for {rel}: {exc!r}")
            n_failed += 1

        # Escalation: Sonnet, if model self-reports low confidence or first
        # attempt failed outright.
        escalated = False
        if (
            result is not None
            and float(result.parsed.get("model_confidence", 0.0)) < _LOW_CONFIDENCE
        ) or result is None:
            try:
                result = llm_client.call_triage(
                    backend=backend,
                    model=escalation_model,
                    system_prompt=system_prompt,
                    user_text=user_text,
                    out_dir=out_dir,
                    budget_usd=budget_usd,
                )
                escalated = True
                n_escalated += 1
            except llm_client.BudgetExceeded as exc:
                tqdm.write(f"[triage] {exc}; stopping")
                break
            except llm_client.PolicyRefusal:
                tqdm.write(f"[triage] policy-refused (escalation) {rel}; skipping")
                if result is None:
                    continue
            except Exception as exc:  # noqa: BLE001
                tqdm.write(f"[triage] escalation failed for {rel}: {exc!r}")
                if result is None:
                    continue  # nothing to write

        # Persist the result.
        out_record = {
            "source_filename": str(rel).replace("_parameters.json", ""),
            "ambiguity_score": score,
            "tier1_annotations": record.get("annotations"),
            "tier2": result.parsed,
            "tier2_meta": {
                "model": result.model,
                "escalated": escalated,
                "cost_usd": result.cost_usd,
                "input_tokens": result.input_tokens,
                "cached_input_tokens": result.cached_input_tokens,
                "cache_creation_tokens": result.cache_creation_tokens,
                "output_tokens": result.output_tokens,
                "ran_at": _now_iso(),
            },
        }
        with open(out_path, "w") as f:
            json.dump(out_record, f, sort_keys=True, indent=2)
        n_triaged += 1
        ledger_now = llm_client._load_ledger(out_dir)
        pbar.set_postfix(
            triaged=n_triaged,
            esc=n_escalated,
            fail=n_failed,
            usd=f"{ledger_now['total_usd']:.2f}",
        )

    pbar.close()
    elapsed = time.time() - t0
    ledger = llm_client._load_ledger(out_dir)
    ts_print(
        f"[triage] done: seen={n_seen}, triaged={n_triaged}, escalated={n_escalated}, "
        f"failed={n_failed}, elapsed={elapsed:.1f}s, "
        f"total_usd=${ledger['total_usd']:.4f}, n_calls={ledger['n_calls']}"
    )
    return 0
