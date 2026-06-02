"""Tier 2 / Tier 3 — LLM-assisted triage and discovery."""

from __future__ import annotations


def run_triage(args) -> int:
    from .triage_prompt import run_triage as _run

    return _run(args)


def run_discover(args) -> int:
    from .discover_prompt import run_discover as _run

    return _run(args)
