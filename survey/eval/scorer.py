"""Tier 4 scorer.

Reads gold annotations + Tier 1 outputs (+ Tier 2 outputs when present)
and writes per-flag precision / recall / F1 tables to
``<out-dir>/reports/``.

CSV outputs:

- ``tier1_vs_gold.csv``     — rows: flags, cols: P/R/F1/support, plus
                              header_lines / preamble_lines / encoding /
                              delimiter agreement counts.
- ``tier2_vs_gold.csv``     — same shape, restricted to gold ∩ triaged.
- ``dialect_agreement.csv`` — encoding / delimiter / quotechar / row_delimiter
                              raw agreement % over the gold set.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sut.utils import print as ts_print

from ..config import (
    NEW_CANDIDATE_FLAGS,
    POLLOCK_ORIGINAL_FLAGS,
)
from . import gold as gold_mod


_BOOLEAN_FLAGS = POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS
_DIALECT_FIELDS = ("encoding", "delimiter", "quotechar", "row_delimiter", "escapechar")


def _binary_metrics(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return round(precision, 3), round(recall, 3), round(f1, 3)


def _score_per_flag(
    pred: dict[str, dict], gold: dict[str, dict]
) -> list[dict]:
    """Per-boolean-flag P/R/F1 across files in ``gold`` ∩ ``pred``."""
    rows: list[dict] = []
    for flag in _BOOLEAN_FLAGS:
        tp = fp = fn = tn = 0
        support = 0
        for name, gold_rec in gold.items():
            pred_rec = pred.get(name)
            if pred_rec is None:
                continue
            support += 1
            g_val = bool(((gold_rec.get("annotations") or {}).get(flag)))
            p_val = bool(((pred_rec.get("annotations") or {}).get(flag)))
            if g_val and p_val:
                tp += 1
            elif p_val and not g_val:
                fp += 1
            elif g_val and not p_val:
                fn += 1
            else:
                tn += 1
        precision, recall, f1 = _binary_metrics(tp, fp, fn)
        rows.append(
            {
                "flag": flag,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return rows


def _dialect_agreement(
    pred: dict[str, dict], gold: dict[str, dict]
) -> list[dict]:
    rows: list[dict] = []
    for field in _DIALECT_FIELDS:
        match = total = 0
        mismatches: list[tuple[str, object, object]] = []
        for name, gold_rec in gold.items():
            pred_rec = pred.get(name)
            if pred_rec is None:
                continue
            total += 1
            g = gold_rec.get(field)
            p = pred_rec.get(field)
            if g == p:
                match += 1
            elif len(mismatches) < 3:
                mismatches.append((name, g, p))
        rows.append(
            {
                "field": field,
                "match": match,
                "total": total,
                "agreement_pct": round(100 * match / total, 1) if total else 0.0,
                "first_mismatches": "; ".join(
                    f"{n}: gold={g!r} pred={p!r}" for n, g, p in mismatches
                ),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _load_tier1(out_dir: Path) -> dict[str, dict]:
    params_dir = out_dir / "parameters"
    if not params_dir.is_dir():
        return {}
    out: dict[str, dict] = {}
    # rglob: tier1 outputs may be nested (e.g. inside_airbnb mirrors its
    # country/region/city/date subtree). Key by relative path so two
    # ``listings.csv_parameters.json`` from different cities don't collide.
    for path in sorted(params_dir.rglob("*_parameters.json")):
        try:
            with open(path) as f:
                out[str(path.relative_to(params_dir))] = json.load(f)
        except Exception:
            continue
    return out


def _load_tier2(out_dir: Path) -> dict[str, dict]:
    """Convert ``triage/<sha>.csv_triage.json`` records into the same
    ``annotations``-keyed shape used by Tier 1, so the scorer doesn't
    need a special branch.
    """
    triage_dir = out_dir / "triage"
    if not triage_dir.is_dir():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(triage_dir.rglob("*_triage.json")):
        try:
            with open(path) as f:
                rec = json.load(f)
        except Exception:
            continue
        rel = str(path.relative_to(triage_dir))
        params_key = rel.replace("_triage.json", "_parameters.json")
        out[params_key] = {"annotations": rec.get("tier2") or {}}
        # Carry through the dialect fields from the embedded tier1 record so
        # _dialect_agreement still works.
        for field in _DIALECT_FIELDS:
            v = (rec.get("tier1_annotations") or {}).get(field)
            if v is not None:
                out[params_key][field] = v
    return out


def run_score(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    gold_dir: Path = Path(args.gold_dir).resolve()
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    gold = gold_mod.load_gold(gold_dir)
    if not gold:
        ts_print(f"[score] no gold annotations under {gold_dir}; nothing to do")
        return 1

    tier1 = _load_tier1(out_dir)
    tier2 = _load_tier2(out_dir)

    flag_fields = ["flag", "tp", "fp", "fn", "tn", "support", "precision", "recall", "f1"]
    dialect_fields = ["field", "match", "total", "agreement_pct", "first_mismatches"]

    tier1_rows = _score_per_flag(tier1, gold)
    _write_csv(reports_dir / "tier1_vs_gold.csv", tier1_rows, flag_fields)

    if tier2:
        tier2_rows = _score_per_flag(tier2, gold)
        _write_csv(reports_dir / "tier2_vs_gold.csv", tier2_rows, flag_fields)

    dialect_rows = _dialect_agreement(tier1, gold)
    _write_csv(reports_dir / "dialect_agreement.csv", dialect_rows, dialect_fields)

    n_overlap_t1 = sum(1 for n in gold if n in tier1)
    n_overlap_t2 = sum(1 for n in gold if n in tier2)
    ts_print(
        f"[score] gold={len(gold)}, tier1∩gold={n_overlap_t1}, "
        f"tier2∩gold={n_overlap_t2} → reports written to {reports_dir}"
    )
    return 0
