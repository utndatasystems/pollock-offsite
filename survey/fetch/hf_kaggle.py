"""HuggingFace Datasets + Kaggle fetch backends.

HuggingFace works without credentials for public datasets. Kaggle requires
``KAGGLE_USERNAME``/``KAGGLE_KEY`` env vars and the ``kaggle`` CLI; we
soft-fail with a clear log message if either is missing.

Dispatch from ``survey/fetch/__init__.py``: ``args.source ∈ {"hf",
"kaggle"}``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from tqdm.auto import tqdm

from . import manifest, storage
from ._log import get_logger

logger = get_logger("hf_kaggle")


_USER_AGENT = "pollock-survey/0.1"
_PER_RESOURCE_MAX_BYTES = 200 * 1024 * 1024
_HF_LIST_URL = "https://huggingface.co/api/datasets"
_HF_TREE_URL = "https://huggingface.co/api/datasets/{repo}/tree/main"
_HF_RESOLVE_URL = "https://huggingface.co/datasets/{repo}/resolve/main/{path}"


def run_hf_kaggle(args) -> int:
    if args.source == "hf":
        return _run_hf(args)
    if args.source == "kaggle":
        return _run_kaggle(args)
    logger.info(f"[fetch/hf_kaggle] unknown source: {args.source}")
    return 1


# --- HuggingFace ----------------------------------------------------------


def _http_get(url: str, *, timeout: int = 30) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), (resp.headers.get("Content-Type") or "").lower()


def _hf_search(query: str, limit: int) -> list[dict]:
    from urllib.parse import urlencode

    url = f"{_HF_LIST_URL}?{urlencode({'search': query, 'limit': limit, 'filter': 'tabular'})}"
    try:
        body, _ = _http_get(url)
        return json.loads(body)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.info(f"[fetch/hf] search failed: {exc!r}")
        return []


def _hf_list_csv_files(repo: str) -> list[dict]:
    """List ``*.csv`` files in the dataset's main branch."""
    url = _HF_TREE_URL.format(repo=repo)
    try:
        body, _ = _http_get(url)
        items = json.loads(body)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return []
    return [
        x for x in items
        if x.get("type") == "file" and (x.get("path") or "").lower().endswith(".csv")
    ]


def _run_hf(args) -> int:
    out_dir: Path = Path(args.out_dir).resolve()
    max_files = args.max_files
    max_bytes = args.max_bytes

    queries = ("csv", "tabular", "table", "spreadsheet", "dataset")
    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    rows: list[manifest.ManifestRow] = []
    seen_repos: set[str] = set()
    n_kept = n_skipped = 0
    bar = tqdm(
        total=max_files,
        desc="fetch hf",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    for q in queries:
        if max_files is not None and n_kept >= max_files:
            break
        logger.info(f"[fetch/hf] search {q!r}")
        for ds in _hf_search(q, limit=200):
            if max_files is not None and n_kept >= max_files:
                break
            repo = ds.get("id")
            if not repo or repo in seen_repos:
                continue
            seen_repos.add(repo)

            files = _hf_list_csv_files(repo)
            if not files:
                continue
            # Take just the first CSV per dataset for diversity.
            file_meta = files[0]
            path = file_meta["path"]
            from urllib.parse import quote
            url = _HF_RESOLVE_URL.format(repo=repo, path=quote(path))

            if args.dry_run:
                logger.info(f"[dry-run] hf {repo}/{path}")
                n_kept += 1
                bar.update(1)
                continue

            try:
                body, ct = _http_get(url, timeout=120)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                logger.info(f"[fetch/hf] download failed: {url} ({exc!r})")
                n_skipped += 1
                continue
            if "text/html" in ct or len(body) == 0:
                n_skipped += 1
                continue
            if len(body) > _PER_RESOURCE_MAX_BYTES:
                n_skipped += 1
                continue

            if bytes_this_run + len(body) > max_bytes:
                logger.info("[fetch/hf] byte cap reached; stopping")
                break
            sha = hashlib.sha256(body).hexdigest()
            staged = storage.stage_path("hf", url)
            with open(staged, "wb") as f:
                f.write(body)
            bytes_this_run += len(body)
            n_kept += 1
            bar.update(1)
            bar.set_postfix(MB=f"{bytes_this_run/1024/1024:.1f}", skipped=n_skipped)

            rows.append(
                manifest.ManifestRow(
                    origin="hf",
                    url=url,
                    sha256=sha,
                    bytes=len(body),
                    source="hf",
                    picked_reason=f"hf:{repo}",
                    fetched_at=manifest.now_iso(),
                    local_path=str(staged.resolve()),
                )
            )
            if len(rows) % 25 == 0:
                manifest.append_rows(out_dir, rows)
                manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
                rows.clear()

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    logger.info(f"[fetch/hf] done: kept={n_kept}, skipped={n_skipped}, bytes_this_run={bytes_this_run:,}")
    return 0


# --- Kaggle ---------------------------------------------------------------


def _kaggle_authed() -> bool:
    if not shutil.which("kaggle"):
        return False
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    cred = Path.home() / ".kaggle" / "kaggle.json"
    return cred.exists()


def _run_kaggle(args) -> int:
    if not _kaggle_authed():
        logger.info(
            "[fetch/kaggle] kaggle CLI not authenticated "
            "(needs KAGGLE_USERNAME+KAGGLE_KEY or ~/.kaggle/kaggle.json); skipping"
        )
        return 1

    # Minimal real implementation: list top-voted CSV-bearing datasets, fetch
    # one CSV per dataset. We rely on ``kaggle datasets list`` JSON output.
    out_dir: Path = Path(args.out_dir).resolve()
    max_files = args.max_files or 50
    # Per-run byte ledger: --max-bytes caps just this invocation's downloads.
    bytes_at_start = manifest.load_bytes_used(out_dir)
    bytes_this_run = 0
    rows: list[manifest.ManifestRow] = []
    n_kept = 0

    try:
        r = subprocess.run(
            ["kaggle", "datasets", "list", "--file-type", "csv",
             "--sort-by", "votes", "-v"],
            capture_output=True, check=True, text=True, timeout=60,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.info(f"[fetch/kaggle] kaggle CLI failed: {exc!r}")
        return 1

    # ``-v`` (verbose) emits CSV; first column is the dataset ref.
    refs: list[str] = []
    for line in r.stdout.splitlines()[1:]:
        cols = line.split(",")
        if cols and cols[0]:
            refs.append(cols[0])
    refs = refs[:max_files]
    logger.info(f"[fetch/kaggle] {len(refs)} candidate datasets")

    if args.dry_run:
        for ref in refs[:20]:
            logger.info(f"[dry-run] kaggle {ref}")
        return 0

    work_dir = out_dir / "raw" / "_kaggle_tmp"
    work_dir.mkdir(parents=True, exist_ok=True)
    bar = tqdm(
        total=len(refs),
        desc="fetch kaggle",
        unit="file",
        dynamic_ncols=True,
        leave=False,
    )

    for ref in refs:
        if n_kept >= max_files:
            break
        try:
            subprocess.run(
                ["kaggle", "datasets", "download", "-p", str(work_dir), "--unzip", ref],
                capture_output=True, check=True, timeout=300,
            )
        except (subprocess.SubprocessError, OSError):
            continue
        # Pick the largest CSV in the unzipped output.
        csvs = sorted(work_dir.rglob("*.csv"), key=lambda p: p.stat().st_size, reverse=True)
        if not csvs:
            for p in work_dir.iterdir():
                if p.is_file():
                    p.unlink()
            continue
        chosen = csvs[0]
        with open(chosen, "rb") as f:
            body = f.read()
        sha = hashlib.sha256(body).hexdigest()
        # Cleanup the staging dir (next iteration starts fresh).
        for p in work_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        if bytes_this_run + len(body) > args.max_bytes:
            continue
        bytes_this_run += len(body)
        n_kept += 1
        bar.update(1)
        bar.set_postfix(MB=f"{bytes_this_run/1024/1024:.1f}")

        kaggle_url = f"https://www.kaggle.com/datasets/{ref}/{chosen.name}"
        staged = storage.stage_path("kaggle", kaggle_url)
        with open(staged, "wb") as f:
            f.write(body)
        rows.append(
            manifest.ManifestRow(
                origin="kaggle",
                url=f"https://www.kaggle.com/datasets/{ref}",
                sha256=sha,
                bytes=len(body),
                source="kaggle",
                picked_reason=f"kaggle:{ref}",
                fetched_at=manifest.now_iso(),
                local_path=str(staged.resolve()),
            )
        )

    bar.close()
    manifest.append_rows(out_dir, rows)
    manifest.save_bytes_used(out_dir, bytes_at_start + bytes_this_run)
    shutil.rmtree(work_dir, ignore_errors=True)
    logger.info(f"[fetch/kaggle] done: kept={n_kept}, bytes_this_run={bytes_this_run:,}")
    return 0
