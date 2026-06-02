"""Tier 4 — gold-set scoring and report generation."""

from __future__ import annotations


def run_score(args) -> int:
    from .scorer import run_score as _run

    return _run(args)


def run_report(args) -> int:
    from .reports import run_report as _run

    return _run(args)
