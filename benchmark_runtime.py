"""Validation and aggregation helpers for benchmark runtime artifacts."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


_RUNTIME_COLUMNS = (
    "file",
    "runtime_mean_seconds",
    "runtime_median_seconds",
    "runtime_max_seconds",
    "runtime_repetitions",
)


def _as_boolean(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"1", "1.0", "true", "yes"})


def _output_succeeded(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("rb") as handle:
            return not handle.read(32).startswith(b"Application Error")
    except OSError:
        return False


def load_file_runtimes(repo_root: Path | str, sut_id: str, dataset: str) -> pd.DataFrame:
    """Load only successful, cold, non-stale timing repetitions.

    Legacy code-generation timing files are rejected because they did not record
    cache hits, so cold inference cannot be distinguished from a cache lookup.
    Legacy full-loader timings remain usable: its overwrite mode already bypasses
    the local cache, and failed outputs are detected from their output files.
    """
    repo_root = Path(repo_root)
    result_dir = repo_root / "results" / sut_id / dataset
    time_path = result_dir / f"{sut_id}_time.csv"
    if not time_path.exists():
        return pd.DataFrame(columns=_RUNTIME_COLUMNS)

    time_data = pd.read_csv(time_path)
    filename_column = "filename" if "filename" in time_data.columns else time_data.columns[0]
    time_columns = [
        column for column in time_data.columns
        if re.fullmatch(r"(?:.*_)?time_(\d+)", column)
    ]
    if not time_columns:
        raise ValueError(f"No timing columns found in {time_path}")

    filenames = time_data[filename_column].astype(str)
    timings = time_data[time_columns].apply(pd.to_numeric, errors="coerce")
    legacy_code_generation = sut_id.startswith("code_generation_llm")

    for time_column in time_columns:
        repetition = re.fullmatch(r"(?:.*_)?time_(\d+)", time_column).group(1)
        valid = timings[time_column].notna()
        success_column = f"success_{repetition}"
        cache_column = f"local_cache_hits_{repetition}"

        if success_column in time_data:
            valid &= _as_boolean(time_data[success_column])
        else:
            valid &= pd.Series([
                _output_succeeded(result_dir / "loading" / f"{filename}_converted.csv")
                for filename in filenames
            ], index=time_data.index)

        if cache_column in time_data:
            cache_hits = pd.to_numeric(time_data[cache_column], errors="coerce")
            valid &= cache_hits.eq(0)
        elif legacy_code_generation:
            valid &= False

        # A newer output means an interrupted rerun changed the result without
        # reaching the timing checkpoint. Do not combine artifacts from two runs.
        timing_mtime = time_path.stat().st_mtime
        valid &= pd.Series([
            not (result_dir / "loading" / f"{filename}_converted.csv").exists()
            or (result_dir / "loading" / f"{filename}_converted.csv").stat().st_mtime
                <= timing_mtime + 1e-6
            for filename in filenames
        ], index=time_data.index)
        timings.loc[~valid, time_column] = pd.NA

    file_runtimes = pd.DataFrame({
        "file": filenames,
        "runtime_mean_seconds": timings.mean(axis=1),
        "runtime_median_seconds": timings.median(axis=1),
        "runtime_max_seconds": timings.max(axis=1),
        "runtime_repetitions": timings.notna().sum(axis=1),
    }).dropna(subset=["runtime_mean_seconds"])

    if file_runtimes["file"].duplicated().any():
        duplicates = sorted(file_runtimes.loc[file_runtimes["file"].duplicated(), "file"].unique())
        raise ValueError(f"Duplicate filenames in {time_path}: {duplicates}")
    return file_runtimes.reset_index(drop=True)
