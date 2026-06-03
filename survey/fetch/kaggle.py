"""Kaggle fetch backend (stubbed).

Full Kaggle support is deferred past v1; the planned implementation will use
the ``kaggle`` Python package (with API-token auth) directly. Until then the
stub keeps the backend discoverable in ``--help`` and exits cleanly with code
``2`` and a pointer to the roadmap.
"""

from __future__ import annotations

import argparse

from ._backend import add_common_args
from ._log import get_logger
from .config import FetchOptions, from_args

logger = get_logger("kaggle")


name = "kaggle"


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register the ``kaggle`` subparser (stub; common flags only)."""
    p = sp.add_parser(name, help="Kaggle (deferred; not yet supported in v1).")
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> FetchOptions:
    return from_args(args, name)


def run(opts: FetchOptions) -> int:
    logger.warning(
        "kaggle backend is not yet supported in v1; "
        "see survey/fetch/README.md#roadmap"
    )
    return 2
