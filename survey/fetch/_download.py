"""Single-candidate download primitive and the shared download loop.

``fetch_one`` is a pure function: given a ``Candidate`` and an ``exclusive_stage``
callable that reserves an O_EXCL path + open handle, it streams the body to disk
under ``opts.per_file_cap_bytes``, validates the result via ``_filters``, and
returns ``Success`` or ``Failure``. No global state, safe to call from a thread
pool.

``download_loop`` runs candidates through a single ``ThreadPoolExecutor``
(reused across pages, per the BLOCKER fix in the plan), enforces ``max_files``
and ``max_bytes``, dedupes by sha256 via the cached ``manifest.load_known_hashes``,
and writes manifest rows + bytes-used via the supplied ``ManifestWriter``.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Callable, Iterable, Iterator, Union

from . import _filters, _http, manifest
from ._log import get_logger
from .config import FetchOptions
from .manifest import ManifestRow, ManifestWriter

logger = get_logger("survey.fetch._download")


@dataclass
class Candidate:
    url: str
    origin: str
    picked_reason: str
    size_hint: int | None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Success:
    body_path: Path
    sha: str
    bytes: int
    content_type: str


@dataclass(frozen=True)
class Failure:
    reason: str


DownloadResult = Union[Success, Failure]


@dataclass(frozen=True)
class FetchSummary:
    n_seen: int
    n_kept: int
    n_skipped: int
    bytes_this_run: int


# Callable that reserves an exclusive on-disk staging slot for ``(origin, url)``.
# Backends pass a partial that wraps ``storage.stage_path(origin, url, root)``
# so this module stays ignorant of ``FetchOptions.data_root`` resolution.
ExclusiveStage = Callable[[str, str], "tuple[Path, BinaryIO]"]


def fetch_one(
    cand: Candidate,
    *,
    opts: FetchOptions,
    exclusive_stage: ExclusiveStage,
) -> DownloadResult:
    """Download one candidate, validate, and return Success/Failure.

    HEAD-checks only when the candidate has no size hint. The per-file cap is
    enforced *during* the stream by ``_http.stream_to_file``, not after — see
    the security note in the plan. On a CSV-shape failure the staged file is
    unlinked so the next run isn't tempted to retry it.
    """
    if cand.size_hint is None:
        size = _http.head_size(cand.url, timeout=opts.head_timeout_s)
        if size is not None and size > opts.per_file_cap_bytes:
            return Failure("too_large")

    try:
        body_path, fh = exclusive_stage(cand.origin, cand.url)
    except OSError as e:
        return Failure(f"stage_error:{e.__class__.__name__}")

    content_type = ""
    try:
        with fh:
            n_bytes, sha = _http.stream_to_file(
                cand.url,
                fh,
                max_bytes=opts.per_file_cap_bytes,
                timeout=opts.request_timeout_s,
            )
        # Re-open just enough to sniff the prefix for the CSV filter; we don't
        # have the content-type from stream_to_file, so we pass empty string
        # and rely on the body-magic checks in ``looks_like_csv``.
        with open(body_path, "rb") as f:
            head = f.read(2048)
        if not _filters.looks_like_csv(head, content_type):
            try:
                body_path.unlink()
            except OSError:
                pass
            return Failure("not_csv")
        return Success(
            body_path=body_path, sha=sha, bytes=n_bytes, content_type=content_type
        )
    except _http.HTTP_ERRORS as e:
        try:
            body_path.unlink()
        except (OSError, FileNotFoundError):
            pass
        return Failure(f"http_error:{e.__class__.__name__}")


def download_loop(
    candidates: Iterable[Candidate],
    *,
    opts: FetchOptions,
    mw: ManifestWriter,
    exclusive_stage: ExclusiveStage,
    on_cap_hit: Callable[[Candidate | None], None] | None = None,
) -> FetchSummary:
    """Drive ``candidates`` through a shared thread pool, writing manifest rows.

    A single ``ThreadPoolExecutor`` is allocated for the full iterator (the
    plan calls out per-page pool churn as a regression in the legacy backends).
    Up to ``concurrency * 2`` futures are kept in flight; we consume them with
    a sliding window so memory stays bounded for large catalogs.

    On ``max_files`` / ``max_bytes`` cap hit, ``on_cap_hit`` is called with the
    last candidate the iterator produced (or ``None`` if the cap fired before
    any candidate was emitted) so the caller can persist its cursor.
    """
    cands_iter: Iterator[Candidate] = iter(candidates)
    known_hashes = manifest.load_known_hashes(opts.out_dir)
    bytes_budget_remaining = max(0, opts.max_bytes - mw.bytes_added)

    n_seen = 0
    n_kept = 0
    n_skipped = 0
    bytes_this_run = 0
    last_cand: Candidate | None = None
    cap_hit = False

    def submit_next(ex: ThreadPoolExecutor) -> Future | None:
        nonlocal last_cand
        try:
            cand = next(cands_iter)
        except StopIteration:
            return None
        last_cand = cand
        fut = ex.submit(fetch_one, cand, opts=opts, exclusive_stage=exclusive_stage)
        # Stash the candidate on the future for result handling.
        fut.candidate = cand  # type: ignore[attr-defined]
        return fut

    with ThreadPoolExecutor(max_workers=opts.concurrency) as ex:
        in_flight: list[Future] = []
        target = max(1, opts.concurrency * 2)

        # Prime the window.
        while len(in_flight) < target:
            fut = submit_next(ex)
            if fut is None:
                break
            in_flight.append(fut)

        while in_flight:
            # Drain the head; preserve order for stable cursor semantics.
            fut = in_flight.pop(0)
            cand: Candidate = fut.candidate  # type: ignore[attr-defined]
            n_seen += 1
            try:
                result = fut.result()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("worker raised %s on %s", e.__class__.__name__, cand.url)
                result = Failure(f"worker_error:{e.__class__.__name__}")

            if isinstance(result, Failure):
                n_skipped += 1
                logger.debug("skip %s: %s", cand.url, result.reason)
            else:
                if result.sha in known_hashes:
                    # Duplicate of an already-manifested file — drop the staged copy.
                    try:
                        result.body_path.unlink()
                    except OSError:
                        pass
                    n_skipped += 1
                else:
                    if result.bytes > bytes_budget_remaining:
                        try:
                            result.body_path.unlink()
                        except OSError:
                            pass
                        cap_hit = True
                    else:
                        row = ManifestRow(
                            origin=cand.origin,
                            url=cand.url,
                            sha256=result.sha,
                            bytes=result.bytes,
                            source=cand.extra.get("source", cand.origin),
                            picked_reason=cand.picked_reason,
                            fetched_at=manifest.now_iso(),
                            local_path=str(result.body_path),
                        )
                        mw.add(row)
                        mw.note_bytes(result.bytes)
                        known_hashes.add(result.sha)
                        bytes_budget_remaining -= result.bytes
                        bytes_this_run += result.bytes
                        n_kept += 1
                        if (
                            opts.max_files is not None
                            and n_kept >= opts.max_files
                        ):
                            cap_hit = True

            if cap_hit:
                # Drain in-flight futures so threads exit cleanly, but stop
                # submitting new work and don't credit late successes.
                for pending in in_flight:
                    pending.cancel()
                for pending in in_flight:
                    try:
                        pending.result()
                    except Exception:
                        pass
                in_flight.clear()
                break

            # Refill the window.
            new_fut = submit_next(ex)
            if new_fut is not None:
                in_flight.append(new_fut)

    if cap_hit and on_cap_hit is not None:
        on_cap_hit(last_cand)

    return FetchSummary(
        n_seen=n_seen,
        n_kept=n_kept,
        n_skipped=n_skipped,
        bytes_this_run=bytes_this_run,
    )
