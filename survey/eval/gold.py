"""Gold-set loading + stub generation.

Gold annotations live in ``<out-dir>/gold/<sha>.csv_parameters.json``
using the same schema as the Tier 1 outputs. The plan calls for ~75
hand-annotated files; the actual labelling is human work, but this
module provides:

- ``load_gold(dir)``: read all gold files, return ``{filename: record}``.
- ``stub_from_tier1(...)``: pre-fill a gold candidate from a Tier 1
  output so the annotator only has to confirm/override values.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def load_gold(gold_dir: Path) -> dict[str, dict]:
    """Read every ``*_parameters.json`` under ``gold_dir`` (recursively).

    Keys are paths relative to ``gold_dir`` so they line up with the
    relative-path keys produced by ``scorer._load_tier1``. Gold trees
    that are flat (the historical layout) still produce bare basenames,
    matching flat tier1 outputs.
    """
    if not gold_dir.is_dir():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(gold_dir.rglob("*_parameters.json")):
        try:
            with open(path) as f:
                record = json.load(f)
        except Exception:
            continue
        out[str(path.relative_to(gold_dir))] = record
    return out


def stub_from_tier1(tier1_path: Path, gold_dir: Path) -> Path:
    """Pre-fill a gold annotation from a Tier 1 output.

    Copy ``<sha>.csv_parameters.json`` into ``gold_dir/`` and tag it as
    ``schema_version=2`` plus ``gold_status="needs_review"`` in the
    ``tier_provenance`` block. The human annotator then overrides any
    values they disagree with and removes the ``needs_review`` tag.
    """
    gold_dir.mkdir(parents=True, exist_ok=True)
    dst = gold_dir / tier1_path.name
    shutil.copyfile(tier1_path, dst)
    with open(dst) as f:
        record = json.load(f)
    prov = record.setdefault("tier_provenance", {})
    prov["gold_status"] = "needs_review"
    with open(dst, "w") as f:
        json.dump(record, f, sort_keys=True, indent=4)
    return dst
