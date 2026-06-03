"""``Backend`` Protocol shared by every fetch backend module.

Using ``Protocol`` (rather than an ABC) means each backend is just a module
with four module-level attributes — no class boilerplate, no MRO surprises.
The Phase 5 / 6 rewrites populate ``BACKENDS`` in ``survey/fetch/__init__.py``
with the modules themselves.

``add_common_args`` gives every backend's argparse subparser the shared flag
surface (``--out-dir`` / ``--max-files`` / ``--max-bytes`` / ``--dry-run`` /
``--concurrency`` / ``--per-file-cap-bytes`` / ``--user-agent``). Phase 7 owns
the top-level fetch CLI; Phase 5 only needs the helper to be callable so the
backend modules can register subparsers.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Protocol, runtime_checkable

from .config import BackendOptions


@runtime_checkable
class Backend(Protocol):
    name: str

    def add_subparser(self, sp: argparse._SubParsersAction) -> argparse.ArgumentParser: ...

    def options_from_args(self, args: argparse.Namespace) -> BackendOptions: ...

    def run(self, opts: BackendOptions) -> int: ...


def _human_bytes(s: str) -> int:
    """Parse ``50G`` / ``500M`` / ``2K`` / raw int into bytes. Mirrors ``survey/cli.py``."""
    s = s.strip()
    if not s:
        raise argparse.ArgumentTypeError("empty byte spec")
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    last = s[-1].upper()
    if last in units:
        return int(float(s[:-1]) * units[last])
    return int(s)


def add_common_args(p: argparse.ArgumentParser) -> None:
    """Attach the shared flag surface to ``p``.

    Phase 7's fetch CLI calls this on every backend subparser so flags stay in
    sync. Defaults are intentionally low so a `--help` listing is honest about
    what the backend will do without further configuration.
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
