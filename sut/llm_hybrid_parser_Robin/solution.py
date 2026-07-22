import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from dialect import (
    _header_lines,
    _read_sample_lines,
    combine_header_rows,
    dialect_from_mappings,
    infer_dialect_with_llm,
    infer_expected_columns,
    sniff_with_clevercsv,
    sniff_with_duckdb,
)
from llm import configure_llm_cache, configure_llm_dry_run, configure_llm_verbose, get_llm_cache_stats
from loader import (
    _scan_rows_by_width,
    finalize_dataframe,
    find_width_rejects,
    infer_repairs_with_llm,
    load_clean_dataframe,
    load_with_duckdb,
    merge_rejects,
    rejects_to_malformed,
    splice_clean_rows,
    write_repaired_copy,
)


TRACE_VERSION = 1
SCORING_LINE_LIMIT = 250


class TraceWriter:
    def __init__(self, path: Optional[str], reset: bool = True):
        self.path = path
        if self.path and reset:
            sidecar_dir = os.path.dirname(self.path)
            if sidecar_dir:
                os.makedirs(sidecar_dir, exist_ok=True)
            with open(self.path, "w", encoding="utf-8"):
                pass

    def write(self, event_type: str, **payload: Any) -> None:
        if not self.path:
            return
        event = {
            "type": event_type,
            "trace_version": TRACE_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        event.update(payload)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str))
            f.write("\n")


def parse_csv_with_validation(
    csv_input: str,
    clean_csv: str = None,
    cheat: bool = False,
    llm_repair: bool = True,
    llm_dialect: bool = True,
    use_clevercsv: bool = False,
    use_duckdb_sniff: bool = False,
    sidecar_path: str = None,
    llm_context_lines: int = 10,
    reset_sidecar: bool = True,
    verbose: bool = False,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Load a polluted CSV using an optional non-LLM sniffer (CleverCSV or DuckDB) +
    optional LLM dialect inference, DuckDB reject tables, and optional LLM repairs
    for rejected lines.

    Returns:
        (DataFrame ready for benchmark output, original DuckDB reject summaries)
    """
    trace = TraceWriter(sidecar_path, reset=reset_sidecar)
    trace.write(
        "file_start",
        path=csv_input,
        clean_csv=clean_csv,
        cheat=cheat,
        llm_repair=llm_repair and not cheat,
        llm_dialect=llm_dialect,
        use_clevercsv=use_clevercsv,
        use_duckdb_sniff=use_duckdb_sniff,
        llm_context_lines=llm_context_lines,
    )

    # Non-LLM dialect sniffer: CleverCSV or DuckDB (mutually exclusive, both optional).
    sniff_mapping: Dict[str, Any] = {}
    sniffer_name = "clevercsv"
    sniffer_label = "CleverCSV"
    if use_clevercsv:
        sniff_mapping = sniff_with_clevercsv(csv_input)
        trace.write("clevercsv_dialect", dialect=sniff_mapping)
    elif use_duckdb_sniff:
        sniffer_name = "duckdb"
        sniffer_label = "DuckDB"
        sniff_mapping = sniff_with_duckdb(csv_input)
        trace.write("duckdb_dialect", dialect=sniff_mapping)

    llm_mapping: Dict[str, Any] = {}
    if llm_dialect:
        try:
            llm_mapping = infer_dialect_with_llm(
                csv_input,
                sniff_mapping,
                llm_context_lines,
                trace,
                sniffer_label,
            )
        except Exception as exc:
            trace.write("llm_dialect_error", error=str(exc))

    if verbose:
        print(f"llm mapping: {llm_mapping}")
    scoring_lines = _read_sample_lines(csv_input, SCORING_LINE_LIMIT)
    dialect = dialect_from_mappings(sniff_mapping, llm_mapping, scoring_lines, trace, sniffer_name)

    raw_header_lines = _header_lines(csv_input, dialect)
    header = combine_header_rows(raw_header_lines, dialect)
    has_header = dialect.header_rows > 0

    llm_columns = llm_mapping.get("column_names") if llm_mapping else None
    if isinstance(llm_columns, list) and llm_columns and all(isinstance(c, str) for c in llm_columns):
        header = [str(c) for c in llm_columns]
        has_header = True
        trace.write("llm_column_names_applied", columns=header)

    expected_columns = len(header) if has_header else infer_expected_columns(scoring_lines, dialect)
    if expected_columns == 0:
        trace.write("empty_or_unreadable_file")
        if cheat and clean_csv:
            clean_df = load_clean_dataframe(clean_csv)
            trace.write("cheat_result", clean_csv=clean_csv, malformed_count=0)
            return clean_df, []
        return pd.DataFrame(), []
    if not has_header:
        header = [f"_c{i}" for i in range(expected_columns)]

    trace.write(
        "schema_inference",
        has_header=has_header,
        header=header,
        expected_columns=expected_columns,
        skipped_rows=dialect.preamble_rows + dialect.header_rows,
    )

    try:
        df, duckdb_rejects, _ = load_with_duckdb(
            csv_input, dialect, expected_columns, trace, "initial"
        )
    except Exception as exc:
        if "CSV Parser state machine reached an invalid state" not in str(exc):
            raise
        trace.write("duckdb_non_strict_fallback", error=str(exc))
        df, duckdb_rejects, _ = load_with_duckdb(
            csv_input,
            dialect,
            expected_columns,
            trace,
            "initial_non_strict",
            strict_mode=False,
        )
    # Single width scan (reused below): good_rows doubles as an independent row count.
    good_rows, width_rejects = _scan_rows_by_width(csv_input, dialect, expected_columns)

    # Strict-mode silent drop: a skipped-but-strict-invalid header can make DuckDB return
    # 0 rows with 0 rejects and no error, because `skip` still tokenizes the header. If the
    # same-dialect line scan finds well-formed rows, reload with the header physically
    # stripped so the malformed header can't poison the data region.
    if len(df) == 0 and good_rows:
        trace.write("strict_mode_zero_rows_fallback", scanned_good_rows=len(good_rows))
        df, duckdb_rejects, _ = load_with_duckdb(
            csv_input,
            dialect,
            expected_columns,
            trace,
            "initial_stripped",
            strip_skipped=True,
        )

    if width_rejects:
        trace.write("local_width_validation_result", stage="initial", reject_errors=width_rejects)
    rejects = merge_rejects(duckdb_rejects, width_rejects)
    malformed = rejects_to_malformed(rejects)

    if llm_repair and rejects:
        repairs = infer_repairs_with_llm(
            header,
            dialect,
            csv_input,
            rejects,
            llm_context_lines,
            trace,
        )
        for item in malformed:
            if item["line_num"] in repairs:
                item["repaired"] = False

        repaired_path = write_repaired_copy(csv_input, repairs, dialect, trace)
        if repaired_path:
            try:
                repaired_df, final_duckdb_rejects, _ = load_with_duckdb(
                    repaired_path,
                    dialect,
                    expected_columns,
                    trace,
                    "repaired",
                )
                final_width_rejects = find_width_rejects(repaired_path, dialect, expected_columns)
                if final_width_rejects:
                    trace.write("local_width_validation_result", stage="repaired", reject_errors=final_width_rejects)
                final_rejects = merge_rejects(final_duckdb_rejects, final_width_rejects)
                if final_rejects:
                    trace.write("repaired_copy_still_has_rejects", rejects=final_rejects)
                final_reject_lines = {
                    int(reject["line"])
                    for reject in final_rejects
                    if reject.get("line") is not None
                }
                for item in malformed:
                    if item["line_num"] in repairs:
                        item["repaired"] = item["line_num"] not in final_reject_lines
                df = repaired_df
            finally:
                try:
                    os.unlink(repaired_path)
                    trace.write("repaired_copy_removed", path=repaired_path)
                except OSError as exc:
                    trace.write("repaired_copy_remove_error", path=repaired_path, error=str(exc))

    result = finalize_dataframe(df, header, has_header)

    if cheat and clean_csv and malformed:
        clean_df = load_clean_dataframe(clean_csv)
        skip_rows = dialect.preamble_rows + dialect.header_rows
        malformed_indices = {m["line_num"] - skip_rows - 1 for m in malformed}
        duckdb_skipped_lines = {int(r["line"]) for r in duckdb_rejects if r.get("line") is not None}
        duckdb_skipped_indices = {line - skip_rows - 1 for line in duckdb_skipped_lines}
        result = splice_clean_rows(result, clean_df, malformed_indices, duckdb_skipped_indices)
        trace.write("cheat_result", clean_csv=clean_csv, malformed_count=len(malformed))

    trace.write(
        "file_result",
        rows=len(result),
        columns=list(result.columns),
        malformed_count=len(malformed),
    )
    return result, malformed
