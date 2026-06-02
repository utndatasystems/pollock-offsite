"""Tier 1 — deterministic detectors.

``run_annotate`` walks an input directory, runs the per-file detector
ensemble, and writes one ``<file>_parameters.json`` per CSV. Implementation
lives in ``runner.py`` and the per-flag detector modules.
"""

from __future__ import annotations


def run_annotate(args) -> int:
    from .runner import run_annotate as _run

    return _run(args)
