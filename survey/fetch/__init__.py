"""Tier 0 -- corpus assembly.

``BACKENDS`` is the registry of fetch backends; each value is a module that
satisfies the ``Backend`` Protocol (``name``, ``add_subparser``,
``options_from_args``, ``run``).

The public ``run_fetch(args)`` shim is what ``survey/cli.py fetch --source X``
dispatches into: it looks up the backend by name, builds the right typed
options via the backend's ``options_from_args``, and calls ``run``. The
fetch-only CLI (``python -m survey.fetch``) uses the same registry directly.
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
    """Register every backend module.

    The three full backends (``data.gov``, ``data.gov.uk``, ``data.europa.eu``)
    do real work; ``inside_airbnb`` / ``hf`` / ``kaggle`` are stubs that exit
    ``2`` with a "not yet supported in v1" message. Keeping the stubs
    registered means they show up in ``--help`` and route through the same
    ``run_fetch`` shim as the full backends.
    """
    from . import ckan, data_europa_eu, datagov, hf, inside_airbnb, kaggle

    return {
        datagov.name: datagov,
        ckan.name: ckan,
        data_europa_eu.name: data_europa_eu,
        inside_airbnb.name: inside_airbnb,
        hf.name: hf,
        kaggle.name: kaggle,
    }


BACKENDS: "dict[str, Backend]" = _build_registry()


def run_fetch(args) -> int:
    """Dispatch ``survey/cli.py fetch --source X`` to the matching backend.

    Reads ``args.source``, looks up the backend module in ``BACKENDS``, builds
    its typed options via the module's ``options_from_args``, and calls
    ``run``.
    """
    source = getattr(args, "source", None)
    if source in BACKENDS:
        backend = BACKENDS[source]
        return backend.run(backend.options_from_args(args))

    raise NotImplementedError(f"fetch source {source!r} not implemented yet")
