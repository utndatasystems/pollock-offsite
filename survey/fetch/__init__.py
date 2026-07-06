"""Tier 0 -- corpus assembly.

``BACKENDS`` is the registry of fetch backends; each value satisfies the
``Backend`` Protocol (``name``, ``add_subparser``, ``options_from_args``,
``run``). Real backends are modules; deferred backends are
``SimpleNamespace`` instances built by ``_stub.make_stub`` so the same
Protocol applies uniformly.

The fetch CLI (``python -m survey.fetch <backend>``) iterates this registry
to wire up subparsers and dispatches the parsed namespace into the matched
backend's ``run``.
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
)


def _build_registry() -> "dict[str, Backend]":
    """Register every backend.

    The three full backends (``data.gov``, ``data.gov.uk``, ``data.europa.eu``)
    do real work; ``inside_airbnb`` / ``hf`` / ``kaggle`` are factory-built
    stubs that exit ``2`` with a "not yet supported in v1" message. Keeping
    the stubs registered means they still show up in ``--help``.
    """
    from . import ckan, data_europa_eu, datagov
    from ._stub import make_stub

    return {
        datagov.name: datagov,
        ckan.name: ckan,
        data_europa_eu.name: data_europa_eu,
        "inside_airbnb": make_stub(
            "inside_airbnb", "Inside Airbnb (deferred; not yet supported in v1)."
        ),
        "hf": make_stub(
            "hf", "Hugging Face Hub (deferred; not yet supported in v1)."
        ),
        "kaggle": make_stub(
            "kaggle", "Kaggle (deferred; not yet supported in v1)."
        ),
    }


BACKENDS: "dict[str, Backend]" = _build_registry()
