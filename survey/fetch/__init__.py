"""Tier 0 — corpus assembly.

``run_fetch`` dispatches on ``args.source`` (data.gov / data.gov.uk /
HF / Kaggle) or falls back to ``args.source_dir`` (local-only mode).
Backends live in sibling modules and produce ``manifest.csv`` rows.
"""

from __future__ import annotations


def run_fetch(args) -> int:
    if args.source_dir is not None:
        from .local import run_local

        return run_local(args)

    if args.source == "data.gov":
        from .datagov import run_datagov

        return run_datagov(args)

    if args.source == "data.gov.uk":
        from .ckan import run_ckan

        return run_ckan(args)

    if args.source in ("hf", "kaggle"):
        from .hf_kaggle import run_hf_kaggle

        return run_hf_kaggle(args)

    if args.source == "inside_airbnb":
        from .inside_airbnb import run_inside_airbnb

        return run_inside_airbnb(args)

    if args.source == "data.europa.eu":
        from .data_europa_eu import run_data_europa_eu

        return run_data_europa_eu(args)

    raise NotImplementedError(f"fetch source {args.source!r} not implemented yet")
