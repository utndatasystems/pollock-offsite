"""Inside Airbnb fetch backend (stubbed).

Full Inside Airbnb support is deferred past v1; the stub keeps the backend
discoverable in ``--help`` and exits cleanly with code ``2`` and a pointer to
the roadmap. Implementation history lives in git (see prior commits before the
Phase 6 stub-out).
"""

from __future__ import annotations

import argparse

from ._backend import add_common_args
from ._log import get_logger
from .config import FetchOptions, from_args

logger = get_logger("inside_airbnb")


name = "inside_airbnb"


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register the ``inside_airbnb`` subparser (stub; common flags only)."""
    p = sp.add_parser(name, help="Inside Airbnb (deferred; not yet supported in v1).")
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> FetchOptions:
    return from_args(args, name)


def run(opts: FetchOptions) -> int:
    logger.warning(
        "inside_airbnb backend is not yet supported in v1; "
        "see survey/fetch/README.md#roadmap"
    )
    return 2
