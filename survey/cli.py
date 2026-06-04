"""Survey CLI dispatcher.

Currently exposes a single ``fetch`` subcommand that shims into
``survey.fetch.run_fetch``::

    python -m survey fetch --source data.gov --max-files 2500

The full-featured fetch CLI (per-backend flags, dry-run, concurrency, etc.)
lives at ``python -m survey.fetch <backend>``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config
from ._units import human_bytes as _human_bytes


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--out-dir",
        type=Path,
        default=config.DEFAULT_OUT_DIR,
        help="Survey output root (default: survey/out).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=config.RAND_SEED,
        help="Random seed for sampling and shuffling.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="survey",
        description="Pollock CSV-pollution survey pipeline.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # fetch ----------------------------------------------------------------
    p_fetch = sub.add_parser("fetch", help="Assemble a corpus.")
    p_fetch.add_argument(
        "--source",
        required=True,
        choices=["data.gov", "data.gov.uk", "hf", "kaggle", "inside_airbnb", "data.europa.eu"],
    )
    p_fetch.add_argument("--max-files", type=int, default=None)
    p_fetch.add_argument(
        "--max-bytes", type=_human_bytes, default=config.DEFAULT_MAX_BYTES
    )
    p_fetch.add_argument(
        "--datagov-query",
        default="csv",
        help="Search query passed to catalog.data.gov (default: 'csv').",
    )
    p_fetch.add_argument("--dry-run", action="store_true")
    _add_common(p_fetch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "fetch":
        from .fetch import run_fetch

        return run_fetch(args)

    parser.error(f"unknown subcommand: {args.cmd}")
    return 2
