"""data.europa.eu fetch backend (EU Open Data Portal).

The portal exposes a JSON search API at
``https://data.europa.eu/api/hub/search/search`` that returns DCAT-style
records. Filtering ``filter=dataset&facets[format][]=CSV`` narrows to
datasets with at least one CSV-flagged distribution; we still filter
``distributions[]`` client-side because a CSV-flagged dataset can also
expose ZIP/PDF/etc. distributions.

The catalog is huge (~1.7M datasets) and the upstream ``access_url`` for
a distribution typically points at a national publisher (data.gov.ua,
opendata.gov.fr, ...), not a unified EU CDN -- HEAD support is uneven
and ``byte_size`` is frequently missing. The shared ``download_loop``
treats both as best-effort and falls back to the per-file streaming cap.

Pagination is integer-page-based (``limit`` capped at 1000); we persist
the next page under ``_state.State`` key ``data_europa_eu_next_page``.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
from dataclasses import dataclass
from typing import Iterator

from . import _http
from ._backend import add_common_args, run_paginated
from ._download import Candidate
from ._filters import is_safe_http_url
from ._log import get_logger
from ._pagination import paginate
from ._state import State
from .config import DataEuropaEuOptions, FetchOptions, from_args

logger = get_logger("data_europa_eu")


name = "data.europa.eu"

_SEARCH_URL = "https://data.europa.eu/api/hub/search/search"
_PAGE_SIZE = 1000  # max allowed by the API
_REQUEST_TIMEOUT = 60
_CURSOR_KEY = "data_europa_eu_next_page"
_SEARCH_ERRORS = _http.HTTP_ERRORS + (json.JSONDecodeError,)


@dataclass
class _CsvHit:
    dataset_id: str
    title: str
    url: str
    size_hint: int | None


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = sp.add_parser(name, help="Fetch CSV resources from data.europa.eu.")
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> DataEuropaEuOptions:
    opts = from_args(args, name)
    assert isinstance(opts, DataEuropaEuOptions)
    return opts


def _pick_title(title_field) -> str:
    """Title field comes back as a language-keyed dict on most records.

    Older records ship a plain string. Pick English first, then any non-empty
    value, else empty string.
    """
    if isinstance(title_field, str):
        return title_field.strip()
    if isinstance(title_field, dict):
        en = (title_field.get("en") or "").strip()
        if en:
            return en
        for v in title_field.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _search_page(page: int, *, require_https: bool = True) -> dict:
    params = {
        "filter": "dataset",
        "facets[format][]": "CSV",
        "limit": _PAGE_SIZE,
        "page": page,
    }
    body, _ = _http.get_bytes(
        f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}",
        timeout=_REQUEST_TIMEOUT,
        require_https=require_https,
    )
    return json.loads(body).get("result", {}) or {}


def _extract_hits(results: list[dict], *, require_https: bool = False) -> Iterator[_CsvHit]:
    for ds in results:
        dataset_id = ds.get("id") or ""
        if not dataset_id:
            continue
        title = _pick_title(ds.get("title"))
        for d in ds.get("distributions") or []:
            fmt = (d.get("format") or {}).get("id") or ""
            if fmt != "CSV":
                continue
            access_url = d.get("access_url") or []
            if not access_url:
                continue
            url = (access_url[0] or "").strip()
            if not url or not is_safe_http_url(url, require_https=require_https):
                continue
            size_hint = d.get("byte_size")
            try:
                size_hint = int(size_hint) if size_hint else None
            except (TypeError, ValueError):
                size_hint = None
            yield _CsvHit(
                dataset_id=dataset_id, title=title, url=url, size_hint=size_hint
            )


def _candidates_factory(
    base: FetchOptions, state: State, dry_run: bool
) -> Iterator[Candidate]:
    require_https = not base.allow_http

    def get_cursor() -> int:
        try:
            return int(state.get(_CURSOR_KEY, 0) or 0)
        except (TypeError, ValueError):
            return 0

    def set_cursor(value: int) -> None:
        state.set(_CURSOR_KEY, int(value))

    initial = get_cursor()
    if initial > 0:
        logger.info(f"resuming from page {initial}")

    def fetch_page(page: int) -> dict:
        return _search_page(page, require_https=require_https)

    def advance(page: int, current: dict) -> "tuple[int, bool]":
        results = current.get("results") or []
        total = current.get("count")
        if not results:
            return (0, True)
        next_page = page + 1
        if total is not None and next_page * _PAGE_SIZE >= total:
            return (0, True)
        return (next_page, False)

    def extract(current: dict) -> Iterator[Candidate]:
        for hit in _extract_hits(
            current.get("results") or [], require_https=require_https
        ):
            yield Candidate(
                url=hit.url,
                origin=name,
                picked_reason=f"data.europa.eu:{hit.title}"[:180],
                size_hint=hit.size_hint,
            )

    return paginate(
        fetch_page=fetch_page,
        advance=advance,
        extract=extract,
        get_cursor=get_cursor,
        set_cursor=set_cursor,
        logger=logger,
        search_errors=_SEARCH_ERRORS,
        dry_run=dry_run,
    )


def run(opts: DataEuropaEuOptions) -> int:
    return run_paginated(
        opts.base,
        source=name,
        candidates_factory=_candidates_factory,
        logger=logger,
    )
