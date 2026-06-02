"""Tier 3 discovery driver.

Open-ended prompt: ask the LLM what's anomalous *beyond* the existing
flag taxonomy. The findings are clustered post-hoc to surface recurring
"novel" pollutions that should become v2 candidate flags.

A stratified random sample of ``--sample`` files is drawn from the Tier 1
parameter outputs, balanced across the four corpus origins (data.gov.uk,
github, hf, local) when available. Output is written to
``<out-dir>/discovery/<sha>.csv_discovery.json``; the cluster pass
(``cluster.py``) is invoked at the end to summarise.
"""

from __future__ import annotations

import json
import random
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from sut.utils import print as ts_print
from tqdm import tqdm

from ..config import RAND_SEED
from . import cluster as cluster_mod
from . import llm_client


_DISCOVER_HEAD = 60
_DISCOVER_TAIL = 20
_MAX_FINDINGS = 5


def _build_system_prompt(known_flags: list[str]) -> list[dict]:
    flag_list = "\n".join(f"  - {f}" for f in known_flags)
    intro = (
        "You are surveying real-world CSV files for novel pollution patterns "
        "that the existing taxonomy does NOT capture.\n\n"
        "You will receive a head/tail snippet of one CSV plus the existing "
        "Tier 1 flag set. Reply with a single JSON object containing "
        "``findings``: a list of up to "
        + str(_MAX_FINDINGS)
        + " short strings (≤ 100 chars each) describing pollutions you "
        "observe that are NOT already covered by the flag list below. "
        "If nothing novel is present, return an empty list.\n\n"
        "Examples of useful findings:\n"
        '  - "year column has 4-digit and 2-digit values mixed"\n'
        '  - "free-text column embeds JSON fragments"\n'
        '  - "rows alternate between two distinct schemas"\n'
        "Examples of bad findings (already covered — DO NOT include):\n"
        '  - "uses semicolon delimiter" (covered by table_not_comma_delimiter)\n'
        '  - "has a preamble" (covered by table_preamble_rows)\n\n"'
    )
    return [
        {"type": "text", "text": intro + "Existing flags:\n" + flag_list},
        {
            "type": "text",
            "text": (
                'JSON schema: {"findings": [string, ...]} — list ≤ '
                + str(_MAX_FINDINGS)
                + " strings, each ≤ 100 chars."
            ),
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _stratified_sample(records: list[tuple[str, dict]], n: int, seed: int) -> list[tuple[str, dict]]:
    """Approximate stratification by ``source_meta.origin``."""
    if n >= len(records):
        return records
    rng = random.Random(seed)
    by_origin: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for name, rec in records:
        origin = (rec.get("source_meta") or {}).get("origin") or "unknown"
        by_origin[origin].append((name, rec))
    per_origin = max(1, n // max(len(by_origin), 1))
    chosen: list[tuple[str, dict]] = []
    for items in by_origin.values():
        rng.shuffle(items)
        chosen.extend(items[:per_origin])
    if len(chosen) < n:
        # Top up randomly from the remainder.
        remainder = [r for r in records if r not in chosen]
        rng.shuffle(remainder)
        chosen.extend(remainder[: n - len(chosen)])
    rng.shuffle(chosen)
    return chosen[:n]


def _read_head_tail(path: Path, encoding: str) -> str:
    from ..detect import io_utils

    enc = encoding or "utf-8"
    head = io_utils.read_head_bytes(path, 1 << 20).decode(enc, errors="replace")
    full = io_utils.read_all_bytes(path, cap=8 * 1024 * 1024).decode(enc, errors="replace")
    head_lines = head.splitlines()[:_DISCOVER_HEAD]
    tail_lines = full.splitlines()[-_DISCOVER_TAIL:]
    return "\n".join(head_lines) + "\n# <SAMPLE_GAP> #\n" + "\n".join(tail_lines)


def _resolve_source_path(record: dict) -> Path | None:
    src = (record.get("source_meta") or {}).get("url") or ""
    if src.startswith("file://"):
        return Path(src[len("file://"):])
    local = (record.get("source_meta") or {}).get("local_path")
    if local:
        return Path(local)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_discover(args) -> int:
    from ..config import (
        ALL_ANNOTATION_FIELDS,
    )

    out_dir: Path = Path(args.out_dir).resolve()
    params_dir = out_dir / "parameters"
    discovery_dir = out_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)

    if not params_dir.is_dir():
        ts_print(f"[discover] no parameters directory at {params_dir}")
        return 1

    records: list[tuple[str, dict]] = []
    # rglob: tier1 outputs may be nested when input data is itself nested
    # (e.g. inside_airbnb mirrors country/region/city/date). Names are
    # relative paths so cross-dir basenames don't collide downstream.
    for path in sorted(params_dir.rglob("*_parameters.json")):
        try:
            with open(path) as f:
                records.append((str(path.relative_to(params_dir)), json.load(f)))
        except Exception:
            continue
    if not records:
        ts_print("[discover] no Tier 1 outputs to sample from")
        return 0

    seed = int(getattr(args, "seed", RAND_SEED))
    sample = _stratified_sample(records, int(args.sample), seed)
    ts_print(f"[discover] sampled {len(sample)} files (seed={seed})")

    try:
        backend = llm_client.build_backend(
            getattr(args, "backend", None),
            effort=getattr(args, "effort", None),
        )
    except (RuntimeError, ValueError) as exc:
        ts_print(f"[discover] {exc}")
        return 1
    ts_print(f"[discover] backend={backend.name}")

    system_prompt = _build_system_prompt(list(ALL_ANNOTATION_FIELDS))
    budget_usd = float(args.budget_usd)
    model = args.model
    jobs = max(1, int(getattr(args, "jobs", 1)))
    n_called = n_failed = 0
    t0 = time.time()

    show_progress = bool(getattr(args, "progress", True))

    # Pre-filter to work items whose source CSV is reachable; cheap, sequential.
    work: list[tuple[str, dict, Path, Path]] = []
    for name, record in sample:
        # Mirror the params subtree under discovery/ so a nested name like
        # ``argentina/.../listings.csv_parameters.json`` lands in a matching
        # nested ``..._discovery.json``.
        rel = Path(name)
        out_path = discovery_dir / rel.with_name(
            rel.name.replace("_parameters.json", "_discovery.json")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            continue
        source_path = _resolve_source_path(record)
        if source_path is None or not source_path.exists():
            continue
        work.append((name, record, source_path, out_path))

    stop_event = threading.Event()

    def _process(item: tuple[str, dict, Path, Path]):
        name, record, source_path, out_path = item
        if stop_event.is_set():
            return name, "skip", None
        encoding = record.get("encoding") or "utf-8"
        try:
            csv_text = _read_head_tail(source_path, encoding)
        except Exception:
            return name, "skip", None

        user_text = (
            "Tier 1 detector output:\n"
            + json.dumps(
                {"annotations": record.get("annotations"), "ambiguity_score": record.get("ambiguity_score")},
                indent=2,
            )
            + "\n\nCSV head/tail snippet:\n"
            + csv_text
        )

        try:
            result = llm_client.call_triage(
                backend=backend,
                model=model,
                system_prompt=system_prompt,
                user_text=user_text,
                out_dir=out_dir,
                budget_usd=budget_usd,
                max_tokens=600,
            )
        except llm_client.BudgetExceeded as exc:
            stop_event.set()
            return name, "budget", exc
        except llm_client.PolicyRefusal as exc:
            return name, "policy_refused", exc
        except Exception as exc:  # noqa: BLE001
            return name, "fail", exc

        findings = result.parsed.get("findings") or []
        if not isinstance(findings, list):
            findings = []
        out_record = {
            "source_filename": name.replace("_parameters.json", ""),
            "findings": [str(x)[:200] for x in findings][:_MAX_FINDINGS],
            "model": result.model,
            "cost_usd": result.cost_usd,
            "ran_at": _now_iso(),
        }
        with open(out_path, "w") as f:
            json.dump(out_record, f, sort_keys=True, indent=2)
        return name, "ok", None

    pbar = tqdm(total=len(work), desc="[discover]", unit="file", disable=not show_progress)
    if jobs == 1:
        for item in work:
            name, status, payload = _process(item)
            if status == "ok":
                n_called += 1
            elif status == "fail":
                tqdm.write(f"[discover] call failed for {name}: {payload!r}")
                n_failed += 1
            elif status == "budget":
                tqdm.write(f"[discover] {payload}; stopping")
                pbar.update(1)
                break
            pbar.update(1)
            ledger_now = llm_client._load_ledger(out_dir)
            pbar.set_postfix(ok=n_called, fail=n_failed, usd=f"{ledger_now['total_usd']:.2f}")
    else:
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            futures = {ex.submit(_process, item): item for item in work}
            for fut in as_completed(futures):
                name, status, payload = fut.result()
                if status == "ok":
                    n_called += 1
                elif status == "fail":
                    tqdm.write(f"[discover] call failed for {name}: {payload!r}")
                    n_failed += 1
                elif status == "budget":
                    tqdm.write(f"[discover] {payload}; stopping")
                pbar.update(1)
                ledger_now = llm_client._load_ledger(out_dir)
                pbar.set_postfix(ok=n_called, fail=n_failed, usd=f"{ledger_now['total_usd']:.2f}")

    pbar.close()
    elapsed = time.time() - t0
    ledger = llm_client._load_ledger(out_dir)
    ts_print(
        f"[discover] done: triaged={n_called}, failed={n_failed}, "
        f"elapsed={elapsed:.1f}s, total_usd=${ledger['total_usd']:.4f}"
    )

    # Cluster the free-text findings.
    cluster_path = cluster_mod.run_clustering(discovery_dir, out_dir / "discovery" / "clusters.md")
    if cluster_path is not None:
        ts_print(f"[discover] clusters.md → {cluster_path}")
    return 0
