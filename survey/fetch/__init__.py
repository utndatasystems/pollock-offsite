"""Tier 0 — corpus assembly.

``run_fetch`` dispatches on ``args.source`` (data.gov / data.gov.uk /
HF / Kaggle) or falls back to ``args.source_dir`` (local-only mode).
Backends live in sibling modules and produce ``manifest.csv`` rows.

Phase 4 adds the ``BACKENDS`` registry and the typed-config / download / Backend
re-exports. The legacy ``run_fetch(args)`` shim is preserved verbatim — the
legacy ``survey/cli.py`` still drives it. Phase 5 will rewrite ``run_fetch`` to
dispatch via ``BACKENDS``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from .config import (
    BackendOptions,
    CkanOptions,
    DataEuropaEuOptions,
    DataGovOptions,
    FetchOptions,
    from_args,
)
from .manifest import MANIFEST_FIELDS, ManifestRow, manifest_path

if TYPE_CHECKING:
    from ._backend import Backend

__all__ = (
    "BACKENDS",
    "CkanOptions",
    "DataEuropaEuOptions",
    "DataGovOptions",
    "FetchOptions",
    "MANIFEST_FIELDS",
    "ManifestRow",
    "manifest_path",
    "run_fetch",
)


@dataclass
class _LegacyBackend:
    """Phase-4 placeholder satisfying the ``Backend`` Protocol.

    Wraps the not-yet-rewritten ``run_<backend>(args)`` entry points so the
    registry exposes the three full backends today. Phase 5 swaps these out
    for first-class backend modules.
    """

    name: str
    _run: Callable[[argparse.Namespace], int]
    _args_factory: Callable[[argparse.Namespace], BackendOptions] = field(
        default=lambda a: from_args(a, "data.gov")  # overridden per-backend
    )

    def add_subparser(
        self, sp: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:  # pragma: no cover - Phase 7 owns the real CLI
        return sp.add_parser(self.name, help=f"{self.name} fetch backend")

    def options_from_args(self, args: argparse.Namespace) -> BackendOptions:
        return self._args_factory(args)

    def run(self, opts: Any) -> int:
        # Phase 4 keeps the legacy argparse entry. Phase 5 will rewrite each
        # backend to take its typed Options dataclass directly.
        if isinstance(opts, argparse.Namespace):
            return self._run(opts)
        raise TypeError(
            f"{self.name}: legacy adapter expects argparse.Namespace until Phase 5"
        )


def _build_registry() -> dict[str, "Backend"]:
    """Register every backend module known to Phase 4.

    Full backends are wrapped via ``_LegacyBackend`` so the registry exposes
    them before the Phase 5 rewrite. Deferred backends (``inside_airbnb``,
    ``hf``, ``kaggle``) are skipped — Phase 6 stubs them.
    """
    registry: dict[str, "Backend"] = {}
    from .ckan import run_ckan
    from .data_europa_eu import run_data_europa_eu
    from .datagov import run_datagov

    registry["data.gov"] = _LegacyBackend(
        name="data.gov",
        _run=run_datagov,
        _args_factory=lambda a: from_args(a, "data.gov"),
    )
    registry["data.gov.uk"] = _LegacyBackend(
        name="data.gov.uk",
        _run=run_ckan,
        _args_factory=lambda a: from_args(a, "data.gov.uk"),
    )
    registry["data.europa.eu"] = _LegacyBackend(
        name="data.europa.eu",
        _run=run_data_europa_eu,
        _args_factory=lambda a: from_args(a, "data.europa.eu"),
    )
    return registry


BACKENDS: dict[str, "Backend"] = _build_registry()


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
