"""Hugging Face Hub fetch backend (stubbed).

Full Hugging Face support is deferred past v1; the planned implementation will
use the ``huggingface_hub`` Python package directly. Until then the stub keeps
the backend discoverable in ``--help`` and exits cleanly with code ``2`` and a
pointer to the roadmap.
"""

from __future__ import annotations

import argparse

from ._backend import add_common_args
from ._log import get_logger
from .config import FetchOptions, from_args

logger = get_logger("hf")


name = "hf"


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register the ``hf`` subparser (stub; common flags only)."""
    p = sp.add_parser(name, help="Hugging Face Hub (deferred; not yet supported in v1).")
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> FetchOptions:
    return from_args(args, name)


def run(opts: FetchOptions) -> int:
    logger.warning(
        "hf backend is not yet supported in v1; "
        "see survey/fetch/README.md#roadmap"
    )
    return 2
