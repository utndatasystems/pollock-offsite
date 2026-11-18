"""Build data/combined_real_world_files from hand_annotated_real and survey_sample.

hand_annotated_real is copied as is. survey_sample files longer than MAX_LINES
physical lines are cut at the last record boundary within MAX_LINES; their clean
file is cut to the header plus the rows of the kept input records. Clean rows are
matched to input records by content (letters and digits only, since the clean
files fix encodings and whitespace), and the script stops if the cut cannot be
verified: the first clean row left out must match the first input record left out.
Bytes, encodings and line endings of the kept lines are preserved.

Usage: python scripts/build_combined_real_world_files.py
"""
import csv
import io
import json
import os
import re
import shutil

MAX_LINES = 300
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUT = os.path.join(DATA, "combined_real_world_files")
csv.field_size_limit(10**9)


def records(lines, delimiter, quotechar, escapechar):
    """Yield (record, number of physical lines consumed up to and including it)."""
    reader = csv.reader(
        io.StringIO("".join(lines), newline=""),
        delimiter=delimiter,
        quotechar=quotechar or '"',
        quoting=csv.QUOTE_MINIMAL if quotechar else csv.QUOTE_NONE,
        escapechar=None if escapechar in ("", None, quotechar) else escapechar,
    )
    for rec in reader:
        yield rec, reader.line_num


def key(rec):
    return re.sub(r"[^A-Za-z0-9]", "", "".join(rec))


def cut_survey_file(name, src):
    with open(f"{src}/parameters/{name}_parameters.json") as f:
        params = json.load(f)
    encoding = "utf-8" if params["encoding"] == "ascii" else params["encoding"]
    with open(f"{src}/csv/{name}", "rb") as f:
        csv_lines = f.read().splitlines(keepends=True)
    with open(f"{src}/clean/{name}", "rb") as f:
        clean_lines = f.read().splitlines(keepends=True)

    # Parse a window past the limit so a record crossing line MAX_LINES is seen whole.
    window = [line.decode(encoding, errors="replace") for line in csv_lines[: MAX_LINES + 200]]
    recs = list(records(window, params["delimiter"], params["quotechar"], params["escapechar"]))
    cut_at = max(n for _, n in recs if n <= MAX_LINES)
    kept = [key(rec) for rec, n in recs if n <= cut_at]
    left_out = [key(rec) for rec, n in recs if n > cut_at]

    clean_window = [line.decode("utf-8") for line in clean_lines[: MAX_LINES + 400]]
    clean_recs = list(records(clean_window, ",", '"', '"'))
    clean_keys = [key(rec) for rec, _ in clean_recs]

    # Match clean data rows (after the clean header) to kept input records in order.
    # Input records without a clean row (preamble, header, blank lines) are skipped.
    # A clean row that differs from its input record is accepted when its neighbours
    # line up (a fix or typo in the ground truth).
    i = matched = 0
    substituted = []
    for c in range(1, len(clean_keys)):
        j = i
        while j < len(kept) and kept[j] != clean_keys[c]:
            j += 1
        if j < len(kept):
            i = j + 1
        elif i + 1 < len(kept) and c + 1 < len(clean_keys) and clean_keys[c + 1] == kept[i + 1]:
            substituted.append(c + 1)
            i += 1
        else:
            break
        matched += 1

    next_clean = clean_keys[1 + matched] if 1 + matched < len(clean_keys) else None
    if next_clean is None or next_clean not in left_out[:5]:
        raise SystemExit(f"cannot verify cut of {name}: {matched} clean rows matched")

    clean_cut_at = clean_recs[matched][1]  # line count after header + matched rows
    os.makedirs(f"{OUT}/csv", exist_ok=True)
    os.makedirs(f"{OUT}/clean", exist_ok=True)
    with open(f"{OUT}/csv/{name}", "wb") as f:
        f.writelines(csv_lines[:cut_at])
    with open(f"{OUT}/clean/{name}", "wb") as f:
        f.writelines(clean_lines[:clean_cut_at])
    print(
        f"cut {name}: {len(csv_lines)} -> {cut_at} input lines, "
        f"{matched} data rows, {len(kept) - matched} input records not in clean"
        + (f", clean lines differing from input: {substituted}" if substituted else "")
    )


def main():
    src = f"{DATA}/hand_annotated_real"
    for sub in sorted(os.listdir(src)):
        shutil.copytree(f"{src}/{sub}", f"{OUT}/{sub}", dirs_exist_ok=True)

    src = f"{DATA}/survey_sample"
    os.makedirs(f"{OUT}/parameters", exist_ok=True)
    for name in sorted(os.listdir(f"{src}/csv")):
        if os.path.exists(f"{DATA}/hand_annotated_real/csv/{name}"):
            raise SystemExit(f"{name} exists in both source datasets")
        shutil.copy2(f"{src}/parameters/{name}_parameters.json", f"{OUT}/parameters/")
        with open(f"{src}/csv/{name}", "rb") as f:
            n_lines = len(f.read().splitlines())
        if n_lines <= MAX_LINES:
            shutil.copy2(f"{src}/csv/{name}", f"{OUT}/csv/")
            shutil.copy2(f"{src}/clean/{name}", f"{OUT}/clean/")
        else:
            cut_survey_file(name, src)

    for sub in ("csv", "clean", "parameters"):
        print(sub, len(os.listdir(f"{OUT}/{sub}")))


if __name__ == "__main__":
    main()
