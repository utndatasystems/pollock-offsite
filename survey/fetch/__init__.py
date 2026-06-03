"""Tier 0 -- corpus assembly.

``BACKENDS`` is the registry of fetch backends; each value is a module that
satisfies the ``Backend`` Protocol (``name``, ``add_subparser``,
``options_from_args``, ``run``). Phase 5 dropped the ``_LegacyBackend`` adapter
in favour of registering the modules directly.

The public ``run_fetch(args)`` shim keeps the legacy ``survey/cli.py`` entry
point working: it dispatches on ``args.source``, builds the right typed
options via the backend's ``options_from_args``, and calls ``run``. The Phase
7 fetch-only CLI (``python -m survey.fetch``) will use the same registry but
bypass this shim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def _build_registry() -> "dict[str, Backend]":
    """Register the three full backend modules.

    Phase 6 will add the deferred backends (``inside_airbnb``, ``hf``,
    ``kaggle``) as stubs.
    """
    from . import ckan, data_europa_eu, datagov

    return {
        datagov.name: datagov,
        ckan.name: ckan,
        data_europa_eu.name: data_europa_eu,
    }


BACKENDS: "dict[str, Backend]" = _build_registry()


def run_fetch(args) -> int:
    """Backwards-compat shim driven by the legacy ``survey/cli.py``.

    Reads ``args.source``, looks up the backend module in ``BACKENDS``, builds
    its typed options via the module's ``options_from_args``, and calls
    ``run``. The deferred backends (``inside_airbnb``, ``hf``, ``kaggle``) and
    the ``--source-dir`` local mode still resolve through their existing
    code paths until Phases 6 and 7 land.
    """
    if getattr(args, "source_dir", None) is not None:
        from .local import run_local

        return run_local(args)

    source = getattr(args, "source", None)
    if source in BACKENDS:
        backend = BACKENDS[source]
        return backend.run(backend.options_from_args(args))

    if source in ("hf", "kaggle"):
        from .hf_kaggle import run_hf_kaggle

        return run_hf_kaggle(args)

    if source == "inside_airbnb":
        from .inside_airbnb import run_inside_airbnb

        return run_inside_airbnb(args)

    raise NotImplementedError(f"fetch source {source!r} not implemented yet")
