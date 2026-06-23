"""Count malformed rows reported by a SUT.

A SUT writes one `<file>_malformed.txt` per input file under
`results/<sut>/<dataset>/loading/`. Each report starts with a
`Malformed rows: N` header (or `Application Error`) followed by one JSON object
per malformed row, each with `line_num`, `reason`, `raw` and an optional
`repaired` flag (true = fixed in the final output, false/absent = still bad).

Usage:
    python scripts/count_malformed.py <sut-results-folder> [--dataset NAME] [--all]

Examples:
    python scripts/count_malformed.py llm_hybrid_parser_gpt_5_4_mini_duckdb
    python scripts/count_malformed.py duckdbauto --dataset small_sample --all
"""
import argparse
import json
import os
import sys

RESULTS_ROOT = "results"


def parse_report(path):
    """Return (malformed, repaired, is_error) for one report file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    if lines and lines[0].startswith("Application Error"):
        return 0, 0, True

    malformed = repaired = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Malformed rows:"):
            continue
        # Count it anyway (even on a JSON error) so we never under-report a row.
        malformed += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("repaired") is True:
            repaired += 1
    return malformed, repaired, False


def count_dataset(sut, dataset, show_all):
    loading_dir = os.path.join(RESULTS_ROOT, sut, dataset, "loading")
    if not os.path.isdir(loading_dir):
        print(f"  No loading/ dir for dataset '{dataset}' (looked in {loading_dir})")
        return

    reports = sorted(f for f in os.listdir(loading_dir) if f.endswith("_malformed.txt"))
    if not reports:
        print(f"  No *_malformed.txt reports under {loading_dir}")
        return

    rows = []
    tot_malformed = tot_repaired = n_errors = 0
    for report in reports:
        name = report[: -len("_malformed.txt")]
        malformed, repaired, is_error = parse_report(os.path.join(loading_dir, report))
        if is_error:
            n_errors += 1
        tot_malformed += malformed
        tot_repaired += repaired
        rows.append((name, malformed, repaired, is_error))

    print(f"\n=== {sut} / {dataset} ===")
    width = max((len(name) for name, *_ in rows), default=4)
    header = f"{'file':<{width}}  {'malformed':>9}  {'repaired':>8}"
    print(header)
    print("-" * len(header))
    for name, malformed, repaired, is_error in rows:
        if not show_all and malformed == 0 and not is_error:
            continue
        flag = "  ERROR" if is_error else ""
        print(f"{name:<{width}}  {malformed:>9}  {repaired:>8}{flag}")
    print("-" * len(header))
    print(f"{'TOTAL (' + str(len(rows)) + ' files)':<{width}}  "
          f"{tot_malformed:>9}  {tot_repaired:>8}")
    if n_errors:
        print(f"Files with Application Error: {n_errors}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sut", help="Results folder name, e.g. llm_hybrid_parser_gpt_5_4_mini_duckdb")
    parser.add_argument("--dataset", default=None,
                        help="Dataset to count (default: every dataset found under the SUT folder)")
    parser.add_argument("--all", action="store_true",
                        help="List every file, including those with zero malformed rows")
    args = parser.parse_args()

    sut_dir = os.path.join(RESULTS_ROOT, args.sut)
    if not os.path.isdir(sut_dir):
        available = sorted(d for d in os.listdir(RESULTS_ROOT)
                           if os.path.isdir(os.path.join(RESULTS_ROOT, d))) \
            if os.path.isdir(RESULTS_ROOT) else []
        print(f"No results folder '{args.sut}' under {RESULTS_ROOT}/")
        if available:
            print("Available SUTs:")
            for s in available:
                print(f"  {s}")
        sys.exit(1)

    if args.dataset:
        datasets = [args.dataset]
    else:
        datasets = sorted(d for d in os.listdir(sut_dir)
                          if os.path.isdir(os.path.join(sut_dir, d, "loading")))
        if not datasets:
            print(f"No datasets with a loading/ dir found under {sut_dir}")
            sys.exit(1)

    for dataset in datasets:
        count_dataset(args.sut, dataset, args.all)


if __name__ == "__main__":
    main()
