"""``Backend`` Protocol shared by every fetch backend module.

Using ``Protocol`` (rather than an ABC) means each backend is just a module
with four module-level attributes — no class boilerplate, no MRO surprises.
The ``BACKENDS`` registry in ``survey/fetch/__init__.py`` maps backend names
to those modules.

``add_common_args`` gives every backend's argparse subparser the shared flag
surface. ``run_paginated`` is the thin glue every paginated backend wraps
around its ``paginate(...)`` iterator: it wires up ``State`` /
``ManifestWriter`` / ``download_loop`` and writes the per-run summary log.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Callable, Iterator, Protocol, runtime_checkable

from .._units import human_bytes as _human_bytes
from . import storage
from ._download import Candidate, download_loop
from ._state import State
from .config import BackendOptions, FetchOptions
from .manifest import ManifestWriter


@runtime_checkable
class Backend(Protocol):
    name: str

    def add_subparser(self, sp: argparse._SubParsersAction) -> argparse.ArgumentParser: ...

    def options_from_args(self, args: argparse.Namespace) -> BackendOptions: ...

    def run(self, opts: BackendOptions) -> int: ...


def add_common_args(p: argparse.ArgumentParser) -> None:
    """Attach the shared flag surface to ``p``.

    Defaults are intentionally explicit so a `--help` listing reflects what
    the backend will do without further configuration.
    """
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--max-files", type=int, default=None)
    p.add_argument(
        "--max-bytes",
        type=_human_bytes,
        default=50 * 1024 * 1024 * 1024,
        help="Cap on bytes downloaded this run (e.g. 50G, 500M).",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument(
        "--per-file-cap-bytes",
        type=_human_bytes,
        default=200 * 1024 * 1024,
        help="Reject downloads whose body exceeds this size (default 200M).",
    )
    p.add_argument("--user-agent", default=None)
    p.add_argument(
        "--head-timeout-s",
        type=int,
        default=5,
        help="HEAD request timeout in seconds (default 5).",
    )
    p.add_argument(
        "--request-timeout-s",
        type=int,
        default=60,
        help="GET request timeout in seconds (default 60).",
    )
    p.add_argument(
        "--allow-http",
        action="store_true",
        help="Permit plain http:// downloads (default: https-only).",
    )
    p.add_argument(
        "--compress",
        choices=("none", "gzip", "zstd"),
        default="none",
        help=(
            "Compress uncompressed CSV downloads to disk (default: none). "
            "Already-compressed downloads (.csv.gz, .csv.zst) are stored "
            "verbatim regardless. Currently parsed but not yet wired into "
            "the streaming download path."
        ),
    )
    verbosity = p.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Reduce log output to WARNING and above.",
    )
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level log output.",
    )


def run_paginated(
    base: FetchOptions,
    *,
    source: str,
    candidates_factory: Callable[[FetchOptions, State, bool], Iterator[Candidate]],
    logger: logging.Logger,
) -> int:
    """Run a paginated backend end-to-end given a candidates factory.

    Resolves ``out_dir``/``state``, builds the candidate iterator, and either
    runs the dry-run preview loop or drives ``download_loop`` and writes the
    summary line. Backends collapse to constructing the factory + delegating.
    """
    out_dir: Path = Path(base.out_dir).resolve()
    state = State(out_dir)
    candidates = candidates_factory(base, state, base.dry_run)

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

    with ManifestWriter(out_dir, state) as mw:
        summary = download_loop(
            candidates,
            opts=base,
            mw=mw,
            exclusive_stage=_stage,
            on_cap_hit=lambda _last: None,
        )

    logger.info(
        f"{source}: seen={summary.n_seen}, kept={summary.n_kept}, "
        f"skipped={summary.n_skipped}, bytes_this_run={summary.bytes_this_run:,}"
    )
    return 0
