"""Inside Airbnb fetch backend.

Source: https://insideairbnb.com/get-the-data/

Per the user's scope we only download the per-city gzipped ``listings.csv.gz``
and ``reviews.csv.gz`` files (skipping ``calendar.csv.gz`` and the
unzipped ``visualisations/*.csv`` files).

The data page renders the full link table server-side so we just regex-scrape
the HTML once. URLs look like::

    https://data.insideairbnb.com/<country>/<region>/<city>/<date>/data/listings.csv.gz

We mirror that path under ``data/inside_airbnb/csv/`` (dropping the
``/data/`` segment) so the basenames don't collide across the 119+ cities and
provenance is visible from the filesystem layout. Files are streamed through
to disk byte-for-byte without recompression.

Honors ``--max-files``, ``--max-bytes``, and ``--dry-run`` like the other
backends; emits one manifest row per downloaded file with ``origin =
"inside_airbnb"`` and ``source = "inside_airbnb:<city>"``.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from tqdm.auto import tqdm

from ..config import REPO_ROOT
from . import manifest
from ._log import get_logger

logger = get_logger("inside_airbnb")


_USER_AGENT = "pollock-survey/0.1 (+https://github.com/HPI-Information-Systems/Pollock)"
_GET_DATA_URL = "https://insideairbnb.com/get-the-data/"
_PER_RESOURCE_MAX_BYTES = 2 * 1024 * 1024 * 1024  # reviews.csv.gz can run hundreds of MB
_REQUEST_TIMEOUT = 60
_DOWNLOAD_TIMEOUT = 600
_CHUNK_BYTES = 64 * 1024

_URL_PATTERN = re.compile(
    r"https://data\.insideairbnb\.com/[^\"'\s<>]+/data/(?:listings|reviews)\.csv\.gz"
)


def _http_get_text(url: str, *, timeout: int = _REQUEST_TIMEOUT) -> str:
    """Fetch a URL and return its body decoded as UTF-8.

    The Inside Airbnb page omits a charset in Content-Type, so requests-style
    auto-detection would fall back to Latin-1 and mojibake non-ASCII city
    names (e.g. ``Ciudad Autónoma de Buenos Aires``).
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _cached_html_path(out_dir: Path) -> Path:
    return out_dir / ".inside_airbnb_get_the_data.html"


def _fetch_urls(out_dir: Path) -> list[str]:
    """Return sorted, de-duplicated list of listings/reviews .csv.gz URLs.

    Caches the source HTML under ``<out-dir>/.inside_airbnb_get_the_data.html``
    so reruns don't hammer the page.
    """
    cache = _cached_html_path(out_dir)
    if cache.exists():
        html = cache.read_text(encoding="utf-8")
    else:
        html = _http_get_text(_GET_DATA_URL)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(html, encoding="utf-8")
    return sorted(set(_URL_PATTERN.findall(html)))


def _city_id(url: str) -> str:
    """Extract a short city identifier (``<country>/<city>``) for logging."""
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 5:
        return f"{parts[0]}/{parts[2]}"
    return urlparse(url).path


def _output_path(url: str) -> Path:
    """Map a source URL to a local mirror path.

    ``.../united-states/ny/albany/2026-02-15/data/listings.csv.gz``
    -> ``<repo>/data/inside_airbnb/csv/united-states/ny/albany/2026-02-15/listings.csv.gz``
    """
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 2 and parts[-2] == "data":
        parts = parts[:-2] + parts[-1:]
    return REPO_ROOT.joinpath("data", "inside_airbnb", "csv", *parts)


def _ascii_url(url: str) -> str:
    """Percent-encode the URL path so urllib can put it on the wire.

    Some cities (e.g. ``ciudad-autónoma-de-buenos-aires``) embed non-ASCII
    characters that would otherwise raise ``UnicodeEncodeError`` in
    ``http.client``.
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=quote(parsed.path, safe="/")))


def _stream_to_disk(url: str, output_path: Path) -> tuple[int, str]:
    """Download ``url`` to ``output_path``, returning ``(bytes, sha256)``.

    Streams in 64 KiB chunks so reviews.csv.gz files (hundreds of MB) don't
    blow up memory. Hashes the bytes on the fly so we don't re-read the file.
    """
    import hashlib

    h = hashlib.sha256()
    total = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(_ascii_url(url), headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp, \
                open(output_path, "wb") as f:
            while True:
                chunk = resp.read(_CHUNK_BYTES)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                total += len(chunk)
    except Exception:
        # Drop partials so reruns retry cleanly.
        if output_path.exists():
            output_path.unlink()
        raise
    return total, h.hexdigest()


def run_inside_airbnb(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    max_files = args.max_files
    max_bytes = args.max_bytes

    logger.info(f"[fetch/inside_airbnb] discovering URLs from {_GET_DATA_URL}")
    try:
        urls = _fetch_urls(out_dir)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        logger.info(f"[fetch/inside_airbnb] URL discovery failed: {exc!r}")
        return 1
    logger.info(
        f"[fetch/inside_airbnb] {len(urls)} files available "
        f"({sum(1 for u in urls if u.endswith('listings.csv.gz'))} listings, "
        f"{sum(1 for u in urls if u.endswith('reviews.csv.gz'))} reviews)"
    )

    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    # The global ledger under .fetch_state.json (shared across all backends)
    # gets bumped by this run's contribution at flush time.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    known_hashes = manifest.load_known_hashes(out_dir)
    rows: list[manifest.ManifestRow] = []
    n_kept = n_skipped = 0

    bar = tqdm(
        total=max_files if max_files is not None else len(urls),
        desc="fetch inside_airbnb",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    for url in urls:
        if max_files is not None and n_kept >= max_files:
            break

        out_path = _output_path(url)

        if args.dry_run:
            logger.info(f"[dry-run] inside_airbnb {url} -> {out_path}")
            n_kept += 1
            bar.update(1)
            continue

        try:
            if out_path.exists():
                # Re-run idempotency: trust the existing file, hash it for the
                # manifest. Don't add to bytes_this_run (it was counted on the
                # original run that wrote .fetch_state.json).
                size = out_path.stat().st_size
                sha = manifest.sha256_file(out_path)
            else:
                if bytes_this_run >= max_bytes:
                    logger.info(
                        f"[fetch/inside_airbnb] byte cap reached "
                        f"({bytes_this_run:,} >= {max_bytes:,}); stopping"
                    )
                    break
                size, sha = _stream_to_disk(url, out_path)
                if size > _PER_RESOURCE_MAX_BYTES:
                    logger.info(
                        f"[fetch/inside_airbnb] {url} exceeded per-resource cap "
                        f"({size:,} > {_PER_RESOURCE_MAX_BYTES:,}); discarding"
                    )
                    out_path.unlink(missing_ok=True)
                    n_skipped += 1
                    continue
                bytes_this_run += size
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.info(f"[fetch/inside_airbnb] download failed: {url} ({exc!r})")
            n_skipped += 1
            continue

        if sha in known_hashes:
            # Already in the manifest from a previous run; nothing to append.
            n_skipped += 1
            bar.update(1)
            continue
        known_hashes.add(sha)

        rows.append(
            manifest.ManifestRow(
                origin="inside_airbnb",
                url=url,
                sha256=sha,
                bytes=size,
                source=f"inside_airbnb:{_city_id(url)}",
                picked_reason="inside_airbnb:" + ("listings" if url.endswith("listings.csv.gz") else "reviews"),
                fetched_at=manifest.now_iso(),
                local_path=str(out_path.resolve()),
            )
        )
        n_kept += 1
        bar.update(1)
        bar.set_postfix(MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped)

        if len(rows) % 25 == 0:
            manifest.append_rows(out_dir, rows)
            manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
            rows.clear()

        if bytes_this_run >= max_bytes:
            logger.info(
                f"[fetch/inside_airbnb] byte cap reached ({bytes_this_run:,}); stopping"
            )
            break

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    logger.info(
        f"[fetch/inside_airbnb] done: kept={n_kept}, skipped={n_skipped}, "
        f"bytes_this_run={bytes_this_run:,}"
    )
    return 0
