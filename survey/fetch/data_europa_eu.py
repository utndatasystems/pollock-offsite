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
from pathlib import Path
from typing import Iterator

from . import _http, storage
from ._backend import add_common_args
from ._download import Candidate, download_loop
from ._filters import is_safe_http_url
from ._log import get_logger
from ._state import State
from .config import DataEuropaEuOptions, FetchOptions, from_args
from .manifest import ManifestWriter

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


def _search_page(page: int) -> dict:
    params = {
        "filter": "dataset",
        "facets[format][]": "CSV",
        "limit": _PAGE_SIZE,
        "page": page,
    }
    body, _ = _http.get_bytes(
        f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}", timeout=_REQUEST_TIMEOUT
    )
    return json.loads(body).get("result", {}) or {}


def _extract(results: list[dict]) -> Iterator[_CsvHit]:
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
            if not url or not is_safe_http_url(url):
                continue
            size_hint = d.get("byte_size")
            try:
                size_hint = int(size_hint) if size_hint else None
            except (TypeError, ValueError):
                size_hint = None
            yield _CsvHit(
                dataset_id=dataset_id, title=title, url=url, size_hint=size_hint
            )


def _iter_candidates(get_page, set_page) -> Iterator[Candidate]:
    """Walk pages from the persisted offset, yielding ``Candidate`` objects.

    Persists the *next* page *before* yielding the current page's candidates.
    If the consumer stops mid-page (cap_hit), the cursor already points at
    the next page; a re-run skips this partially-processed page (sha-dedup
    keeps it safe).
    """
    page: int = get_page()
    if page > 0:
        logger.info(f"resuming from page {page}")

    total: int | None = None

    while True:
        try:
            current = _search_page(page)
        except _SEARCH_ERRORS as exc:
            logger.error(f"page request failed at page={page}: {exc!r}; stopping")
            return
        if total is None:
            total = current.get("count")
            if total is not None:
                logger.info(f"catalog reports {total} CSV-flagged datasets")
        results = current.get("results") or []
        if not results:
            # Catalog exhausted; reset cursor.
            set_page(0)
            return
        next_page = page + 1
        # Persist next cursor *before* yielding so cap_hit mid-page is safe.
        if total is not None and next_page * _PAGE_SIZE >= total:
            # End of catalog after this page; reset cursor.
            set_page(0)
        else:
            set_page(next_page)
        for hit in _extract(results):
            yield Candidate(
                url=hit.url,
                origin=name,
                picked_reason=f"data.europa.eu:{hit.title}"[:180],
                size_hint=hit.size_hint,
            )
        page = next_page
        if total is not None and page * _PAGE_SIZE >= total:
            return


def run(opts: DataEuropaEuOptions) -> int:
    base: FetchOptions = opts.base
    out_dir: Path = Path(base.out_dir).resolve()
    state = State(out_dir)

    def get_page() -> int:
        try:
            return int(state.get(_CURSOR_KEY, 0) or 0)
        except (TypeError, ValueError):
            return 0

    def set_page(value: int) -> None:
        state.set(_CURSOR_KEY, int(value))

    candidates = _iter_candidates(get_page, set_page)

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
