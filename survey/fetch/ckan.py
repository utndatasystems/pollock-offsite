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
from typing import Iterator
from urllib.parse import urlencode

from . import _http
from ._backend import add_common_args, run_paginated
from ._download import Candidate
from ._filters import is_safe_http_url
from ._log import get_logger
from ._pagination import paginate
from ._state import State
from .config import CkanOptions, FetchOptions, from_args

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
    """Resolve the CKAN endpoint and reject unsafe inputs.

    Rejects schemes other than http/https, userinfo (``user:pass@``), private
    or loopback hosts, and (when not ``--allow-http``) plain ``http://``.
    """
    if opts.endpoint:
        endpoint = opts.endpoint.rstrip("/")
    else:
        endpoint = (
            os.environ.get(_LEGACY_ENV_OVERRIDE) or _DEFAULT_ENDPOINT
        ).rstrip("/")
    require_https = not opts.base.allow_http
    if not is_safe_http_url(endpoint + "/", require_https=require_https):
        raise ValueError(
            f"unsafe or non-https CKAN endpoint: {endpoint!r} "
            f"(pass --allow-http to permit plain http)"
        )
    return endpoint


def _ckan_search(
    endpoint: str, start: int, rows: int, *, require_https: bool = True
) -> dict:
    params = urlencode({"q": "res_format:CSV", "rows": rows, "start": start})
    body, _ = _http.get_bytes(
        f"{endpoint}/api/3/action/package_search?{params}",
        timeout=_REQUEST_TIMEOUT,
        require_https=require_https,
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


def _candidates_factory_for(endpoint: str, source: str):
    def _factory(base: FetchOptions, state: State, dry_run: bool) -> Iterator[Candidate]:
        require_https = not base.allow_http

        def get_cursor() -> int:
            cursors = state.get(_CURSOR_KEY) or {}
            try:
                return int(cursors.get(source, 0) or 0)
            except (TypeError, ValueError):
                return 0

        def set_cursor(value: int) -> None:
            cursors = dict(state.get(_CURSOR_KEY) or {})
            cursors[source] = int(value)
            state.set(_CURSOR_KEY, cursors)

        initial = get_cursor()
        if initial > 0:
            logger.info(f"resuming from persisted offset start={initial}")

        def fetch_page(start: int) -> dict:
            return _ckan_search(
                endpoint, start=start, rows=_PAGE_SIZE, require_https=require_https
            )

        def advance(start: int, page: dict) -> "tuple[int, bool] | None":
            if not page.get("success"):
                logger.error(
                    f"endpoint reported success=false: "
                    f"{page.get('error') or page.get('message')}"
                )
                return None
            results = (page.get("result") or {}).get("results") or []
            if not results:
                return (0, True)
            return (start + len(results), False)

        def extract(page: dict) -> Iterator[Candidate]:
            results = (page.get("result") or {}).get("results") or []
            for r in _walk_resources(results):
                yield Candidate(
                    url=r.url,
                    origin=source,
                    picked_reason=f"ckan:{r.package_title or r.resource_name}"[:180],
                    size_hint=r.size_hint,
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


def run(opts: CkanOptions) -> int:
    base: FetchOptions = opts.base
    try:
        endpoint = _resolve_endpoint(opts)
    except ValueError as exc:
        logger.error(str(exc))
        return 2
    source = opts.source
    require_https = not base.allow_http

    logger.info(f"source={source} endpoint={endpoint}")

    # Probe so the user gets a clear failure mode for unreachable endpoints.
    try:
        probe = _ckan_search(endpoint, start=0, rows=1, require_https=require_https)
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

    return run_paginated(
        base,
        source=source,
        candidates_factory=_candidates_factory_for(endpoint, source),
        logger=logger,
    )
