"""
Merge per-engine attack outputs into one combined dataset.

After each engine has run pollute_main_extended.py and score_engine.py against
its own per-engine dataset (e.g. data/extended_unicode), this script collects
the worst-K pollutions per (engine, parser) into a single combined dataset
data/extended_pollutions/, ready for full-roster evaluation.

Selection: for each engine and each Python SuT scored during the closed loop,
take the K files with lowest cell_f1 (the strongest attacks against that
parser). Union across SuTs and across engines, deduplicated by filename.

Output structure mirrors the standard benchmark:
    data/extended_pollutions/csv/
    data/extended_pollutions/clean/
    data/extended_pollutions/parameters/

Each input file is copied (not moved) so engine datasets stay intact for
debugging.

Usage:
    python3 scripts/merge_engines.py --engines unicode quote typeinfer lineend struct dialect --top-k 25
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

import pandas as pd


PYTHON_SUTS = ["duckdbparse", "duckdbauto", "pandas", "pycsv"]


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def select_worst(engine: str, top_k: int) -> set:
    """Return the set of filenames to promote from this engine's dataset."""
    dataset = f"extended_{engine}"
    global_path = f"{repo_root()}/results/global_results_{dataset}.csv"
    if not os.path.exists(global_path):
        sys.stderr.write(f"[merge] no global_results for engine {engine}\n")
        return set()
    df = pd.read_csv(global_path)
    if "file" not in df.columns:
        df = df.rename(columns={df.columns[0]: "file"})
    df = df.set_index("file")

    selected = set()
    for sut in PYTHON_SUTS:
        col = f"{sut}_cell_f1"
        if col not in df.columns:
            continue
        bad = df.sort_values(col, ascending=True).head(top_k).index.tolist()
        selected.update(bad)
    return selected


def copy_one(src_root: str, filename: str, dst_root: str, hashes_seen: dict) -> bool:
    """Copy csv + clean + parameters for a single filename. Skip on hash collision.

    Dedup hash combines the CSV bytes AND the parameters JSON, so two files
    that share bytes but lie differently in parameters (a real Engine F
    pattern) are kept as distinct attacks.
    """
    src_csv = os.path.join(src_root, "csv", filename)
    if not os.path.exists(src_csv):
        sys.stderr.write(f"[merge]   missing {src_csv}\n")
        return False

    src_param = os.path.join(src_root, "parameters", f"{filename}_parameters.json")
    h = hashlib.sha256()
    with open(src_csv, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    h.update(b"\x00PARAM\x00")
    if os.path.exists(src_param):
        with open(src_param, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    digest = h.hexdigest()
    if digest in hashes_seen:
        sys.stderr.write(
            f"[merge]   skipping {filename} (duplicate of {hashes_seen[digest]})\n"
        )
        return False
    hashes_seen[digest] = filename

    for sub in ("csv", "clean"):
        src = os.path.join(src_root, sub, filename)
        dst = os.path.join(dst_root, sub, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    src_param = os.path.join(src_root, "parameters", f"{filename}_parameters.json")
    dst_param = os.path.join(dst_root, "parameters", f"{filename}_parameters.json")
    if os.path.exists(src_param):
        shutil.copy2(src_param, dst_param)
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--engines", nargs="+", required=True,
                   help="Engine names whose datasets live at data/extended_<name>")
    p.add_argument("--out", default="./data/extended_pollutions",
                   help="Combined output dataset root")
    p.add_argument("--top-k", type=int, default=25,
                   help="Worst-K pollutions per (engine, sut) to promote")
    p.add_argument("--clean-out", action="store_true",
                   help="Wipe the output dataset dir before merging")
    args = p.parse_args()

    out_root = os.path.abspath(args.out)
    if args.clean_out and os.path.isdir(out_root):
        shutil.rmtree(out_root)
    for sub in ("csv", "clean", "parameters"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    hashes_seen: dict = {}
    promoted = 0
    by_engine: dict = {}
    for eng in args.engines:
        src_root = os.path.abspath(f"./data/extended_{eng}")
        if not os.path.isdir(src_root):
            sys.stderr.write(f"[merge] dataset dir missing for engine {eng}: {src_root}\n")
            continue
        winners = select_worst(eng, args.top_k)
        eng_count = 0
        for fname in sorted(winners):
            if copy_one(src_root, fname, out_root, hashes_seen):
                eng_count += 1
                promoted += 1
        by_engine[eng] = eng_count
        print(f"[merge] {eng}: promoted {eng_count} files")

    manifest = {
        "engines": args.engines,
        "top_k_per_sut": args.top_k,
        "promoted_total": promoted,
        "promoted_by_engine": by_engine,
    }
    with open(os.path.join(out_root, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[merge] wrote {promoted} files to {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
