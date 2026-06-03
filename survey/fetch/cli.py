"""Top-level fetch CLI: ``python -m survey.fetch <backend> [opts]``.

Each backend module registers its own subparser via ``add_subparser`` and
brings in the shared flag surface through ``_backend.add_common_args``. The
adapter layer in ``config.from_args`` translates the parsed namespace back
into a typed ``FetchOptions`` (or per-backend variant) and dispatches into
the backend's ``run``.

The legacy ``survey/cli.py fetch --source <name>`` shim still works in
parallel via ``run_fetch`` in ``survey/fetch/__init__.py``.
"""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from . import BACKENDS
from ._log import set_level


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with one subcommand per registered backend."""
    parser = argparse.ArgumentParser(
        prog="survey.fetch",
        description=(
            "Download CSV datasets from public catalogs into a deduplicated "
            "manifest. One subcommand per supported backend."
        ),
    )
    sub = parser.add_subparsers(dest="backend", required=True)
    # Sort for stable --help ordering across Python versions / dict insertions.
    for name in sorted(BACKENDS):
        BACKENDS[name].add_subparser(sub)
    return parser


def _resolve_log_level(args: argparse.Namespace) -> int:
    """Map ``--quiet`` / ``--verbose`` flags to a stdlib logging level."""
    if getattr(args, "quiet", False):
        return logging.WARNING
    if getattr(args, "verbose", False):
        return logging.DEBUG
    return logging.INFO


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    set_level(_resolve_log_level(args))
    backend = BACKENDS[args.backend]
    return backend.run(backend.options_from_args(args))
