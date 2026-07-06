"""Factory for deferred-backend stub modules.

Each deferred backend (``inside_airbnb``, ``hf``, ``kaggle``) used to live in
its own module that did nothing but log a warning and exit ``2``. The factory
collapses them into one source of truth — the registry constructs three
stubs at import time and registers them by name.
"""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from ._backend import add_common_args
from ._log import get_logger
from .config import FetchOptions, from_args


def make_stub(backend_name: str, help_text: str) -> SimpleNamespace:
    """Return an object satisfying the ``Backend`` Protocol.

    The object's ``run`` logs a deferred-feature warning and returns ``2``.
    ``add_subparser`` registers a subcommand with the shared flag surface so
    ``--help`` still lists it.
    """
    logger = get_logger(backend_name)

    def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
        p = sp.add_parser(backend_name, help=help_text)
        add_common_args(p)
        return p

    def options_from_args(args: argparse.Namespace) -> FetchOptions:
        return from_args(args, backend_name)  # type: ignore[return-value]

    def run(opts: FetchOptions) -> int:
        logger.warning(
            f"{backend_name} backend is not yet supported in v1; "
            "see survey/fetch/README.md#roadmap"
        )
        return 2

    return SimpleNamespace(
        name=backend_name,
        add_subparser=add_subparser,
        options_from_args=options_from_args,
        run=run,
    )
