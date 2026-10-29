from pathlib import Path

import pandas as pd

from benchmark_runtime import load_file_runtimes


def _write_result(tmp_path: Path, sut: str, row: dict, output: str = "a\n1\n"):
    result_dir = tmp_path / "results" / sut / "csv_storm"
    loading_dir = result_dir / "loading"
    loading_dir.mkdir(parents=True)
    output_path = loading_dir / "sample.csv_converted.csv"
    output_path.write_text(output)
    time_path = result_dir / f"{sut}_time.csv"
    pd.DataFrame([{"filename": "sample.csv", **row}]).to_csv(time_path, index=False)
    return time_path, output_path


def test_accepts_successful_cold_timing(tmp_path):
    sut = "llm_hybrid_parser_test"
    _write_result(tmp_path, sut, {
        "time_0": 12.5, "success_0": True, "local_cache_hits_0": 0,
    })

    result = load_file_runtimes(tmp_path, sut, "csv_storm")

    assert result.loc[0, "runtime_mean_seconds"] == 12.5
    assert result.loc[0, "runtime_repetitions"] == 1


def test_rejects_cached_and_failed_timings(tmp_path):
    cached = "llm_hybrid_parser_cached"
    failed = "llm_hybrid_parser_failed"
    _write_result(tmp_path, cached, {
        "time_0": 0.1, "success_0": True, "local_cache_hits_0": 1,
    })
    _write_result(tmp_path, failed, {
        "time_0": 0.1, "success_0": False, "local_cache_hits_0": 0,
    })

    assert load_file_runtimes(tmp_path, cached, "csv_storm").empty
    assert load_file_runtimes(tmp_path, failed, "csv_storm").empty


def test_rejects_unauditable_legacy_codegen_timing(tmp_path):
    sut = "code_generation_llm_legacy"
    _write_result(tmp_path, sut, {"code_generation_llm_legacy_time_0": 0.2})

    assert load_file_runtimes(tmp_path, sut, "csv_storm").empty


def test_keeps_successful_legacy_full_loader_timing(tmp_path):
    sut = "full_llm_loader_naive_legacy"
    _write_result(tmp_path, sut, {"time_0": 60.0})

    result = load_file_runtimes(tmp_path, sut, "csv_storm")

    assert result.loc[0, "runtime_mean_seconds"] == 60.0


def test_rejects_legacy_application_error_and_stale_output(tmp_path):
    failed = "full_llm_loader_naive_failed"
    stale = "full_llm_loader_naive_stale"
    _write_result(tmp_path, failed, {"time_0": 0.2}, "Application Error\nquota")
    time_path, output_path = _write_result(tmp_path, stale, {"time_0": 10.0})
    newer = time_path.stat().st_mtime + 2
    output_path.touch()
    output_path.chmod(0o644)
    import os
    os.utime(output_path, (newer, newer))

    assert load_file_runtimes(tmp_path, failed, "csv_storm").empty
    assert load_file_runtimes(tmp_path, stale, "csv_storm").empty
