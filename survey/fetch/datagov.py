"""data.gov fetch backend (US federal catalog).

The CKAN action API at ``catalog.data.gov/api/3/action/...`` was
discontinued (returns 404). The current way to discover federal datasets
programmatically is the **htmx JSON search endpoint** that powers the
catalog's HTML UI — visible by following the cursor-paginated request
the page itself fires:

    GET https://catalog.data.gov/search?q=csv&per_page=20&sort=popularity[&after=<cursor>]

Returns a JSON object:

    {
      "after": "<base64 cursor>",   # null when exhausted
      "results": [
        {
          "dcat": {
            "title": "...",
            "distribution": [
              {"downloadURL": "...", "format": "CSV", "mediaType": "text/csv", "title": "..."},
              ...
            ]
          }
        }, ...
      ]
    }

We walk the cursor, filter ``distribution[]`` for CSV-format entries,
HEAD-check size, download the body, and append to the manifest. Same
HTML-stub filter and idempotent-on-sha256 pattern as ``fetch/ckan.py``.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tqdm.auto import tqdm

from . import _http, manifest, storage
from ._filters import is_safe_http_url, looks_like_csv
from ._log import get_logger

logger = get_logger("datagov")


_SEARCH_URL = "https://catalog.data.gov/search"
_PAGE_SIZE = 20
_REQUEST_TIMEOUT = 30
_MAX_PER_RESOURCE_BYTES = 50 * 1024 * 1024  # skip files > 50 MB; survey doesn't need them
_DOWNLOAD_CONCURRENCY = 8  # parallel HTTP fetches per page


@dataclass
class _CsvCandidate:
    package_title: str
    resource_title: str
    url: str
    size_hint: int | None


def _search_page(query: str, after: str | None) -> dict:
    params = {
        "q": query,
        "per_page": _PAGE_SIZE,
        "sort": "popularity",
    }
    if after:
        params["after"] = after
    url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    body, _ = _http.get_bytes(url, timeout=_REQUEST_TIMEOUT)
    return json.loads(body)


def _extract_csv_candidates(results: list[dict]) -> list[_CsvCandidate]:
    out: list[_CsvCandidate] = []
    for ds in results:
        dcat = ds.get("dcat") or {}
        title = (dcat.get("title") or "").strip()
        for d in dcat.get("distribution") or []:
            url = (d.get("downloadURL") or "").strip()
            fmt = (d.get("format") or "").strip().lower()
            media = (d.get("mediaType") or "").strip().lower()
            if not url:
                continue
            if fmt != "csv" and "csv" not in media:
                continue
            size_hint = d.get("byteSize")
            try:
                size_hint = int(size_hint) if size_hint is not None else None
            except (TypeError, ValueError):
                size_hint = None
            out.append(
                _CsvCandidate(
                    package_title=title,
                    resource_title=(d.get("title") or "").strip(),
                    url=url,
                    size_hint=size_hint,
                )
            )
    return out


@dataclass
class _DownloadOutcome:
    candidate: _CsvCandidate
    body: bytes | None
    content_type: str
    error: str | None  # None on success, "oversize"/"http"/"not_csv" otherwise


def _fetch_one(cand: _CsvCandidate) -> _DownloadOutcome:
    """HEAD-check + GET one candidate. Returns an outcome the caller can sequence.

    Pure function: no shared state, safe to run from a thread pool.
    """
    if not is_safe_http_url(cand.url):
        return _DownloadOutcome(cand, None, "", "unsafe_url")
    size_hint = cand.size_hint
    if size_hint is None:
        size_hint = _http.head_size(cand.url) or 0
    if size_hint and size_hint > _MAX_PER_RESOURCE_BYTES:
        return _DownloadOutcome(cand, None, "", "oversize")
    try:
        # 30 s is enough for any CSV under our 50 MB cap on a non-pathological
        # connection. Slow ArcGIS / dead agency hosts shouldn't block the page.
        body, content_type = _http.get_bytes(cand.url, timeout=30)
    except _http.HTTP_ERRORS as exc:
        return _DownloadOutcome(cand, None, "", f"http:{exc!r}"[:200])
    if not looks_like_csv(body, content_type):
        return _DownloadOutcome(cand, None, content_type, "not_csv")
    if len(body) > _MAX_PER_RESOURCE_BYTES:
        return _DownloadOutcome(cand, None, content_type, "oversize_body")
    return _DownloadOutcome(cand, body, content_type, None)


# --- Cursor persistence ---------------------------------------------------
# data.gov's /search endpoint paginates with an opaque base64 ``after=``
# token. We store the *next* cursor under ``<out-dir>/.datagov_cursors.json``
# keyed by query, so re-runs of the same ``--datagov-query`` pick up where
# the previous run stopped (or hit ``--max-bytes``) instead of starting
# from the most-popular results again.

_CURSOR_FILE = ".datagov_cursors.json"


def _cursor_path(out_dir: Path) -> Path:
    return out_dir / _CURSOR_FILE


def _load_cursor(out_dir: Path, query: str) -> str | None:
    p = _cursor_path(out_dir)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            data = json.load(f)
    except Exception:
        return None
    return data.get(query)


def _save_cursor(out_dir: Path, query: str, cursor: str | None) -> None:
    p = _cursor_path(out_dir)
    data: dict = {}
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
        except Exception:
            data = {}
    if cursor is None:
        data.pop(query, None)
    else:
        data[query] = cursor
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, sort_keys=True, indent=2)


_SEARCH_ERRORS = _http.HTTP_ERRORS + (json.JSONDecodeError,)


def run_datagov(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    max_files = args.max_files
    max_bytes = args.max_bytes
    query = getattr(args, "datagov_query", None) or "csv"
    skip_pages = int(getattr(args, "datagov_skip_pages", 0) or 0)

    logger.info(f"[fetch/data.gov] query={query!r}")

    # Resume: pick up where the previous run for this query stopped (if any).
    persisted_cursor = _load_cursor(out_dir, query)
    after: str | None = persisted_cursor
    if after is not None:
        logger.info(f"[fetch/data.gov] resuming from persisted cursor for query {query!r}")

    # Probe with one search page to fail fast on outages.
    try:
        first = _search_page(query, after)
    except _SEARCH_ERRORS as exc:
        logger.error(f"[fetch/data.gov] endpoint unreachable ({exc!r}); skipping")
        return 1

    # Optional one-shot fast-forward: skip N pages before doing real work.
    # Useful exactly once — when an earlier run hit --max-bytes and the
    # cursor wasn't persisted yet (the persistence landed later).
    if skip_pages > 0:
        logger.info(
            f"[fetch/data.gov] fast-forwarding past {skip_pages} pages "
            "(no downloads performed)"
        )
        page = first
        for i in range(skip_pages):
            after = page.get("after")
            if not after:
                logger.info(
                    f"[fetch/data.gov] catalog exhausted after {i} skips; nothing to do"
                )
                _save_cursor(out_dir, query, None)
                return 0
            try:
                page = _search_page(query, after)
            except _SEARCH_ERRORS as exc:
                logger.error(f"[fetch/data.gov] page request failed during skip: {exc!r}")
                return 1
        first = page

    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    # The global ledger (.fetch_state.json) is shared across all backends and
    # gets bumped by this run's contribution at flush time.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    rows: list[manifest.ManifestRow] = []
    n_seen = n_kept = n_skipped = 0
    page = first
    bar = tqdm(
        total=max_files,
        desc="fetch data.gov",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    while True:
        results = page.get("results") or []
        candidates = _extract_csv_candidates(results)

        if args.dry_run:
            for cand in candidates:
                if max_files is not None and n_kept >= max_files:
                    break
                logger.info(f"[dry-run] data.gov {cand.size_hint or '?'}B {cand.url}")
                n_seen += 1
                n_kept += 1
                bar.update(1)
        else:
            # Cap per-page candidate count so we don't queue more work than
            # we'll keep — but leave a margin so failed downloads can be
            # backfilled.
            page_budget = (max_files - n_kept if max_files is not None else None)
            page_candidates = (
                candidates[: page_budget * 2] if page_budget is not None else candidates
            )

            cap_hit = False
            # Submit all candidates and consume completions in finish-order
            # so a single slow URL doesn't block the page. Cancel pending
            # futures the moment we hit --max-files or --max-bytes.
            with ThreadPoolExecutor(max_workers=_DOWNLOAD_CONCURRENCY) as pool:
                futures = {pool.submit(_fetch_one, c): c for c in page_candidates}
                try:
                    for fut in as_completed(futures):
                        outcome = fut.result()
                        if max_files is not None and n_kept >= max_files:
                            break
                        cand = outcome.candidate
                        n_seen += 1

                        if outcome.error is not None:
                            if outcome.error.startswith("http:"):
                                logger.warning(
                                    f"[fetch/data.gov] download failed: {cand.url} "
                                    f"({outcome.error[5:]})"
                                )
                            n_skipped += 1
                            bar.set_postfix(
                                MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped
                            )
                            continue

                        body = outcome.body
                        assert body is not None
                        real_size = len(body)
                        if bytes_this_run + real_size > max_bytes:
                            logger.info("[fetch/data.gov] byte cap reached; stopping")
                            cap_hit = True
                            break

                        sha = hashlib.sha256(body).hexdigest()
                        staged = storage.stage_path("data.gov", cand.url)
                        with open(staged, "wb") as f:
                            f.write(body)
                        bytes_this_run += real_size
                        n_kept += 1
                        bar.update(1)
                        bar.set_postfix(
                            MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped
                        )

                        rows.append(
                            manifest.ManifestRow(
                                origin="data.gov",
                                url=cand.url,
                                sha256=sha,
                                bytes=real_size,
                                source="data.gov",
                                picked_reason=f"datagov:{cand.package_title or cand.resource_title}"[:180],
                                fetched_at=manifest.now_iso(),
                                local_path=str(staged.resolve()),
                            )
                        )

                        if len(rows) % 25 == 0:
                            manifest.append_rows(out_dir, rows)
                            manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
                            rows.clear()
                finally:
                    # Cancel anything still pending; in-flight downloads
                    # finish naturally because urllib doesn't support cancel.
                    for f in futures:
                        f.cancel()

            if cap_hit:
                # Persist the *current* page's next-cursor so the resume
                # skips this partially-processed page (avoids re-fetching the
                # files we already kept on this page; the leftover candidates
                # we didn't reach are sacrificed — fine, the catalog is huge).
                _save_cursor(out_dir, query, page.get("after"))
                break

        if max_files is None or n_kept < max_files:
            # Inner loop completed without `break` — advance cursor.
            after = page.get("after")
            if not after or (max_files is not None and n_kept >= max_files):
                # Catalog exhausted (or we hit --max-files exactly). Either
                # way, persist whatever ``after`` we have so the next run
                # picks up correctly. ``None`` clears the cursor.
                _save_cursor(out_dir, query, after)
                break
            # Persist the next cursor *before* we make the next request, so
            # if the run is killed mid-page we still resume on this one.
            _save_cursor(out_dir, query, after)
            try:
                page = _search_page(query, after)
            except _SEARCH_ERRORS as exc:
                logger.error(f"[fetch/data.gov] page request failed: {exc!r}; stopping")
                break
            continue
        # Hit --max-files; persist the next-cursor so a re-run with a
        # bigger cap continues from here.
        _save_cursor(out_dir, query, page.get("after"))
        break  # broke out of inner loop because of cap

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    logger.info(
        f"[fetch/data.gov] done: seen={n_seen}, kept={n_kept}, skipped={n_skipped}, "
        f"bytes_this_run={bytes_this_run:,}"
    )
    return 0
