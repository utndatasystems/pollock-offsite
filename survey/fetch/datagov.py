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
from pathlib import Path
from typing import Iterator

from . import _http, storage
from ._backend import add_common_args
from ._download import Candidate, download_loop
from ._log import get_logger
from ._state import State
from .config import DataGovOptions, FetchOptions, from_args
from .manifest import ManifestWriter

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
    """Register the ``data.gov`` subparser. Phase 7 owns the top-level CLI."""
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


def _search_page(query: str, after: str | None) -> dict:
    params = {"q": query, "per_page": _PAGE_SIZE, "sort": "popularity"}
    if after:
        params["after"] = after
    body, _ = _http.get_bytes(
        f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}", timeout=_REQUEST_TIMEOUT
    )
    return json.loads(body)


def _extract(results: list[dict]) -> Iterator[_CsvHit]:
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


def _iter_candidates(
    query: str, get_after, set_after
) -> Iterator[Candidate]:
    """Walk pages and yield ``Candidate`` objects until the cursor is exhausted.

    Persists the *next* page's cursor *before* yielding the current page's
    candidates. If the consumer stops mid-page (cap_hit), the cursor already
    points at the next page, so a re-run skips this partially-processed page;
    the leftover candidates we didn't reach are sacrificed (sha-dedup keeps it
    safe across the page boundary on a re-run too).
    """
    after: str | None = get_after()
    if after is not None:
        logger.info(f"resuming from persisted cursor for query {query!r}")

    while True:
        try:
            page = _search_page(query, after)
        except _SEARCH_ERRORS as exc:
            logger.error(f"page request failed: {exc!r}; stopping")
            return
        results = page.get("results") or []
        next_after = page.get("after")
        # Persist next cursor *before* yielding so cap_hit mid-page is safe.
        set_after(next_after)
        for hit in _extract(results):
            yield Candidate(
                url=hit.url,
                origin=name,
                picked_reason=f"datagov:{hit.package_title or hit.resource_title}"[:180],
                size_hint=hit.size_hint,
            )
        if not next_after:
            return
        after = next_after


def run(opts: DataGovOptions) -> int:
    base: FetchOptions = opts.base
    out_dir: Path = Path(base.out_dir).resolve()
    state = State(out_dir)
    logger.info(f"query={opts.query!r}")

    def get_after() -> str | None:
        cursors = state.get(_CURSOR_KEY) or {}
        return cursors.get(opts.query)

    def set_after(cursor: str | None) -> None:
        cursors = dict(state.get(_CURSOR_KEY) or {})
        if cursor is None:
            cursors.pop(opts.query, None)
        else:
            cursors[opts.query] = cursor
        state.set(_CURSOR_KEY, cursors)

    candidates = _iter_candidates(opts.query, get_after, set_after)

    if base.dry_run:
        n = 0
        for cand in candidates:
            if base.max_files is not None and n >= base.max_files:
                break
            logger.info(f"[dry-run] {cand.size_hint or '?'}B {cand.url}")
            n += 1
        logger.info(f"dry-run done: {n} candidates")
        return 0

    def _stage(origin: str, url: str):
        return storage.stage_path(origin, url, base.data_root)

    with ManifestWriter(out_dir) as mw:
        summary = download_loop(
            candidates,
            opts=base,
            mw=mw,
            exclusive_stage=_stage,
            on_cap_hit=lambda _last: None,  # cursor already persisted on page advance
        )

    logger.info(
        f"done: seen={summary.n_seen}, kept={summary.n_kept}, "
        f"skipped={summary.n_skipped}, bytes_this_run={summary.bytes_this_run:,}"
    )
    return 0
