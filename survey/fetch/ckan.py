"""CKAN-portal fetch backend (data.gov.uk).

Targets the live CKAN 3 API at ``https://ckan.publishing.service.gov.uk``.
The public ``data.gov.uk`` site is a static portal; the underlying CKAN
instance is the address above.

Workflow:
1. ``package_search?q=res_format:CSV`` paginated until ``--max-files`` is hit.
2. Walk ``resources[]`` per package, keep CSV/TSV-format entries.
3. Stream each candidate through the shared ``download_loop``: HEAD-check
   size, stream-to-disk under per-file caps, sha-dedup against the manifest,
   and append manifest rows.

The endpoint URL can be overridden either with ``--endpoint`` (preferred)
or the legacy ``CKAN_DATA_GOV_UK_URL`` env var (consulted only when no
``--endpoint`` is given). Other CKAN portals would each get their own
backend module rather than sharing this one.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode

from . import _http, storage
from ._backend import add_common_args
from ._download import Candidate, download_loop
from ._log import get_logger
from ._state import State
from .config import CkanOptions, FetchOptions, from_args
from .manifest import ManifestWriter

logger = get_logger("ckan")


name = "data.gov.uk"

_DEFAULT_ENDPOINT = "https://ckan.publishing.service.gov.uk"
_LEGACY_ENV_OVERRIDE = "CKAN_DATA_GOV_UK_URL"
_PAGE_SIZE = 100
_REQUEST_TIMEOUT = 30
_CSV_FORMATS = {"csv", "tsv"}
_CURSOR_KEY = "ckan_cursors"
_SEARCH_ERRORS = _http.HTTP_ERRORS + (json.JSONDecodeError,)


@dataclass
class _CkanResource:
    package_title: str
    resource_name: str
    url: str
    size_hint: int | None


def add_subparser(sp: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = sp.add_parser(name, help="Fetch CSV resources from data.gov.uk's CKAN.")
    p.add_argument(
        "--endpoint",
        dest="ckan_endpoint",
        default=None,
        help=(
            f"CKAN endpoint URL (default: {_DEFAULT_ENDPOINT}). "
            f"Falls back to the {_LEGACY_ENV_OVERRIDE} env var if unset."
        ),
    )
    add_common_args(p)
    return p


def options_from_args(args: argparse.Namespace) -> CkanOptions:
    opts = from_args(args, name)
    assert isinstance(opts, CkanOptions)
    return opts


def _resolve_endpoint(opts: CkanOptions) -> str:
    if opts.endpoint:
        return opts.endpoint.rstrip("/")
    return (os.environ.get(_LEGACY_ENV_OVERRIDE) or _DEFAULT_ENDPOINT).rstrip("/")


def _ckan_search(endpoint: str, start: int, rows: int) -> dict:
    params = urlencode({"q": "res_format:CSV", "rows": rows, "start": start})
    body, _ = _http.get_bytes(
        f"{endpoint}/api/3/action/package_search?{params}", timeout=_REQUEST_TIMEOUT
    )
    return json.loads(body)


def _walk_resources(packages: list[dict]) -> Iterator[_CkanResource]:
    for pkg in packages:
        title = (pkg.get("title") or "").strip()
        for r in pkg.get("resources") or []:
            url = (r.get("url") or "").strip()
            fmt = (r.get("format") or "").strip().lower()
            if not url or fmt not in _CSV_FORMATS:
                continue
            size_hint = r.get("size")
            try:
                size_hint = int(size_hint) if size_hint is not None else None
            except (TypeError, ValueError):
                size_hint = None
            yield _CkanResource(
                package_title=title,
                resource_name=(r.get("name") or "").strip(),
                url=url,
                size_hint=size_hint,
            )


def _iter_candidates(
    endpoint: str, source: str, get_start, set_start
) -> Iterator[Candidate]:
    """Walk CKAN pages from the resume offset, yielding ``Candidate`` objects.

    Persists the *next* page's ``start`` offset *before* yielding the current
    page's candidates. If the consumer stops mid-page (cap_hit), the cursor
    already points at the next page and a re-run skips this partially
    processed one (sha-dedup keeps it safe).
    """
    start: int = get_start()
    if start > 0:
        logger.info(f"resuming from persisted offset start={start}")

    while True:
        try:
            page = _ckan_search(endpoint, start=start, rows=_PAGE_SIZE)
        except _SEARCH_ERRORS as exc:
            logger.error(f"page request failed at start={start}: {exc!r}; stopping")
            return
        if not page.get("success"):
            logger.error(
                f"endpoint reported success=false: "
                f"{page.get('error') or page.get('message')}"
            )
            return
        results = (page.get("result") or {}).get("results") or []
        if not results:
            # Catalog exhausted; reset cursor.
            set_start(0)
            return
        next_start = start + len(results)
        # Persist next cursor *before* yielding so cap_hit mid-page is safe.
        set_start(next_start)
        for r in _walk_resources(results):
            yield Candidate(
                url=r.url,
                origin=source,
                picked_reason=f"ckan:{r.package_title or r.resource_name}"[:180],
                size_hint=r.size_hint,
            )
        start = next_start


def run(opts: CkanOptions) -> int:
    base: FetchOptions = opts.base
    out_dir: Path = Path(base.out_dir).resolve()
    endpoint = _resolve_endpoint(opts)
    source = opts.source
    state = State(out_dir)

    logger.info(f"source={source} endpoint={endpoint}")

    # Probe so the user gets a clear failure mode for unreachable endpoints.
    try:
        probe = _ckan_search(endpoint, start=0, rows=1)
        if not probe.get("success"):
            logger.error(
                f"endpoint reported success=false; aborting "
                f"({probe.get('error') or probe.get('message')})"
            )
            return 1
        total = probe.get("result", {}).get("count", 0)
        logger.info(f"endpoint healthy: {total:,} packages indexed")
    except _SEARCH_ERRORS as exc:
        logger.error(f"endpoint unreachable ({exc!r}); skipping {source}")
        return 1

    def get_start() -> int:
        cursors = state.get(_CURSOR_KEY) or {}
        try:
            return int(cursors.get(source, 0) or 0)
        except (TypeError, ValueError):
            return 0

    def set_start(value: int) -> None:
        cursors = dict(state.get(_CURSOR_KEY) or {})
        cursors[source] = int(value)
        state.set(_CURSOR_KEY, cursors)

    candidates = _iter_candidates(endpoint, source, get_start, set_start)

    if base.dry_run:
        n = 0
        for cand in candidates:
            if base.max_files is not None and n >= base.max_files:
                break
            logger.info(f"[dry-run] {source} {cand.size_hint or '?'}B {cand.url}")
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
        f"{source}: seen={summary.n_seen}, kept={summary.n_kept}, "
        f"skipped={summary.n_skipped}, bytes_this_run={summary.bytes_this_run:,}"
    )
    return 0
