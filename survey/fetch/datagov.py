"""data.gov fetch backend (US federal catalog).

The CKAN action API at ``catalog.data.gov/api/3/action/...`` was
discontinued (returns 404). The current way to discover federal datasets
programmatically is the **htmx JSON search endpoint** that powers the
catalog's HTML UI:

    GET https://catalog.data.gov/search?q=csv&per_page=20&sort=popularity[&after=<cursor>]

Returns a JSON object with an opaque base64 ``after`` cursor and a
``results[]`` list of DCAT records. We walk the cursor, filter
``distribution[]`` for CSV-format entries, and feed them through the shared
``download_loop`` (which dedups against ``known_hashes``, enforces caps,
and writes the manifest).
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
from ._log import get_logger
from ._pagination import paginate
from ._state import State
from .config import DataGovOptions, FetchOptions, from_args

logger = get_logger("datagov")


name = "data.gov"

_SEARCH_URL = "https://catalog.data.gov/search"
_PAGE_SIZE = 20
_REQUEST_TIMEOUT = 30
_CURSOR_KEY = "datagov_cursors"
_SEARCH_ERRORS = _http.HTTP_ERRORS + (json.JSONDecodeError,)


@dataclass
class _CsvHit:
    package_title: str
    resource_title: str
    url: str
    size_hint: int | None


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register the ``data.gov`` subparser."""
    p = sp.add_parser(name, help="Fetch CSV resources from catalog.data.gov.")
    p.add_argument(
        "--datagov-query",
        default="csv",
        help="Search query passed to catalog.data.gov (default: 'csv').",
    )
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> DataGovOptions:
    opts = from_args(args, name)
    assert isinstance(opts, DataGovOptions)
    return opts


def _search_page(query: str, after: str | None, *, require_https: bool = True) -> dict:
    params = {"q": query, "per_page": _PAGE_SIZE, "sort": "popularity"}
    if after:
        params["after"] = after
    body, _ = _http.get_bytes(
        f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}",
        timeout=_REQUEST_TIMEOUT,
        require_https=require_https,
    )
    return json.loads(body)


def _extract_hits(results: list[dict]) -> Iterator[_CsvHit]:
    for ds in results:
        dcat = ds.get("dcat") or {}
        title = (dcat.get("title") or "").strip()
        for d in dcat.get("distribution") or []:
            url = (d.get("downloadURL") or "").strip()
            fmt = (d.get("format") or "").strip().lower()
            media = (d.get("mediaType") or "").strip().lower()
            if not url or (fmt != "csv" and "csv" not in media):
                continue
            size_hint = d.get("byteSize")
            try:
                size_hint = int(size_hint) if size_hint is not None else None
            except (TypeError, ValueError):
                size_hint = None
            yield _CsvHit(
                package_title=title,
                resource_title=(d.get("title") or "").strip(),
                url=url,
                size_hint=size_hint,
            )


def _candidates_factory_for(query: str):
    def _factory(base: FetchOptions, state: State, dry_run: bool) -> Iterator[Candidate]:
        require_https = not base.allow_http

        def get_cursor() -> str | None:
            cursors = state.get(_CURSOR_KEY) or {}
            return cursors.get(query)

        def set_cursor(cursor: str | None) -> None:
            cursors = dict(state.get(_CURSOR_KEY) or {})
            if cursor is None:
                cursors.pop(query, None)
            else:
                cursors[query] = cursor
            state.set(_CURSOR_KEY, cursors)

        if get_cursor() is not None:
            logger.info(f"resuming from persisted cursor for query {query!r}")

        def fetch_page(after: str | None) -> dict:
            return _search_page(query, after, require_https=require_https)

        def advance(_after: str | None, page: dict) -> "tuple[str | None, bool]":
            results = page.get("results") or []
            if not results:
                return (None, True)
            next_after = page.get("after")
            return (next_after, not next_after)

        def extract(page: dict) -> Iterator[Candidate]:
            for hit in _extract_hits(page.get("results") or []):
                yield Candidate(
                    url=hit.url,
                    origin=name,
                    picked_reason=f"datagov:{hit.package_title or hit.resource_title}"[:180],
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

    return _factory


def run(opts: DataGovOptions) -> int:
    logger.info(f"query={opts.query!r}")
    return run_paginated(
        opts.base,
        source=name,
        candidates_factory=_candidates_factory_for(opts.query),
        logger=logger,
    )
