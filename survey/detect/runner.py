"""Tier 1 orchestrator.

Reads CSV files from ``--in``, runs every detector, writes one
``<original_name>_parameters.json`` next to ``<out-dir>/parameters/``.

Reuses:
- ``pollock/CSVFile.py:131-139`` encoding-fallback (via parser.py).
- ``pollock/data_types.parse_cell`` (via columns.py).
- ``sut/utils.print`` for timestamped logging.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from joblib import Parallel, delayed

from sut.utils import print as ts_print

from ..config import (
    ALL_ANNOTATION_FIELDS,
    DEFAULT_OUT_DIR,
    POLLOCK_ORIGINAL_FLAGS,
    NEW_CANDIDATE_FLAGS,
    SCALAR_ANNOTATION_FIELDS,
    SCHEMA_VERSION,
)
from . import cells, columns, dialect, file_level, format_check, io_utils, structure
from .parser import (
    ParsedSample,
    parse_csv_sample,
    vote_escape_char,
    vote_field_delimiter,
    vote_quote_char,
    vote_record_delimiter,
)


CSV_GLOBS = (
    "*.csv",
    "*.CSV",
    "*.tsv",
    "*.TSV",
    "*.csv.zstd",
    "*.CSV.zstd",
    "*.tsv.zstd",
    "*.TSV.zstd",
    "*.csv.zst",
    "*.CSV.zst",
    "*.tsv.zst",
    "*.TSV.zst",
    "*.csv.gz",
    "*.CSV.gz",
    "*.tsv.gz",
    "*.TSV.gz",
    "*.csv.gzip",
    "*.tsv.gzip",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _annotate_one(path: Path, *, preserve_existing: bool, out_dir: Path) -> dict:
    """Run all Tier 1 detectors on one file, return the schema-v2 dict.

    Wrapped in a broad try/except: a single bad file must never bring the
    survey to a halt. On error we still emit a record with the failure noted
    in ``tier_provenance``.
    """
    record: dict = {
        "schema_version": SCHEMA_VERSION,
        "source_meta": {
            "origin": "local",
            "url": f"file://{path.resolve()}",
            "sha256": None,
            "bytes": os.path.getsize(path),
            "fetched_at": None,
        },
        "tier_provenance": {
            "tier1": _now_iso(),
            "tier2_model": None,
            "tier2_at": None,
        },
    }
    non_csv = format_check.detect_non_csv_format(path)
    if non_csv is not None:
        record["tier_provenance"]["tier1_error"] = f"non-csv format detected: {non_csv}"
        record.update(_empty_schema(path))
        return record
    try:
        sample = parse_csv_sample(path)
    except Exception as exc:  # noqa: BLE001
        record["tier_provenance"]["tier1_error"] = repr(exc)
        record.update(_empty_schema(path))
        return record

    record.update(_emit_schema(sample, path))
    return record


def _empty_schema(path: Path) -> dict:
    """Schema for a file we couldn't parse at all."""
    annotations = {f: False for f in POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS}
    annotations.update(
        {"dimension": "0x0", "encoding_flag": "unknown", "jagged_rows_count": 0}
    )
    return {
        "encoding": "unknown",
        "encoding_confidence": 0.0,
        "delimiter": "",
        "quotechar": "",
        "escapechar": "",
        "row_delimiter": "\r\n",
        "header_lines": "0",
        "preamble_lines": "0",
        "footnote_lines": "0",
        "column_names": [],
        "n_columns": 0,
        "annotations": annotations,
        "confidences": {},
        "ambiguity_score": 1.0,
    }


def _emit_schema(sample: ParsedSample, path: Path) -> dict:
    """Run every detector and assemble the schema-v2 fields."""
    n_rows, n_cols = structure.n_rows_cols(sample)

    field_delim = vote_field_delimiter(sample)
    quote_char = vote_quote_char(sample)
    escape_char = vote_escape_char(sample)
    record_delim = vote_record_delimiter(sample)

    header_count, header_conf = structure.header_lines(sample)
    preamble_count, preamble_conf = structure.preamble_lines(sample)
    footnote_count, footnote_conf = structure.footnote_lines(sample)

    col_names = columns.column_names(sample, header_count)

    enc_name, enc_conf = file_level.encoding_flag(sample)

    multitable, multitable_conf = structure.table_multiple_tables(sample)
    jagged, jagged_conf = structure.jagged_rows_count(sample)
    sniffer_low, sniffer_ratio = dialect.sniffer_low_confidence(sample)
    heterogeneous, heterogeneous_conf = columns.column_formats_heterogeneous(
        sample, header_count
    )
    row_inconsist = structure.row_inconsistencies(sample)

    # Filename-level detectors operate on the *logical* CSV name so that
    # ``foo.csv.zstd`` is treated the same as ``foo.csv``.
    logical_path = path.with_name(io_utils.logical_name(path))

    annotations: dict[str, object] = {
        # File-name flags
        "file_name_nonalnum": file_level.file_name_nonalnum(logical_path),
        "file_name_nonalnum_nounderscore": file_level.file_name_nonalnum_nounderscore(logical_path),
        # Table-shape flags
        "table_multiple_tables": multitable,
        "table_no_header": structure.table_no_header(header_count),
        "table_multirow_header": structure.table_multirow_header(header_count),
        "table_preamble_rows": structure.table_preamble_rows(preamble_count),
        "table_footnote_rows": structure.table_footnote_rows(footnote_count),
        "table_columns_less_than_2": structure.table_columns_less_than_2(n_cols),
        "table_columns_more_256": structure.table_columns_more_256(n_cols),
        "table_lines_less_2": structure.table_lines_less_2(n_rows),
        "table_lines_more_65k": structure.table_lines_more_65k(n_rows),
        # Dialect flags
        "table_not_crlf_delimiter": dialect.table_not_crlf_delimiter(sample, record_delim),
        "table_not_comma_delimiter": dialect.table_not_comma_delimiter(sample),
        "table_not_double_quote": dialect.table_not_double_quote(sample),
        "table_not_escape_quote": dialect.table_not_escape_quote(sample),
        # Row-consistency flags
        **row_inconsist,
        # Column header flags
        "column_header_unique": columns.column_header_unique(col_names),
        "column_header_non_alnum": columns.column_header_non_alnum(col_names),
        "column_header_empty": columns.column_header_empty(col_names),
        "column_header_long": columns.column_header_long(col_names),
        # Column type flags
        "column_formats_heterogeneous": heterogeneous,
        "column_string_boundary": columns.column_string_boundary(sample, header_count),
        "column_int_boundary": columns.column_int_boundary(sample, header_count),
        "column_date_boundary": columns.column_date_boundary(sample, header_count),
        # New candidates
        "bom_present": file_level.bom_present(sample),
        "has_comment_lines": structure.has_comment_lines(sample),
        "line_art_row_present": structure.line_art_row_present(sample),
        "locale_european_numbers": cells.locale_european_numbers(sample),
        "multiline_cell_present": cells.multiline_cell_present(sample),
        "missing_value_qualifier_diverse": cells.missing_value_qualifier_diverse(sample),
        "aggregated_row_present": structure.aggregated_row_present(sample),
        "units_in_values": cells.units_in_values(sample),
        "ambiguous_delimiter": dialect.ambiguous_delimiter(sample),
        "sniffer_low_confidence": sniffer_low,
        "leading_trailing_whitespace_in_header":
            columns.leading_trailing_whitespace_in_header(sample, header_count),
        "mixed_quote_styles": dialect.mixed_quote_styles(sample),
        "dialect_unparseable": dialect.dialect_unparseable(sample),
        # Scalars
        "dimension": file_level.dimension(sample, n_rows, n_cols),
        "encoding_flag": enc_name,
        "jagged_rows_count": jagged,
    }

    confidences = {
        "delimiter": sample.sniffer_confidence,
        "header_lines": header_conf,
        "preamble_lines": preamble_conf,
        "footnote_lines": footnote_conf,
        "encoding": enc_conf,
        "table_multiple_tables": multitable_conf,
        "jagged_rows_count": jagged_conf,
        "column_formats_heterogeneous": heterogeneous_conf,
        "sniffer_match_ratio": sniffer_ratio,
    }

    ambiguity = compute_ambiguity_score(annotations, confidences)

    out = {
        # Existing schema (backward compatible with sut/utils.load_parameters):
        "encoding": enc_name,
        "encoding_confidence": enc_conf,
        "delimiter": field_delim,
        "quotechar": quote_char,
        "escapechar": escape_char,
        "row_delimiter": record_delim,
        "header_lines": str(header_count),
        "preamble_lines": str(preamble_count),
        "footnote_lines": str(footnote_count),
        "column_names": col_names,
        "n_columns": n_cols,
        # New schema-v2 fields:
        "annotations": annotations,
        "confidences": {k: round(v, 3) for k, v in confidences.items()},
        "ambiguity_score": round(ambiguity, 3),
    }
    return out


def compute_ambiguity_score(
    annotations: dict[str, object], confidences: dict[str, float]
) -> float:
    """Composite score in [0, 1]; see plan §Tier 2."""
    score = 0.0
    if annotations.get("sniffer_low_confidence"):
        score += 0.25
    if annotations.get("ambiguous_delimiter"):
        score += 0.25
    if (
        annotations.get("jagged_rows_count", 0)
        and int(annotations.get("jagged_rows_count", 0)) > 0
        and not annotations.get("table_no_header", True)
    ):
        score += 0.20
    if annotations.get("table_multiple_tables"):
        score += 0.15
    if confidences and min(confidences.values()) < 0.6:
        score += 0.15
    return min(score, 1.0)


def _output_path(out_dir: Path, source_path: Path, in_dir: Path) -> Path:
    """Mirror the input subtree under ``out_dir``.

    For flat inputs (most datasets) this collapses to ``out_dir/<name>``,
    matching the historical layout so prior runs are not re-keyed. For
    nested inputs (Inside Airbnb: country/region/city/date/) this preserves
    the path so listings.csv.gz from different cities don't collide.
    """
    # Use the logical CSV name so foo.csv.zstd → foo.csv_parameters.json.
    logical = io_utils.logical_name(source_path)
    try:
        rel_parent = source_path.parent.relative_to(in_dir)
    except ValueError:
        rel_parent = Path(".")
    out_path = out_dir / rel_parent / f"{logical}_parameters.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def _list_csv_files(in_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in CSV_GLOBS:
        files.extend(sorted(in_dir.rglob(pattern)))
    # Dedup while preserving order.
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in files:
        if p in seen:
            continue
        seen.add(p)
        deduped.append(p)
    return deduped


def _is_up_to_date(out_path: Path) -> bool:
    if not out_path.exists():
        return False
    try:
        with open(out_path, "r") as f:
            data = json.load(f)
        return int(data.get("schema_version", 0)) == SCHEMA_VERSION
    except Exception:
        return False


def _merge_preserve_existing(existing: dict, fresh: dict) -> dict:
    """Keep curated dialect/header fields from ``existing``; overlay new annotation fields.

    Used for ``data/survey_sample/parameters/`` so the original Pollock
    paper's hand-curated values are never overwritten.
    """
    merged = dict(existing)
    for key in ("annotations", "confidences", "ambiguity_score",
                "schema_version", "source_meta", "tier_provenance"):
        if key in fresh:
            merged[key] = fresh[key]
    return merged


def _process(path: Path, out_dir: Path, in_dir: Path, force: bool, preserve_existing: bool) -> str:
    out_path = _output_path(out_dir, path, in_dir)
    if not force and _is_up_to_date(out_path):
        return f"skip {path.name}"
    record = _annotate_one(path, preserve_existing=preserve_existing, out_dir=out_dir)

    if preserve_existing and out_path.exists():
        try:
            with open(out_path, "r") as f:
                existing = json.load(f)
            record = _merge_preserve_existing(existing, record)
        except Exception:
            pass  # fall through, write fresh

    with open(out_path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=4)
    return f"ok   {path.name}"


def run_annotate(args) -> int:
    in_dir: Path = (args.in_dir or (Path(args.out_dir) / "raw")).resolve()
    out_dir: Path = (Path(args.out_dir) / "parameters").resolve()

    if not in_dir.is_dir():
        ts_print(f"[annotate] no input directory: {in_dir}")
        return 1

    files = _list_csv_files(in_dir)
    if not files:
        ts_print(f"[annotate] no CSV files under {in_dir}")
        return 0

    ts_print(f"[annotate] {len(files)} files -> {out_dir} (jobs={args.jobs})")
    t0 = time.time()

    from tqdm.auto import tqdm

    if args.jobs <= 1:
        results = [
            _process(p, out_dir, in_dir, args.force, args.preserve_existing)
            for p in tqdm(files, desc="annotate", unit="file", dynamic_ncols=True, leave=False)
        ]
    else:
        # joblib + tqdm: wrap the generator so each completed delayed() call
        # ticks the bar. ``return_as="generator"`` yields results as workers
        # finish, which is what tqdm needs to update incrementally.
        bar = tqdm(
            total=len(files),
            desc="annotate",
            unit="file",
            dynamic_ncols=True,
            leave=False,
        )
        results = []
        try:
            for r in Parallel(
                n_jobs=args.jobs,
                prefer="processes",
                return_as="generator_unordered",
            )(
                delayed(_process)(p, out_dir, in_dir, args.force, args.preserve_existing)
                for p in files
            ):
                results.append(r)
                bar.update(1)
        finally:
            bar.close()

    n_ok = sum(1 for r in results if r and r.startswith("ok"))
    n_skip = sum(1 for r in results if r and r.startswith("skip"))
    ts_print(f"[annotate] done: {n_ok} written, {n_skip} skipped in {time.time() - t0:.1f}s")
    return 0
