"""CKAN-portal fetch backend.

Targets any CKAN 3-API endpoint. The two portals the user requested are:

- **data.gov.uk** — the public site is a static portal but the live CKAN
  instance is at ``https://ckan.publishing.service.gov.uk``. We use that.
- **data.gov (US)** — the CKAN endpoint at ``catalog.data.gov`` returns
  ``404 Not Found`` to ``/api/3/action/...`` requests as of 2026-05.
  When the configured endpoint is unreachable we log a clear error and
  return without writing any manifest rows; the survey can proceed
  without this source.

Override the CKAN URL with the env var ``CKAN_<source>_URL`` (e.g.
``CKAN_DATA_GOV_URL``) to point at a different mirror.

Workflow per source:
1. ``package_search?q=res_format:CSV`` paginated until ``--max-files`` is hit.
2. For each candidate package, walk ``resources[]`` and keep entries whose
   ``format`` matches CSV / TSV.
3. ``HEAD`` each resource URL, skip if size is unknown or > 200 MB.
4. Download the resource body to ``<out-dir>/raw/<sha256[:2]>/<sha256>.csv``,
   append a manifest row, increment the byte ledger.

Hard-stops on ``--max-bytes`` and ``--max-files``.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

from tqdm.auto import tqdm

from ..config import REPO_ROOT
from . import _http, manifest, storage
from ._filters import is_safe_http_url, looks_like_csv
from ._log import get_logger

logger = get_logger("ckan")


# Endpoint table. Override with env vars for offline / mirror testing.
_DEFAULT_ENDPOINTS = {
    "data.gov":    "https://catalog.data.gov",
    "data.gov.uk": "https://ckan.publishing.service.gov.uk",
}

_CSV_FORMATS = {"csv", "tsv"}
_MAX_PER_RESOURCE_BYTES = 200 * 1024 * 1024  # 200 MB cap per CSV
_REQUEST_TIMEOUT = 30
_PAGE_SIZE = 100


@dataclass
class CkanResource:
    package_title: str
    resource_name: str
    url: str
    format: str
    size_hint: int | None


def _endpoint_for(source: str) -> str:
    env_key = f"CKAN_{source.upper().replace('.', '_').replace('-', '_')}_URL"
    return os.environ.get(env_key) or _DEFAULT_ENDPOINTS[source]


def _ckan_search(endpoint: str, query: str, start: int, rows: int) -> dict:
    params = urlencode({"q": query, "rows": rows, "start": start})
    url = f"{endpoint}/api/3/action/package_search?{params}"
    body, _ = _http.get_bytes(url, timeout=_REQUEST_TIMEOUT)
    import json

    return json.loads(body)


def _walk_resources(packages: Iterable[dict]) -> Iterable[CkanResource]:
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
            yield CkanResource(
                package_title=title,
                resource_name=(r.get("name") or "").strip(),
                url=url,
                format=fmt,
                size_hint=size_hint,
            )


def run_ckan(args) -> int:
    source: str = args.source
    out_dir: Path = Path(args.out_dir).resolve()
    endpoint = _endpoint_for(source).rstrip("/")
    max_files = args.max_files
    max_bytes = args.max_bytes

    logger.info(f"[fetch/ckan] source={source} endpoint={endpoint}")

    # Probe the endpoint up front so the user gets a clear failure mode.
    try:
        probe = _ckan_search(endpoint, "*:*", start=0, rows=1)
        if not probe.get("success"):
            logger.info(
                f"[fetch/ckan] endpoint reported success=false; aborting "
                f"({probe.get('error') or probe.get('message')})"
            )
            return 1
        total = probe.get("result", {}).get("count", 0)
        logger.info(f"[fetch/ckan] endpoint healthy: {total:,} packages indexed")
    except _http.HTTP_ERRORS as exc:
        logger.info(f"[fetch/ckan] endpoint unreachable ({exc!r}); skipping {source}")
        return 1

    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    # The global ledger (.fetch_state.json) is shared across all backends and
    # gets bumped by this run's contribution at flush time.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    rows: list[manifest.ManifestRow] = []

    n_seen = n_kept = n_skipped = 0
    start = 0
    bar = tqdm(
        total=max_files,
        desc=f"fetch {source}",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    while True:
        if max_files is not None and n_kept >= max_files:
            break
        try:
            page = _ckan_search(endpoint, "res_format:CSV", start=start, rows=_PAGE_SIZE)
        except _http.HTTP_ERRORS as exc:
            logger.info(f"[fetch/ckan] page request failed at start={start}: {exc!r}; stopping")
            break
        results = (page.get("result") or {}).get("results") or []
        if not results:
            break
        start += len(results)

        for resource in _walk_resources(results):
            if max_files is not None and n_kept >= max_files:
                break
            n_seen += 1

            if args.dry_run:
                bar.update(1)
                logger.info(
                    f"[dry-run] {source} {resource.format} "
                    f"{resource.size_hint or '?'}B {resource.url}"
                )
                n_kept += 1
                continue

            size_hint = resource.size_hint
            if size_hint is None:
                size_hint = _http.head_size(resource.url) or 0
            if size_hint and size_hint > _MAX_PER_RESOURCE_BYTES:
                n_skipped += 1
                continue
            if size_hint and bytes_this_run + size_hint > max_bytes:
                logger.info(f"[fetch/ckan] byte cap reached; stopping at {bytes_this_run:,} bytes")
                break

            if not is_safe_http_url(resource.url):
                n_skipped += 1
                continue
            try:
                body, content_type = _http.get_bytes(resource.url, timeout=120)
            except _http.HTTP_ERRORS as exc:
                logger.info(f"[fetch/ckan] download failed: {resource.url} ({exc!r})")
                n_skipped += 1
                continue

            if not looks_like_csv(body, content_type):
                n_skipped += 1
                continue

            real_size = len(body)
            if bytes_this_run + real_size > max_bytes:
                logger.info("[fetch/ckan] byte cap reached after download; stopping")
                break
            sha = hashlib.sha256(body).hexdigest()
            staged, fh = storage.stage_path(source, resource.url, REPO_ROOT / "data")
            with fh:
                fh.write(body)
            bytes_this_run += real_size
            n_kept += 1
            bar.update(1)
            bar.set_postfix(MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped)

            rows.append(
                manifest.ManifestRow(
                    origin=source,
                    url=resource.url,
                    sha256=sha,
                    bytes=real_size,
                    source=source,
                    picked_reason=f"ckan:{resource.package_title or resource.resource_name}"[
                        :180
                    ],
                    fetched_at=manifest.now_iso(),
                    local_path=str(staged.resolve()),
                )
            )

            if len(rows) % 25 == 0:
                manifest.append_rows(out_dir, rows)
                manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
                rows.clear()

            time.sleep(0.05)  # be nice to the portal
        else:
            continue
        break  # broke out of inner loop because cap hit

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    logger.info(
        f"[fetch/ckan] {source}: seen={n_seen}, kept={n_kept}, skipped={n_skipped}, "
        f"bytes_this_run={bytes_this_run:,}"
    )
    return 0
