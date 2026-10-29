"""Safety checks for isolated benchmark runs."""

from argparse import Namespace

import pytest

from scripts import experiment_run as runs


@pytest.fixture
def run_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(runs, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runs, "RUNS_ROOT", tmp_path / "results" / "runs")
    monkeypatch.setattr(runs, "RECORDS_ROOT", tmp_path / "experiments")
    monkeypatch.setattr(runs, "require_clean_tree", lambda: None)
    monkeypatch.setattr(runs, "git", lambda *args: "a" * 40)
    (tmp_path / "requirements.txt").write_text("")
    csv_dir = tmp_path / "data" / "tiny" / "csv"
    csv_dir.mkdir(parents=True)
    (csv_dir / "file.csv").write_text("a\n1\n")
    return tmp_path


def init_args(**changes):
    values = dict(
        run_id="trial", resume=False, script="classical", dataset="tiny", seed=1337,
        remote_models="", local_models="", suts="pandas", files="", repetitions="3",
        eval_njobs=1, cache_policy="none", verbose=False,
    )
    values.update(changes)
    return Namespace(**values)


def test_run_id_is_unique_and_resume_checks_dataset(run_workspace):
    runs.init_run(init_args())
    with pytest.raises(FileExistsError):
        runs.init_run(init_args())

    runs.init_run(init_args(resume=True))
    with pytest.raises(ValueError, match="config"):
        runs.init_run(init_args(resume=True, seed=999))
    (run_workspace / "data" / "tiny" / "csv" / "file.csv").write_text("a\n2\n")
    with pytest.raises(ValueError, match="dataset_sha256"):
        runs.init_run(init_args(resume=True))
    with pytest.raises(ValueError, match="run ID"):
        runs.run_dir("../elsewhere")


def test_manifest_endpoint_omits_credentials():
    assert runs.sanitized_endpoint("https://user:secret@example.org/v1?api_key=secret") == (
        "https://example.org/v1"
    )


def test_completion_requires_results_and_export_copies_summaries(run_workspace):
    runs.init_run(init_args(files="file.csv"))
    with pytest.raises(ValueError, match="unevaluated"):
        runs.finish_run(Namespace(run_id="trial", status="complete", exit_code=0))

    directory = runs.run_dir("trial")
    result_dir = directory / "pandas" / "tiny"
    result_dir.mkdir(parents=True)
    (result_dir / "pandas_results.csv").write_text("file,pandas_correct\nother.csv,1\n")
    with pytest.raises(ValueError, match="selected files"):
        runs.mark_sut(Namespace(run_id="trial", sut="pandas"))
    (result_dir / "pandas_results.csv").write_text("file,pandas_correct\nfile.csv,1\n")
    runs.mark_sut(Namespace(run_id="trial", sut="pandas"))
    for stem in ("evaluation_summary", "evaluation_by_file"):
        (directory / f"{stem}_tiny.csv").write_text("header\n")
    runs.finish_run(Namespace(run_id="trial", status="complete", exit_code=0))
    runs.export_run(Namespace(run_id="trial"))

    record = run_workspace / "experiments" / "trial"
    assert (record / "manifest.json").is_file()
    assert (record / "evaluation_summary_tiny.csv").is_file()
    assert (record / "evaluation_by_file_tiny.csv").is_file()
    with pytest.raises(ValueError, match="already complete"):
        runs.init_run(init_args(resume=True))
