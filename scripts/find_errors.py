#!/usr/bin/env python3
"""Find files where a given SUT produced any error."""

import argparse
import csv
import io
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from pollock.metrics import alex_compare


def _counter_subtract(a: Counter, b: Counter) -> Counter:
    """Return elements in a that are not covered by b (multiset difference)."""
    result = Counter()
    for k, v in a.items():
        diff = v - b.get(k, 0)
        if diff > 0:
            result[k] = diff
    return result


POLLUTION_PATTERNS = [
    (r"file_no_payload",                "Empty file (0 bytes)"),
    (r"file_no_trailing_newline",        "Missing trailing newline"),
    (r"file_double_trailing_newline",    "Double trailing newline"),
    (r"file_no_header",                  "No header row"),
    (r"file_header_multirow_(\d+)",      "Multi-row header ({0} rows)"),
    (r"file_header_only",                "Header row only, no data"),
    (r"file_one_data_row",               "Single data row"),
    (r"file_preamble",                   "Preamble rows before header"),
    (r"file_multitable_less",            "Two tables, first has fewer columns"),
    (r"file_multitable_more",            "Two tables, first has more columns"),
    (r"file_multitable_same",            "Two tables with the same number of columns"),
    (r"file_field_delimiter_(0x\w+)",    "Non-standard field delimiter ({0})"),
    (r"file_quotation_char_(0x\w+)",     "Non-standard quotation character ({0})"),
    (r"file_escape_char_(0x\w+)",        "Non-standard escape character ({0})"),
    (r"file_record_delimiter_(0x\w+)",   "Non-standard record delimiter ({0})"),
    (r"row_extra_quote(\d+)_col(\d+)",   "Extra unescaped quote in row {0}, column {1}"),
    (r"row_field_delimiter_(\d+)_",      "Row {0} uses space as field delimiter (opposed to the correct delimiter defined by the grammar)"),
    (r"row_less_sep_row(\d+)_col(\d+)",  "Missing delimiter in row {0} at column {1}"),
    (r"row_more_sep_row(\d+)_col(\d+)",  "Extra delimiter in row {0} at column {1}"),
]


def pollution_type(filename):
    stem = filename.removesuffix(".csv")
    for pattern, description in POLLUTION_PATTERNS:
        m = re.match(pattern, stem)
        if m:
            return description.format(*m.groups())
    return "Unknown"


_GROUP_PATTERNS = [
    (r"row_field_delimiter_\d+_.+", "Row uses space as field delimiter"),
    (r"row_extra_quote\d+_col\d+",  "Extra unescaped quote"),
    (r"row_less_sep_row\d+_col\d+", "Missing delimiter"),
    (r"row_more_sep_row\d+_col\d+", "Extra delimiter"),
]


def pollution_group(filename):
    """Like pollution_type but collapses row/col-index variants into a single label."""
    stem = filename.removesuffix(".csv")
    for pattern, description in _GROUP_PATTERNS:
        if re.fullmatch(pattern, stem):
            return description
    return pollution_type(filename)


def group_by_pollution(files):
    grouped = defaultdict(list)
    for filename in files:
        grouped[pollution_group(filename)].append(filename)
    for grouped_files in grouped.values():
        grouped_files.sort(key=natural_sort_key)
    return grouped


def natural_sort_key(value):
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", value)
    ]


def sorted_pollution_groups(grouped):
    return sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))


def pollution_location(filename):
    stem = filename.removesuffix(".csv")
    patterns = [
        r"row_field_delimiter_(?P<row>\d+)_.+",
        r"row_extra_quote(?P<row>\d+)_col(?P<col>\d+)",
        r"row_less_sep_row(?P<row>\d+)_col(?P<col>\d+)",
        r"row_more_sep_row(?P<row>\d+)_col(?P<col>\d+)",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, stem)
        if match:
            row = int(match.group("row"))
            col = match.groupdict().get("col")
            return row, int(col) if col is not None else None
    return None


def format_number_ranges(values):
    values = sorted(set(values))
    if not values:
        return ""

    ranges = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append((start, prev))
        start = prev = value
    ranges.append((start, prev))

    return ", ".join(
        str(start) if start == end else f"{start}-{end}"
        for start, end in ranges
    )


def pollution_variant_summary(files):
    rows = []
    cols = []
    for filename in files:
        location = pollution_location(filename)
        if location is None:
            continue
        row, col = location
        rows.append(row)
        if col is not None:
            cols.append(col)

    parts = []
    if rows:
        parts.append(f"rows {format_number_ranges(rows)} ({len(set(rows))} unique)")
    if cols:
        parts.append(f"columns {format_number_ranges(cols)} ({len(set(cols))} unique)")
    return "; ".join(parts)


def read_csv_rows(path):
    """Read a CSV (clean/converted format: comma-delimited, double-quote) into list of rows."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"', doublequote=True)
            return [row for row in reader]
    except Exception:
        with open(path, "rb") as f:
            raw = f.read()
        import chardet
        enc = chardet.detect(raw)["encoding"] or "utf-8"
        with open(path, "r", encoding=enc) as f:
            reader = csv.reader(f, delimiter=",", quotechar='"', doublequote=True)
            return [row for row in reader]


def read_polluted_lines(path, n=5):
    """Read first n raw lines of a polluted input file."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return [f.readline().rstrip("\r\n") for _ in range(n)]
    except Exception as e:
        return [f"(could not read: {e})"]


def is_load_failed(path):
    if not os.path.exists(path):
        return True
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.readline().rstrip("\r\n") == "Application Error"
    except Exception:
        return True


def load_params(params_path):
    try:
        with open(params_path) as f:
            return json.load(f)
    except Exception:
        return {}


def load_sidecar_dialect(sidecar_path):
    """Return the dialect entry from a .llm.jsonl sidecar, or None if absent."""
    try:
        with open(sidecar_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "dialect":
                        return entry
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return None


def format_params(params):
    keys = ["delimiter", "quotechar", "escapechar", "row_delimiter",
            "encoding", "header_lines", "preamble_lines", "n_columns"]
    parts = []
    for k in keys:
        if k in params:
            v = params[k]
            parts.append(f"{k}={repr(v)}")
    return ", ".join(parts)


def malformed_report_path(loading_dir, filename):
    return os.path.join(loading_dir, f"{filename}_malformed.txt")


def load_malformed_report(path):
    report = {
        "exists": os.path.exists(path),
        "status": "missing",
        "count": 0,
        "entries": [],
        "error": None,
    }
    if not report["exists"]:
        return report

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]
    except Exception as exc:
        report["status"] = "read_error"
        report["error"] = str(exc)
        return report

    if not lines:
        report["status"] = "empty"
        return report

    header = lines[0].strip()
    if header == "Application Error":
        report["status"] = "application_error"
        report["error"] = "\n".join(lines[1:]).strip() or None
        return report

    if header.startswith("Malformed rows:"):
        report["status"] = "ok"
        try:
            report["count"] = int(header.split(":", 1)[1].strip())
        except ValueError:
            report["status"] = "parse_error"
            report["error"] = f"Invalid malformed row count header: {header!r}"
            return report

        entries = []
        for line in lines[1:]:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                report["status"] = "parse_error"
                report["error"] = f"Invalid JSON entry: {exc}"
                return report
        report["entries"] = entries
        if entries and report["count"] == 0:
            report["count"] = len(entries)
        elif report["count"] == 0:
            report["count"] = len(entries)
        return report

    report["status"] = "parse_error"
    report["error"] = f"Unknown malformed report format: {header!r}"
    return report


def format_malformed_raw(raw, max_width=120):
    text = raw if isinstance(raw, str) else repr(raw)
    text = text.replace("\n", "\\n")
    if len(text) > max_width:
        return text[: max_width - 3] + "..."
    return text


def malformed_reason_counts(reports):
    counts = Counter()
    for report in reports.values():
        for entry in report.get("entries", []):
            reason = entry.get("reason") or "Unknown"
            counts[reason] += 1
    return counts


def malformed_detection_counts(files, reports):
    detected = 0
    total_rows = 0
    for filename in files:
        report = reports.get(filename, {})
        count = report.get("count", 0)
        if count > 0:
            detected += 1
            total_rows += count
    return detected, total_rows


def subset_reports(reports, filenames):
    return {filename: reports[filename] for filename in filenames if filename in reports}


def load_cached_results(results_csv, sut):
    if not os.path.exists(results_csv):
        return None
    try:
        df = pd.read_csv(results_csv)
    except Exception:
        return None

    required = {"file", f"{sut}_correct", f"{sut}_wrong"}
    if not required.issubset(df.columns):
        return None
    return df


def compare_loaded_to_clean(task):
    fname, clean_path, loaded_path, origin_csv = task
    return fname, alex_compare(clean_path, loaded_path, origin_csv=origin_csv)


def build_results_cache(all_files, loading_dir, clean_dir, sut, results_csv, origin_csv=None):
    app_error_files = []
    compare_tasks = []
    for fname in all_files:
        loaded_path = os.path.join(loading_dir, fname + "_converted.csv")
        if is_load_failed(loaded_path):
            app_error_files.append(fname)
            continue
        clean_path = os.path.join(clean_dir, fname)
        if os.path.exists(clean_path):
            compare_tasks.append((fname, clean_path, loaded_path, origin_csv))

    compare_results = {}
    max_workers = min(os.cpu_count() or 1, 8)
    if compare_tasks:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for fname, is_correct in executor.map(compare_loaded_to_clean, compare_tasks):
                compare_results[fname] = bool(is_correct)

    rows = []
    app_error_set = set(app_error_files)
    for fname in all_files:
        if fname in app_error_set:
            correct = False
        else:
            correct = compare_results.get(fname, False)
        rows.append({
            "file": fname,
            f"{sut}_correct": int(correct),
            f"{sut}_wrong": int(not correct),
        })

    df = pd.DataFrame(rows)
    Path(results_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_csv, index=False)
    return df


def classify_files(all_files, results_csv, loading_dir, clean_dir, sut, origin_csv=None):
    df = load_cached_results(results_csv, sut)
    if df is None or set(df["file"]) != set(all_files):
        df = build_results_cache(all_files, loading_dir, clean_dir, sut, results_csv, origin_csv=origin_csv)

    app_error_files = []
    wrong_content_files = []
    wrong_col = f"{sut}_wrong"
    wrong_files = {
        row["file"]
        for _, row in df.iterrows()
        if bool(row[wrong_col])
    }

    for fname in all_files:
        loaded_path = os.path.join(loading_dir, fname + "_converted.csv")
        if is_load_failed(loaded_path):
            app_error_files.append(fname)
        elif fname in wrong_files:
            wrong_content_files.append(fname)

    return app_error_files, wrong_content_files


def format_record(row):
    buf = io.StringIO()
    csv.writer(buf).writerow(row)
    return buf.getvalue().rstrip("\r\n")


def diff_rows(clean_rows, loaded_rows, max_examples=3):
    """
    Return a diagnostic dict comparing clean vs loaded row lists.
    Both lists include the header as row 0.
    """
    diag = {}

    # Header comparison
    clean_header = clean_rows[0] if clean_rows else []
    loaded_header = loaded_rows[0] if loaded_rows else []
    if clean_header != loaded_header:
        diag["header_expected"] = clean_header
        diag["header_got"] = loaded_header

    # Row / column counts
    clean_data = clean_rows[1:] if len(clean_rows) > 1 else []
    loaded_data = loaded_rows[1:] if len(loaded_rows) > 1 else []
    diag["expected_rows"] = len(clean_data)
    diag["loaded_rows"] = len(loaded_data)

    if clean_data:
        diag["expected_cols"] = len(clean_data[0])
    if loaded_data:
        diag["loaded_cols"] = len(loaded_data[0])

    # Multiset diff on records (same logic as metrics.py)
    clean_records = Counter("||".join(r) for r in clean_data)
    loaded_records = Counter("||".join(r) for r in loaded_data)

    missing = _counter_subtract(clean_records, loaded_records)
    extra   = _counter_subtract(loaded_records, clean_records)

    if missing:
        diag["missing_count"] = sum(missing.values())
        diag["missing_examples"] = [r.split("||") for r in list(missing)[:max_examples]]
    if extra:
        diag["extra_count"] = sum(extra.values())
        diag["extra_examples"] = [r.split("||") for r in list(extra)[:max_examples]]

    return diag


def write_file_section(f, filename, scores, diag, polluted_lines, params, poll_type, malformed_report=None, sidecar_dialect=None):
    sep = "-" * 70
    f.write(f"\n{sep}\n")
    f.write(f"FILE: {filename}\n")
    f.write(f"POLLUTION: {poll_type}\n")
    if params:
        f.write(f"DIALECT: {format_params(params)}\n")
    if sidecar_dialect:
        f.write(f"SNIFFED: {format_params(sidecar_dialect.get('sniffed', {}))}\n")
        f.write(f"REFINED: {format_params(sidecar_dialect.get('final', {}))}\n")

    if malformed_report and malformed_report.get("exists"):
        status = malformed_report.get("status")
        if status == "ok":
            count = malformed_report.get("count", 0)
            f.write(f"MALFORMED ROWS DETECTED: {count}\n")
            if count:
                entries = malformed_report.get("entries", [])
                for entry in entries[:3]:
                    f.write(
                        f"  line {entry.get('line_num')}: {entry.get('reason')} "
                        f"- {format_malformed_raw(entry.get('raw'))}\n"
                    )
                if count > len(entries[:3]):
                    f.write(f"  ... and {count - len(entries[:3])} more\n")
        else:
            f.write(f"MALFORMED ROW REPORT: {status}\n")
            if malformed_report.get("error"):
                f.write(f"  {malformed_report['error']}\n")

    if scores.get("load_failed", False):
        f.write("\n  SUT failed to load the file.\n")
        if polluted_lines:
            f.write("  First lines of polluted input:\n")
            for line in polluted_lines:
                f.write(f"    {line}\n")
        return

    if diag is None:
        return

    # Header mismatch
    if "header_expected" in diag:
        f.write("\n  HEADER MISMATCH:\n")
        f.write(f"    Expected: {diag['header_expected']}\n")
        f.write(f"    Got:      {diag['header_got']}\n")

    # Row / column counts
    er, lr = diag.get("expected_rows"), diag.get("loaded_rows")
    ec, lc = diag.get("expected_cols"), diag.get("loaded_cols")
    if er is not None and lr is not None:
        row_note = "" if er == lr else f"  ← expected {er}"
        f.write(f"\n  ROWS: loaded {lr}{row_note}\n")
    if ec is not None and lc is not None and ec != lc:
        f.write(f"  COLS: expected {ec}, got {lc} (first data row)\n")

    # Missing records
    if "missing_count" in diag:
        cnt = diag["missing_count"]
        f.write(f"\n  MISSING RECORDS ({cnt} record(s) present in clean but absent in loaded output):\n")
        for ex in diag["missing_examples"]:
            f.write(f"    {format_record(ex)}\n")
        if cnt > len(diag["missing_examples"]):
            f.write(f"    ... and {cnt - len(diag['missing_examples'])} more\n")

    # Extra records
    if "extra_count" in diag:
        cnt = diag["extra_count"]
        f.write(f"\n  EXTRA RECORDS ({cnt} record(s) in loaded output not in clean file):\n")
        for ex in diag["extra_examples"]:
            f.write(f"    {format_record(ex)}\n")
        if cnt > len(diag["extra_examples"]):
            f.write(f"    ... and {cnt - len(diag['extra_examples'])} more\n")


def main():
    parser = argparse.ArgumentParser(
        description="Find files where a SUT failed to load (Application Error)."
    )
    parser.add_argument("sut", help="Name of the SUT (e.g. pandas, duckdbparse)")
    parser.add_argument(
        "--dataset", default="polluted_files",
        help="Dataset to examine (default: polluted_files)"
    )
    parser.add_argument(
        "--results-dir", default="results",
        help="Root results directory (default: results)"
    )
    parser.add_argument(
        "--polluted-dir", default="data/polluted_files",
        help="Root polluted files directory (default: data/polluted_files)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output file path (default: results/{sut}/{dataset}/{sut}_errors.txt)"
    )
    parser.add_argument(
        "--max-details-per-type", type=int, default=3,
        help="Number of detailed file examples to write per pollution type (0 = all; default: 3)"
    )
    parser.add_argument(
        "--custom", action="store_true",
        help="Read custom malformed-row sidecars and report detection ratios by pollution type"
    )
    parser.add_argument(
        "--origin-csv", default=None,
        help="Pre-pollution source CSV; a cell is accepted if it matches either the clean value "
             "or this origin value (default: {polluted-dir}/source.csv if it exists)"
    )
    args = parser.parse_args()
    if args.max_details_per_type < 0:
        parser.error("--max-details-per-type must be greater than or equal to 0")

    sut = args.sut
    results_csv = os.path.join(args.results_dir, sut, args.dataset, f"{sut}_results.csv")
    loading_dir = os.path.join(args.results_dir, sut, args.dataset, "loading")
    clean_dir   = os.path.join(args.polluted_dir, "clean")
    csv_dir     = os.path.join(args.polluted_dir, "csv")
    params_dir  = os.path.join(args.polluted_dir, "parameters")

    origin_csv = args.origin_csv
    if origin_csv is None:
        for candidate in [os.path.join(args.polluted_dir, "source.csv"),
                          "data/polluted_files/source.csv"]:
            if os.path.exists(candidate):
                origin_csv = candidate
                break

    # Get file list from results CSV if available, otherwise scan the input dir.
    if os.path.exists(results_csv):
        df = pd.read_csv(results_csv)
        all_files = df["file"].tolist()
    elif os.path.isdir(csv_dir):
        all_files = sorted(f for f in os.listdir(csv_dir) if f.endswith(".csv"))
    else:
        sys.exit(f"Error: neither results CSV ({results_csv}) nor input dir ({csv_dir}) found")

    app_error_files, wrong_content_files = classify_files(
        all_files=all_files,
        results_csv=results_csv,
        loading_dir=loading_dir,
        clean_dir=clean_dir,
        sut=sut,
        origin_csv=origin_csv,
    )

    app_error_groups = group_by_pollution(app_error_files)
    wrong_content_groups = group_by_pollution(wrong_content_files)
    app_error_counts = Counter({k: len(v) for k, v in app_error_groups.items()})
    wrong_content_counts = Counter({k: len(v) for k, v in wrong_content_groups.items()})
    malformed_reports = {}
    if args.custom:
        malformed_reports = {
            fname: load_malformed_report(malformed_report_path(loading_dir, fname))
            for fname in all_files
        }

    output_path = args.output or os.path.join(args.results_dir, sut, args.dataset, f"{sut}_errors.txt")

    def write_category_counts(out, grouped):
        if not grouped:
            out.write("  (none)\n")
            return
        for category, files in sorted_pollution_groups(grouped):
            out.write(f"  {len(files):4d}  {category}\n")

    def detail_files_for_type(files):
        if args.max_details_per_type == 0:
            return files
        return files[:args.max_details_per_type]

    def write_pollution_type_header(out, pollution, files):
        out.write(f"\n{'-'*70}\n")
        out.write(f"POLLUTION TYPE: {pollution}\n")
        out.write(f"FILES: {len(files)}\n")
        variants = pollution_variant_summary(files)
        if variants:
            out.write(f"VARIANTS: {variants}\n")

        shown = detail_files_for_type(files)
        if len(shown) < len(files):
            hidden = len(files) - len(shown)
            out.write(
                f"SHOWING: {len(shown)} example file(s); "
                f"{hidden} more grouped under this pollution type.\n"
            )
        return shown

    def write_app_error_file(out, fname):
        params = load_params(os.path.join(params_dir, fname + "_parameters.json"))
        polluted_lines = read_polluted_lines(os.path.join(csv_dir, fname))
        sidecar_dialect = load_sidecar_dialect(os.path.join(loading_dir, fname + ".llm.jsonl"))
        write_file_section(
            out,
            fname,
            {"load_failed": True},
            None,
            polluted_lines,
            params,
            pollution_type(fname),
            malformed_reports.get(fname),
            sidecar_dialect=sidecar_dialect,
        )

    def write_wrong_content_file(out, fname):
        params = load_params(os.path.join(params_dir, fname + "_parameters.json"))
        clean_path = os.path.join(clean_dir, fname)
        loaded_path = os.path.join(loading_dir, fname + "_converted.csv")
        clean_rows = read_csv_rows(clean_path)
        loaded_rows = read_csv_rows(loaded_path)
        diag = diff_rows(clean_rows, loaded_rows)
        sidecar_dialect = load_sidecar_dialect(os.path.join(loading_dir, fname + ".llm.jsonl"))
        write_file_section(
            out,
            fname,
            {"load_failed": False},
            diag,
            None,
            params,
            pollution_type(fname),
            malformed_reports.get(fname),
            sidecar_dialect=sidecar_dialect,
        )

    def write_grouped_file_sections(out, grouped, write_file):
        if not grouped:
            out.write("\n  (none)\n")
            return
        for pollution, files in sorted_pollution_groups(grouped):
            for fname in write_pollution_type_header(out, pollution, files):
                write_file(out, fname)

    def write_custom_detection_summary(out):
        wrong_reports = subset_reports(malformed_reports, wrong_content_files)
        present = sum(1 for report in wrong_reports.values() if report.get("exists"))
        detected = sum(1 for report in wrong_reports.values() if report.get("count", 0) > 0)
        total_rows = sum(report.get("count", 0) for report in wrong_reports.values())

        out.write(f"\n{'='*70}\n")
        out.write("CUSTOM MALFORMED-ROW DETECTION\n")
        out.write(f"{'='*70}\n")
        out.write(f"Scope: wrong-content files only\n")
        out.write(f"Sidecar reports found: {present} / {len(wrong_content_files)}\n")
        out.write(f"Files with detected malformed rows: {detected} / {len(wrong_content_files)}")
        if wrong_content_files:
            out.write(f" ({detected / len(wrong_content_files):.1%})")
        out.write("\n")
        out.write(f"Total malformed rows logged: {total_rows}\n")

        out.write("\nDETECTION RATIO BY POLLUTION TYPE\n")
        if not wrong_content_groups:
            out.write("  (none)\n")
        for pollution, files in sorted_pollution_groups(wrong_content_groups):
            detected_files, rows_logged = malformed_detection_counts(files, malformed_reports)
            ratio = detected_files / len(files) if files else 0.0
            out.write(
                f"  {detected_files:4d}/{len(files):4d}  {ratio:6.1%}  {pollution}"
            )
            if rows_logged:
                out.write(f"  ({rows_logged} row(s) logged)")
            out.write("\n")

        reason_counts = malformed_reason_counts(wrong_reports)
        out.write("\nMALFORMED ROW REASONS\n")
        if reason_counts:
            for reason, count in reason_counts.most_common():
                out.write(f"  {count:4d}  {reason}\n")
        else:
            out.write("  (none)\n")

    with open(output_path, "w") as out:
        out.write(f"SUT: {sut}\n")
        out.write(f"Dataset: {args.dataset}\n")
        if os.path.exists(results_csv):
            out.write(f"Results file: {results_csv}\n")
        out.write(f"Total files evaluated: {len(all_files)}\n")
        out.write(f"Application errors: {len(app_error_files)}\n")
        out.write(f"Wrong content:      {len(wrong_content_files)}\n")
        if args.custom:
            missing_sidecars = sum(1 for report in malformed_reports.values() if not report.get("exists"))
            out.write(f"Malformed sidecars: {len(all_files) - missing_sidecars} / {len(all_files)}\n")

        if args.custom:
            write_custom_detection_summary(out)

        out.write(f"\n{'='*70}\n")
        out.write(f"APPLICATION ERRORS BY POLLUTION TYPE - {len(app_error_files)} files\n")
        out.write(f"{'='*70}\n")
        write_category_counts(out, app_error_groups)

        out.write(f"\n{'='*70}\n")
        out.write(f"APPLICATION ERROR FILES BY POLLUTION TYPE\n")
        out.write(f"{'='*70}\n")
        write_grouped_file_sections(out, app_error_groups, write_app_error_file)

        out.write(f"\n{'='*70}\n")
        out.write(f"WRONG CONTENT BY POLLUTION TYPE - {len(wrong_content_files)} files\n")
        out.write(f"{'='*70}\n")
        write_category_counts(out, wrong_content_groups)

        out.write(f"\n{'='*70}\n")
        out.write(f"WRONG CONTENT FILES BY POLLUTION TYPE\n")
        out.write(f"{'='*70}\n")
        write_grouped_file_sections(out, wrong_content_groups, write_wrong_content_file)

    print(f"Results written to {output_path}")
    if args.custom:
        wrong_reports = subset_reports(malformed_reports, wrong_content_files)
        detected = sum(1 for report in wrong_reports.values() if report.get("count", 0) > 0)
        present = sum(1 for report in wrong_reports.values() if report.get("exists"))
        print(f"  Malformed sidecars on wrong-content files: {present} / {len(wrong_content_files)}")
        print(f"  Wrong-content files with detected malformed rows: {detected} / {len(wrong_content_files)}")
    print(f"  Application errors: {len(app_error_files)} / {len(all_files)}")
    if app_error_counts:
        for category, count in sorted(app_error_counts.items(), key=lambda x: -x[1]):
            print(f"    {count:4d}  {category}")
    print(f"  Wrong content: {len(wrong_content_files)} / {len(all_files)}")
    if wrong_content_counts:
        for category, count in sorted(wrong_content_counts.items(), key=lambda x: -x[1]):
            print(f"    {count:4d}  {category}")


if __name__ == "__main__":
    main()
