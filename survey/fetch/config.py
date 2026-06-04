"""Typed configuration for fetch backends.

``FetchOptions`` is the shared, immutable shape every backend takes; per-backend
options compose it via a ``base`` field rather than inheriting (frozen-dataclass
inheritance is awkward and surprises type checkers).

``from_args`` adapts an argparse namespace to the right per-backend dataclass.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union


@dataclass(frozen=True)
class FetchOptions:
    """Shared, immutable knobs every fetch backend reads."""

    out_dir: Path
    data_root: Path
    max_files: int | None
    max_bytes: int
    dry_run: bool
    concurrency: int = 8
    per_file_cap_bytes: int = 200 * 1024 * 1024
    head_timeout_s: int = 5
    request_timeout_s: int = 60
    user_agent: str | None = None
    log_level: str = "INFO"
    compress: Literal["none", "gzip", "zstd"] = "none"


@dataclass(frozen=True)
class DataGovOptions:
    """Options for the catalog.data.gov backend; ``query`` is the search term."""

    base: FetchOptions
    query: str = "csv"


@dataclass(frozen=True)
class CkanOptions:
    """Options for any CKAN-shaped catalog (``data.gov.uk`` and friends)."""

    base: FetchOptions
    source: str = "data.gov.uk"
    endpoint: str | None = None


@dataclass(frozen=True)
class DataEuropaEuOptions:
    """Options for the data.europa.eu hub backend."""

    base: FetchOptions


BackendOptions = Union[FetchOptions, DataGovOptions, CkanOptions, DataEuropaEuOptions]


def _base_from_args(args: argparse.Namespace) -> FetchOptions:
    out_dir: Path = getattr(args, "out_dir")
    data_root_attr = getattr(args, "data_root", None)
    data_root: Path = Path(data_root_attr) if data_root_attr else out_dir / "raw"
    return FetchOptions(
        out_dir=out_dir,
        data_root=data_root,
        max_files=getattr(args, "max_files", None),
        max_bytes=getattr(args, "max_bytes"),
        dry_run=bool(getattr(args, "dry_run", False)),
        concurrency=int(getattr(args, "concurrency", 8) or 8),
        per_file_cap_bytes=int(
            getattr(args, "per_file_cap_bytes", 200 * 1024 * 1024)
            or 200 * 1024 * 1024
        ),
        head_timeout_s=int(getattr(args, "head_timeout_s", 5) or 5),
        request_timeout_s=int(getattr(args, "request_timeout_s", 60) or 60),
        user_agent=getattr(args, "user_agent", None),
        log_level=getattr(args, "log_level", "INFO") or "INFO",
        compress=getattr(args, "compress", "none") or "none",
    )


def from_args(args: argparse.Namespace, backend: str) -> BackendOptions:
    """Adapt an argparse namespace to a per-backend options dataclass.

    Reads only fields the top-level ``survey/cli.py`` parser exposes today
    (``out_dir``, ``max_files``, ``max_bytes``, ``dry_run``, ``datagov_query``).
    Unknown attributes fall back to their dataclass defaults via ``getattr``.
    """
    base = _base_from_args(args)
    if backend == "data.gov":
        return DataGovOptions(
            base=base, query=getattr(args, "datagov_query", "csv") or "csv"
        )
    if backend in ("data.gov.uk", "ckan"):
        return CkanOptions(
            base=base,
            source=getattr(args, "source", "data.gov.uk") or "data.gov.uk",
            endpoint=getattr(args, "ckan_endpoint", None),
        )
    if backend == "data.europa.eu":
        return DataEuropaEuOptions(base=base)
    if backend in ("inside_airbnb", "hf", "kaggle"):
        # Deferred stub backends: return the bare base; the stub run() exits 2.
        return base
    raise ValueError(f"unknown backend: {backend!r}")
