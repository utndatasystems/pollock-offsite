"""Create, verify, and archive isolated benchmark runs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = REPO_ROOT / "results" / "runs"
RECORDS_ROOT = REPO_ROOT / "experiments"
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True
    ).strip()


def require_clean_tree() -> None:
    if git("status", "--porcelain=v1", "--untracked-files=normal"):
        raise ValueError("Git working tree is not clean; commit changes before a benchmark run")


def run_dir(run_id: str) -> Path:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run ID must contain only letters, digits, hyphens, and underscores")
    return RUNS_ROOT / run_id


def dataset_digest(dataset: str) -> str:
    dataset_path = REPO_ROOT / "data" / dataset
    if not dataset_path.is_dir() or not (dataset_path / "csv").is_dir():
        raise ValueError(f"dataset does not exist: {dataset_path}")
    digest = hashlib.sha256()
    for path in sorted(p for p in dataset_path.rglob("*") if p.is_file()):
        relative = path.relative_to(dataset_path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def sanitized_endpoint(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def installed_dependencies(requirements: Path) -> dict[str, str | None]:
    versions = {}
    for line in requirements.read_text().splitlines():
        name = line.split("==", 1)[0].strip()
        if not name or name.startswith("#"):
            continue
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def config_from_args(args: argparse.Namespace) -> dict:
    return {
        "script": args.script,
        "dataset": args.dataset,
        "dataset_seed": args.seed,
        "remote_models": args.remote_models.split(),
        "local_models": args.local_models.split(),
        "suts": args.suts.split(),
        "repetitions": args.repetitions,
        "eval_njobs": args.eval_njobs,
        "cache_policy": args.cache_policy,
        "remote_endpoint": sanitized_endpoint(
            os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        ) if args.script == "full" else "",
        "local_api_base": sanitized_endpoint(
            os.environ.get("OLLAMA_API_BASE", "http://localhost:11434/v1")
        ) if args.script == "full" else "",
        "verbose": args.verbose,
        "row_order_invariant": True,
    }


def write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def load_manifest(directory: Path) -> dict:
    path = directory / "manifest.json"
    if not path.is_file():
        raise ValueError(f"no run manifest found: {path}")
    return json.loads(path.read_text())


def init_run(args: argparse.Namespace) -> None:
    require_clean_tree()
    directory = run_dir(args.run_id)
    config = config_from_args(args)
    digest = dataset_digest(args.dataset)
    commit = git("rev-parse", "HEAD")
    requirements = REPO_ROOT / "requirements.txt"
    requirements_digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    dependencies = installed_dependencies(requirements)
    if args.resume:
        manifest = load_manifest(directory)
        if manifest["status"] == "complete":
            raise ValueError(f"run {args.run_id} is already complete")
        for key, expected in (
            ("git_commit", commit),
            ("dataset_sha256", digest),
            ("requirements_sha256", requirements_digest),
            ("python_version", sys.version.split()[0]),
            ("installed_dependencies", dependencies),
            ("config", config),
        ):
            if manifest[key] != expected:
                raise ValueError(f"cannot resume {args.run_id}: {key} has changed")
        manifest["status"] = "running"
        manifest["resumed_at_utc"] = now_utc()
        write_manifest(directory / "manifest.json", manifest)
    else:
        directory.mkdir(parents=True, exist_ok=False)
        manifest = {
            "schema_version": 1,
            "run_id": args.run_id,
            "status": "running",
            "started_at_utc": now_utc(),
            "git_commit": commit,
            "dataset_sha256": digest,
            "requirements_sha256": requirements_digest,
            "python_version": sys.version.split()[0],
            "installed_dependencies": dependencies,
            "config": config,
            "completed_suts": [],
        }
        write_manifest(directory / "manifest.json", manifest)
    print(directory)


def mark_sut(args: argparse.Namespace) -> None:
    directory = run_dir(args.run_id)
    manifest = load_manifest(directory)
    if args.sut not in manifest["config"]["suts"]:
        raise ValueError(f"SUT not in run configuration: {args.sut}")
    dataset = manifest["config"]["dataset"]
    result_file = directory / args.sut / dataset / f"{args.sut}_results.csv"
    if not result_file.is_file():
        raise ValueError(f"evaluation results are missing: {result_file}")
    if args.sut not in manifest["completed_suts"]:
        manifest["completed_suts"].append(args.sut)
    write_manifest(directory / "manifest.json", manifest)


def finish_run(args: argparse.Namespace) -> None:
    directory = run_dir(args.run_id)
    manifest = load_manifest(directory)
    if args.status == "complete":
        missing = set(manifest["config"]["suts"]) - set(manifest["completed_suts"])
        if missing:
            raise ValueError(f"cannot complete run; unevaluated SUTs: {', '.join(sorted(missing))}")
        dataset = manifest["config"]["dataset"]
        for stem in ("evaluation_summary", "evaluation_by_file"):
            source = directory / f"{stem}_{dataset}.csv"
            if not source.is_file():
                raise ValueError(f"cannot complete run; missing summary: {source}")
    manifest["status"] = args.status
    manifest["finished_at_utc"] = now_utc()
    if args.status == "failed":
        manifest["exit_code"] = args.exit_code
    else:
        manifest.pop("exit_code", None)
    write_manifest(directory / "manifest.json", manifest)


def export_run(args: argparse.Namespace) -> None:
    directory = run_dir(args.run_id)
    manifest = load_manifest(directory)
    if manifest["status"] != "complete":
        raise ValueError("only complete runs can be exported")
    dataset = manifest["config"]["dataset"]
    sources = []
    for stem in ("evaluation_summary", "evaluation_by_file"):
        source = directory / f"{stem}_{dataset}.csv"
        if not source.is_file():
            raise ValueError(f"missing run summary: {source}")
        sources.append(source)
    destination = RECORDS_ROOT / args.run_id
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(directory / "manifest.json", destination / "manifest.json")
    for source in sources:
        shutil.copy2(source, destination / source.name)
    print(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check-clean")
    init = commands.add_parser("init")
    init.add_argument("--run-id", required=True)
    init.add_argument("--resume", action="store_true")
    init.add_argument("--script", choices=("full", "classical"), required=True)
    init.add_argument("--dataset", required=True)
    init.add_argument("--seed", type=int, required=True)
    init.add_argument("--remote-models", default="")
    init.add_argument("--local-models", default="")
    init.add_argument("--suts", required=True)
    init.add_argument("--repetitions", required=True)
    init.add_argument("--eval-njobs", type=int, required=True)
    init.add_argument("--cache-policy", choices=("cold", "cached", "none"), required=True)
    init.add_argument("--verbose", action="store_true")
    mark = commands.add_parser("mark-sut")
    mark.add_argument("--run-id", required=True)
    mark.add_argument("--sut", required=True)
    finish = commands.add_parser("finish")
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--status", choices=("complete", "failed"), required=True)
    finish.add_argument("--exit-code", type=int, default=0)
    export = commands.add_parser("export")
    export.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.command == "check-clean":
            require_clean_tree()
        elif args.command == "init":
            init_run(args)
        elif args.command == "mark-sut":
            mark_sut(args)
        elif args.command == "finish":
            finish_run(args)
        else:
            export_run(args)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
