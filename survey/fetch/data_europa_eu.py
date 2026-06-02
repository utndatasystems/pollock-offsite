"""data.europa.eu fetch backend (EU Open Data Portal).

The portal exposes a JSON search API at
``https://data.europa.eu/api/hub/search/search`` that returns DCAT-style
records. Filtering ``filter=dataset&facets[format][]=CSV`` narrows to
datasets with at least one CSV-flagged distribution; we still filter
``distributions[]`` client-side because a CSV-flagged dataset can also
expose ZIP/PDF/etc. distributions.

The catalog is huge (~1.7M datasets) and the upstream ``access_url`` for
a distribution typically points at a national publisher (data.gov.ua,
opendata.gov.fr, …), not a unified EU CDN — HEAD support is uneven and
``byte_size`` is frequently missing. We treat both as best-effort and
fall back to the post-download size check (same idiom as
``fetch/datagov.py``).

Pagination is integer-page-based (``limit`` capped at 1000), so we
persist a single ``next_page`` integer rather than the opaque cursor
data.gov uses.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tqdm.auto import tqdm

from . import manifest, storage
from ._log import get_logger

logger = get_logger("data_europa_eu")


_SEARCH_URL = "https://data.europa.eu/api/hub/search/search"
_PAGE_SIZE = 1000  # max allowed by the API
_USER_AGENT = "pollock-survey/0.1 (+https://github.com/HPI-Information-Systems/Pollock)"
_REQUEST_TIMEOUT = 60
_DOWNLOAD_TIMEOUT = 120
_MAX_PER_RESOURCE_BYTES = 500 * 1024 * 1024  # 500 MB cap per file
_DOWNLOAD_CONCURRENCY = 8


@dataclass
class _CsvCandidate:
    dataset_id: str
    distribution_id: str | None
    title: str
    url: str
    size_hint: int | None


def _http_get(url: str, *, timeout: int = _REQUEST_TIMEOUT) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), (resp.headers.get("Content-Type") or "").lower()


def _http_head_size(url: str, *, timeout: int = 15) -> int | None:
    try:
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": _USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl is not None else None
    except (urllib.error.URLError, urllib.error.HTTPError, http.client.HTTPException,
            ValueError, TimeoutError, OSError):
        return None


def _looks_like_csv(body: bytes, content_type: str) -> bool:
    if "text/html" in content_type or "application/json" in content_type:
        return False
    if "application/xml" in content_type or "text/xml" in content_type:
        return False
    if "application/zip" in content_type or "application/x-zip" in content_type:
        return False
    head = body[:1024].lstrip()
    if head.startswith((b"<!DOCTYPE", b"<html", b"<HTML", b"<?xml", b"<!--")):
        return False
    if head.startswith(b"{") and b'"' in head[:200]:
        return False
    if head.startswith(b"PK\x03\x04"):  # zip magic
        return False
    return True


def _pick_title(title_field) -> str:
    """Titles come back as language-keyed dicts (``{"en": "...", "de": "..."}``)
    or sometimes as plain strings on older records. Pick English first, then
    any non-empty value, else empty string."""
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
    url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        body = resp.read()
    return json.loads(body).get("result", {}) or {}


def _is_safe_http_url(url: str) -> bool:
    """Reject malformed catalog entries before they hit urllib.

    The data.europa.eu catalog occasionally returns ``access_url`` values that
    are dataset titles or otherwise non-URLs, which crash
    ``http.client._validate_host`` with ``InvalidURL``. Require an http(s)
    scheme, a netloc, and no control characters / whitespace in the host.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    if any(c.isspace() or ord(c) < 0x20 for c in parsed.netloc):
        return False
    return True


def _extract_csv_candidates(results: list[dict]) -> list[_CsvCandidate]:
    out: list[_CsvCandidate] = []
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
            if not url or not _is_safe_http_url(url):
                continue
            size_hint = d.get("byte_size")
            try:
                size_hint = int(size_hint) if size_hint else None
            except (TypeError, ValueError):
                size_hint = None
            out.append(
                _CsvCandidate(
                    dataset_id=dataset_id,
                    distribution_id=d.get("id"),
                    title=title,
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
    error: str | None


def _fetch_one(cand: _CsvCandidate) -> _DownloadOutcome:
    size_hint = cand.size_hint
    if size_hint is None:
        size_hint = _http_head_size(cand.url) or 0
    if size_hint and size_hint > _MAX_PER_RESOURCE_BYTES:
        return _DownloadOutcome(cand, None, "", "oversize")
    try:
        body, content_type = _http_get(cand.url, timeout=_DOWNLOAD_TIMEOUT)
    except (urllib.error.URLError, urllib.error.HTTPError, http.client.HTTPException,
            ValueError, TimeoutError, OSError) as exc:
        return _DownloadOutcome(cand, None, "", f"http:{exc!r}"[:200])
    if len(body) > _MAX_PER_RESOURCE_BYTES:
        return _DownloadOutcome(cand, None, content_type, "oversize_body")
    if not _looks_like_csv(body, content_type):
        return _DownloadOutcome(cand, None, content_type, "not_csv")
    return _DownloadOutcome(cand, body, content_type, None)


_STATE_FILE = ".data_europa_eu_state.json"


def _state_path(out_dir: Path) -> Path:
    return out_dir / _STATE_FILE


def _load_next_page(out_dir: Path) -> int:
    p = _state_path(out_dir)
    if not p.exists():
        return 0
    try:
        with open(p) as f:
            return int(json.load(f).get("next_page", 0))
    except Exception:
        return 0


def _save_next_page(out_dir: Path, page: int | None) -> None:
    p = _state_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump({"next_page": page}, f)


def run_data_europa_eu(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    max_files = args.max_files
    max_bytes = args.max_bytes

    page = _load_next_page(out_dir)
    if page > 0:
        logger.info(f"[fetch/data.europa.eu] resuming from page {page}")

    try:
        first = _search_page(page)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        logger.info(f"[fetch/data.europa.eu] endpoint unreachable ({exc!r}); skipping")
        return 1

    total = first.get("count")
    if total is not None:
        logger.info(f"[fetch/data.europa.eu] catalog reports {total} CSV-flagged datasets")

    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    # The global ledger (.fetch_state.json) is shared across all backends and
    # gets bumped by this run's contribution at flush time.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    known_hashes = manifest.load_known_hashes(out_dir)
    rows: list[manifest.ManifestRow] = []
    n_seen = n_kept = n_skipped = 0
    current = first
    bar = tqdm(
        total=max_files,
        desc="fetch data.europa.eu",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    while True:
        results = current.get("results") or []
        candidates = _extract_csv_candidates(results)

        if args.dry_run:
            for cand in candidates:
                if max_files is not None and n_kept >= max_files:
                    break
                logger.info(f"[dry-run] data.europa.eu {cand.size_hint or '?'}B {cand.url}")
                n_seen += 1
                n_kept += 1
                bar.update(1)
            if max_files is not None and n_kept >= max_files:
                _save_next_page(out_dir, page)
                break
        else:
            page_budget = (max_files - n_kept if max_files is not None else None)
            page_candidates = (
                candidates[: page_budget * 2] if page_budget is not None else candidates
            )

            cap_hit = False
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
                                logger.info(
                                    f"[fetch/data.europa.eu] download failed: {cand.url} "
                                    f"({outcome.error[5:]})"
                                )
                            n_skipped += 1
                            bar.set_postfix(
                                MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped
                            )
                            continue

                        body = outcome.body
                        assert body is not None
                        sha = hashlib.sha256(body).hexdigest()
                        if sha in known_hashes:
                            n_skipped += 1
                            bar.set_postfix(
                                MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped
                            )
                            continue

                        real_size = len(body)
                        if bytes_this_run + real_size > max_bytes:
                            logger.info("[fetch/data.europa.eu] byte cap reached; stopping")
                            cap_hit = True
                            break

                        staged = storage.stage_path("data.europa.eu", cand.url)
                        with open(staged, "wb") as f:
                            f.write(body)
                        bytes_this_run += real_size
                        known_hashes.add(sha)
                        n_kept += 1
                        bar.update(1)
                        bar.set_postfix(
                            MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped
                        )

                        rows.append(
                            manifest.ManifestRow(
                                origin="data.europa.eu",
                                url=cand.url,
                                sha256=sha,
                                bytes=real_size,
                                source="data.europa.eu",
                                picked_reason=f"data.europa.eu:{cand.title}"[:180],
                                fetched_at=manifest.now_iso(),
                                local_path=str(staged.resolve()),
                            )
                        )

                        if len(rows) % 25 == 0:
                            manifest.append_rows(out_dir, rows)
                            manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
                            rows.clear()
                finally:
                    for f in futures:
                        f.cancel()

            if cap_hit:
                # Resume on the same page next time — leftover candidates
                # will be re-considered (sha-dedup keeps it idempotent).
                _save_next_page(out_dir, page)
                break

            if max_files is not None and n_kept >= max_files:
                _save_next_page(out_dir, page + 1)
                break

        # Page complete; advance.
        if not results:
            # Catalog exhausted.
            _save_next_page(out_dir, page)
            break

        page += 1
        if total is not None and page * _PAGE_SIZE >= total:
            _save_next_page(out_dir, page)
            break
        _save_next_page(out_dir, page)
        try:
            current = _search_page(page)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            logger.info(f"[fetch/data.europa.eu] page request failed: {exc!r}; stopping")
            break

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    logger.info(
        f"[fetch/data.europa.eu] done: seen={n_seen}, kept={n_kept}, skipped={n_skipped}, "
        f"bytes_this_run={bytes_this_run:,}"
    )
    return 0
