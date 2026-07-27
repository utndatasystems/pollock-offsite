from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


ComparisonMode = Literal["single_table", "ordered_tables", "unordered_tables"]
_VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _validate_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not _VALID_ID.fullmatch(value):
        raise ValueError(
            f"{field} must start with an alphanumeric character and contain only "
            "letters, numbers, underscores, or hyphens"
        )


def _freeze_rows(rows: Iterable[Iterable[object]]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple("" if value is None else str(value) for value in row)
        for row in rows)


@dataclass(frozen=True)
class GroundTruthTable:
    id: str
    rows: tuple[tuple[str, ...], ...]
    role: str = "primary"

    @classmethod
    def from_rows(
        cls,
        id: str,
        rows: Iterable[Iterable[object]],
        role: str = "primary",
    ) -> "GroundTruthTable":
        _validate_id(id, "table id")
        return cls(id=id, rows=_freeze_rows(rows), role=role)


@dataclass(frozen=True)
class GroundTruthAlternative:
    id: str
    table_ids: tuple[str, ...]
    comparison: ComparisonMode = "single_table"

    def __post_init__(self) -> None:
        _validate_id(self.id, "alternative id")
        if not self.table_ids:
            raise ValueError("A ground-truth alternative must reference at least one table")
        if self.comparison not in {
            "single_table",
            "ordered_tables",
            "unordered_tables",
        }:
            raise ValueError(f"Invalid ground-truth comparison mode: {self.comparison}")
        if self.comparison == "single_table" and len(self.table_ids) != 1:
            raise ValueError("single_table alternatives must reference exactly one table")


@dataclass(frozen=True)
class GroundTruthBundle:
    tables: tuple[GroundTruthTable, ...]
    alternatives: tuple[GroundTruthAlternative, ...]
    canonical: str
    accept_origin: bool = False

    def __post_init__(self) -> None:
        table_ids = [table.id for table in self.tables]
        for table_id in table_ids:
            _validate_id(table_id, "table id")
        alternative_ids = [alternative.id for alternative in self.alternatives]
        if len(table_ids) != len(set(table_ids)):
            raise ValueError("Ground-truth table ids must be unique")
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError("Ground-truth alternative ids must be unique")
        if self.canonical not in alternative_ids:
            raise ValueError("canonical must reference an existing alternative")

        known_tables = set(table_ids)
        for alternative in self.alternatives:
            unknown = set(alternative.table_ids) - known_tables
            if unknown:
                raise ValueError(
                    f"Alternative {alternative.id} references unknown tables: "
                    f"{sorted(unknown)}"
                )

    @classmethod
    def single(
        cls,
        rows: Iterable[Iterable[object]],
        *,
        table_id: str = "primary",
        alternative_id: str = "canonical",
        accept_origin: bool = False,
    ) -> "GroundTruthBundle":
        return cls(
            tables=(GroundTruthTable.from_rows(table_id, rows),),
            alternatives=(
                GroundTruthAlternative(
                    id=alternative_id,
                    table_ids=(table_id,),
                    comparison="single_table",
                ),
            ),
            canonical=alternative_id,
            accept_origin=accept_origin,
        )

    def write(self, root: str | Path, filename: str) -> Path:
        bundle_dir = Path(root) / filename
        bundle_dir.mkdir(parents=True, exist_ok=True)

        table_entries = {}
        for table in self.tables:
            table_filename = f"{table.id}.csv"
            table_path = bundle_dir / table_filename
            with table_path.open("w", encoding="utf-8", newline="") as stream:
                csv.writer(stream, dialect="unix").writerows(table.rows)
            table_entries[table.id] = {
                "path": table_filename,
                "role": table.role,
            }

        manifest = {
            "schema_version": 1,
            "canonical": self.canonical,
            "accept_origin": self.accept_origin,
            "tables": table_entries,
            "alternatives": [
                {
                    "id": alternative.id,
                    "comparison": alternative.comparison,
                    "tables": list(alternative.table_ids),
                }
                for alternative in self.alternatives
            ],
        }
        manifest_path = bundle_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return manifest_path


def load_ground_truth_manifest(path: str | Path) -> dict:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError(
            f"Unsupported ground-truth schema version: {manifest.get('schema_version')}"
        )

    tables = manifest.get("tables")
    alternatives = manifest.get("alternatives")
    canonical = manifest.get("canonical")
    accept_origin = manifest.get("accept_origin", False)
    if not isinstance(tables, dict) or not tables:
        raise ValueError("Ground-truth manifest must define tables")
    if not isinstance(alternatives, list) or not alternatives:
        raise ValueError("Ground-truth manifest must define alternatives")
    if not isinstance(accept_origin, bool):
        raise ValueError("Ground-truth accept_origin must be a boolean")

    alternative_ids = set()
    for alternative in alternatives:
        if not isinstance(alternative, dict):
            raise ValueError("Ground-truth alternatives must be objects")
        alternative_id = alternative.get("id")
        _validate_id(alternative_id, "alternative id")
        if alternative_id in alternative_ids:
            raise ValueError(
                f"Ground-truth alternative id is duplicated: {alternative_id}"
            )
        alternative_ids.add(alternative_id)
        table_ids = alternative.get("tables")
        if not isinstance(table_ids, list) or not table_ids:
            raise ValueError(f"Alternative {alternative_id} must reference tables")
        unknown = set(table_ids) - set(tables)
        if unknown:
            raise ValueError(
                f"Alternative {alternative_id} references unknown tables: "
                f"{sorted(unknown)}"
            )
        comparison = alternative.get("comparison")
        if comparison not in {"single_table", "ordered_tables", "unordered_tables"}:
            raise ValueError(
                f"Alternative {alternative_id} has invalid comparison mode: {comparison}"
            )
        if comparison == "single_table" and len(table_ids) != 1:
            raise ValueError(
                f"Alternative {alternative_id} uses single_table with multiple tables"
            )

    if canonical not in alternative_ids:
        raise ValueError("Ground-truth canonical id is not an alternative")

    for table_id, table in tables.items():
        _validate_id(table_id, "table id")
        if not isinstance(table, dict):
            raise ValueError(f"Ground-truth table {table_id} must be an object")
        relative_path = Path(table.get("path", ""))
        if (
            not relative_path.name
            or relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise ValueError(f"Unsafe ground-truth table path: {relative_path}")
        table_path = manifest_path.parent / relative_path
        if not table_path.is_file():
            raise FileNotFoundError(
                f"Missing ground-truth table {table_id}: {table_path}"
            )

    return manifest


def single_table_alternatives(
    path: str | Path,
) -> list[tuple[str, Path]]:
    manifest_path = Path(path)
    manifest = load_ground_truth_manifest(manifest_path)
    candidates = []
    for alternative in manifest["alternatives"]:
        if alternative["comparison"] != "single_table":
            continue
        table_id = alternative["tables"][0]
        table_path = manifest_path.parent / manifest["tables"][table_id]["path"]
        candidates.append((alternative["id"], table_path))
    return candidates


def manifest_accepts_origin(path: str | Path) -> bool:
    return bool(load_ground_truth_manifest(path).get("accept_origin", False))
