"""Ambiguity-score computation for Tier 1 → Tier 2 routing.

Given a Tier 1 ``_parameters.json`` record, returns a float in [0, 1]
representing how much the deterministic detectors disagreed or
under-determined the answer. The Tier 2 triage runs only on files
exceeding ``DEFAULT_AMBIGUITY_THRESHOLD`` (0.30 — see ``survey/config.py``).

The formula (see plan §Tier 2):

    score = 0.25 * sniffer_low_confidence
          + 0.25 * ambiguous_delimiter
          + 0.20 * (jagged_rows_count > 0 AND header_lines > 0)
          + 0.15 * table_multiple_tables
          + 0.15 * (min(confidences.values()) < 0.6)

Capped at 1.0.
"""

from __future__ import annotations


def compute(record: dict) -> float:
    annotations = record.get("annotations") or {}
    confidences = record.get("confidences") or {}

    score = 0.0
    if annotations.get("sniffer_low_confidence"):
        score += 0.25
    if annotations.get("ambiguous_delimiter"):
        score += 0.25
    if (
        int(annotations.get("jagged_rows_count") or 0) > 0
        and not annotations.get("table_no_header", True)
    ):
        score += 0.20
    if annotations.get("table_multiple_tables"):
        score += 0.15
    if confidences and min(confidences.values()) < 0.6:
        score += 0.15
    return min(round(score, 3), 1.0)
