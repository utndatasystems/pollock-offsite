"""Survey CLI dispatcher.

Subcommands map 1:1 to submodule entry points so each can be invoked or
tested in isolation:

    python -m survey fetch    --source data.gov --max-files 2500
    python -m survey fetch    --source-dir /data/local_csvs --max-files 5000
    python -m survey annotate --in survey/out/raw --jobs 16
    python -m survey triage   --threshold 0.30 --budget-usd 200
    python -m survey discover --sample 250 --budget-usd 50
    python -m survey score    --gold-dir survey/out/gold
    python -m survey report   --out survey/out/reports

Phase P1 wires the argparse surface and calls into NotImplementedError
stubs so later phases can fill them in without touching this file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config


def _human_bytes(s: str) -> int:
    """Parse ``50G``, ``500M``, ``2K``, or a raw integer into bytes."""
    s = s.strip()
    if not s:
        raise argparse.ArgumentTypeError("empty byte spec")
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    last = s[-1].upper()
    if last in units:
        return int(float(s[:-1]) * units[last])
    return int(s)


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--out-dir",
        type=Path,
        default=config.DEFAULT_OUT_DIR,
        help="Survey output root (default: survey/out).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=config.RAND_SEED,
        help="Random seed for sampling and shuffling.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="survey",
        description="Pollock CSV-pollution survey pipeline.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # fetch ----------------------------------------------------------------
    p_fetch = sub.add_parser("fetch", help="Assemble a corpus.")
    src = p_fetch.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--source",
        choices=["data.gov", "data.gov.uk", "hf", "kaggle", "inside_airbnb", "data.europa.eu"],
    )
    src.add_argument(
        "--source-dir",
        type=Path,
        help="Local directory of CSV files (no network).",
    )
    p_fetch.add_argument("--max-files", type=int, default=None)
    p_fetch.add_argument(
        "--max-bytes", type=_human_bytes, default=config.DEFAULT_MAX_BYTES
    )
    p_fetch.add_argument(
        "--datagov-query",
        default="csv",
        help="Search query passed to catalog.data.gov (default: 'csv').",
    )
    p_fetch.add_argument(
        "--datagov-skip-pages",
        type=int,
        default=0,
        help=(
            "data.gov only: fast-forward past N search pages before "
            "downloading. Use this once to recover from a previous run that "
            "exited before cursor persistence was wired up. "
            "(20 datasets per page; ignored when a persisted cursor is found.)"
        ),
    )
    p_fetch.add_argument("--dry-run", action="store_true")
    _add_common(p_fetch)

    # annotate -------------------------------------------------------------
    p_ann = sub.add_parser("annotate", help="Run Tier 1 detectors.")
    p_ann.add_argument(
        "--in",
        dest="in_dir",
        type=Path,
        default=None,
        help="Directory of CSV files. Defaults to <out-dir>/raw.",
    )
    p_ann.add_argument("--jobs", type=int, default=4)
    p_ann.add_argument(
        "--force",
        action="store_true",
        help="Re-annotate even when an up-to-date _parameters.json exists.",
    )
    p_ann.add_argument(
        "--preserve-existing",
        action="store_true",
        help=(
            "Keep curated dialect fields in pre-existing _parameters.json "
            "and only fill the new annotation block."
        ),
    )
    _add_common(p_ann)

    # scan -----------------------------------------------------------------
    p_scan = sub.add_parser(
        "scan",
        help="Stripped-down per-defect line-level scanner (subset of annotate).",
    )
    p_scan.add_argument(
        "--in",
        dest="in_dir",
        type=Path,
        required=True,
        help="Directory of CSV files to scan.",
    )
    p_scan.add_argument("--jobs", type=int, default=1)
    p_scan.add_argument(
        "--long-field-chars",
        type=int,
        default=2048,
        help="Threshold (chars) for the extremely-long-field detector.",
    )
    p_scan.add_argument(
        "--max-bytes",
        type=_human_bytes,
        default=50 * 1024 * 1024,
        help=(
            "Cap on uncompressed bytes read for the encoding-issues "
            "byte-scan (default 50M). Distinct from `fetch --max-bytes` "
            "(which is a corpus-wide budget); this cap is per-file and "
            "intentionally smaller because the parser already operates on "
            "a head/tail sample for files past survey.config "
            "SAMPLE_BYTES_THRESHOLD (5 MB)."
        ),
    )
    p_scan.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing scan output.",
    )
    p_scan.add_argument(
        "--no-sampling",
        action="store_true",
        help=(
            "Disable head/tail sampling for files larger than the parser's "
            "SAMPLE_BYTES_THRESHOLD (5 MB). Default is to sample, which is "
            "fast but makes line numbers in the tail half of large files "
            "unreliable. Use this flag for accurate line numbers at the "
            "cost of full-file scans."
        ),
    )
    p_scan.add_argument(
        "--dataset-prefix",
        type=str,
        default=None,
        help="Prefix for paths in output JSON. Defaults to --in directory name.",
    )
    _add_common(p_scan)

    # triage ---------------------------------------------------------------
    p_tri = sub.add_parser("triage", help="Run Tier 2 LLM triage.")
    p_tri.add_argument(
        "--threshold",
        type=float,
        default=config.DEFAULT_AMBIGUITY_THRESHOLD,
    )
    p_tri.add_argument("--model", default=config.DEFAULT_TRIAGE_MODEL)
    p_tri.add_argument(
        "--escalation-model",
        default=config.DEFAULT_TRIAGE_ESCALATION_MODEL,
        help=(
            "Model to retry with when the primary model self-reports low "
            "confidence. Set to the same value as --model to disable escalation."
        ),
    )
    p_tri.add_argument(
        "--budget-usd", type=float, default=config.DEFAULT_BUDGET_USD
    )
    p_tri.add_argument(
        "--backend",
        choices=["auto", "anthropic", "sf-claude"],
        default="auto",
        help=(
            "LLM backend. 'auto' picks 'anthropic' when ANTHROPIC_API_KEY is "
            "set, else 'sf-claude' when the wrapper is on PATH."
        ),
    )
    p_tri.add_argument(
        "--effort",
        default="medium",
        help="Reasoning effort passed to the sf-claude wrapper (default: medium).",
    )
    _add_common(p_tri)

    # discover -------------------------------------------------------------
    p_dis = sub.add_parser("discover", help="Run Tier 3 LLM discovery pass.")
    p_dis.add_argument(
        "--sample", type=int, default=config.DEFAULT_DISCOVER_SAMPLE
    )
    p_dis.add_argument("--model", default=config.DEFAULT_DISCOVERY_MODEL)
    p_dis.add_argument("--budget-usd", type=float, default=50.0)
    p_dis.add_argument(
        "--backend",
        choices=["auto", "anthropic", "sf-claude"],
        default="auto",
    )
    p_dis.add_argument(
        "--effort",
        default="medium",
        help="Reasoning effort passed to the sf-claude wrapper (default: medium).",
    )
    p_dis.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of files to process in parallel (default: 1).",
    )
    _add_common(p_dis)

    # score ----------------------------------------------------------------
    p_sc = sub.add_parser("score", help="Score Tier 1/2 against gold.")
    p_sc.add_argument(
        "--gold-dir", type=Path, default=config.DEFAULT_OUT_DIR / "gold"
    )
    _add_common(p_sc)

    # report ---------------------------------------------------------------
    p_rep = sub.add_parser("report", help="Emit aggregate reports.")
    p_rep.add_argument(
        "--out", type=Path, default=config.DEFAULT_OUT_DIR / "reports"
    )
    _add_common(p_rep)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Lazy imports so unimplemented submodules don't break unrelated subcommands.
    if args.cmd == "fetch":
        from .fetch import run_fetch

        return run_fetch(args)
    if args.cmd == "annotate":
        from .detect import run_annotate

        return run_annotate(args)
    if args.cmd == "scan":
        from .scan import run_scan

        return run_scan(args)
    if args.cmd == "triage":
        from .triage import run_triage

        return run_triage(args)
    if args.cmd == "discover":
        from .triage import run_discover

        return run_discover(args)
    if args.cmd == "score":
        from .eval import run_score

        return run_score(args)
    if args.cmd == "report":
        from .eval import run_report

        return run_report(args)

    parser.error(f"unknown subcommand: {args.cmd}")
    return 2
