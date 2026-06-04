"""Atomic JSON key-value store for fetch-stage cursors and counters.

Replaces the per-backend dotfiles (``.fetch_state.json``,
``.datagov_cursors.json``, ``.data_europa_eu_state.json``) with a single
``<out_dir>/.pollock_survey_state.json``. Writes are eager: every ``set``
re-encodes and ``os.replace``s the file so a killed run never leaves a
corrupt JSON behind.

On first instantiation the legacy files are merged into the new schema
(keys ``bytes_used``, ``datagov_cursors``, ``data_europa_eu_next_page``)
and the originals are moved under ``<out_dir>/.legacy-state-backup/``
as a recovery snapshot.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

_STATE_FILENAME = ".pollock_survey_state.json"
_LEGACY_BACKUP_DIR = ".legacy-state-backup"
_LEGACY_FETCH_STATE = ".fetch_state.json"
_LEGACY_DATAGOV_CURSORS = ".datagov_cursors.json"
_LEGACY_DATA_EUROPA_EU_STATE = ".data_europa_eu_state.json"


class State:
    """Atomic JSON KV store at ``<out_dir>/.pollock_survey_state.json``."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.path = out_dir / _STATE_FILENAME
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                with open(self.path) as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data = loaded
            except (OSError, json.JSONDecodeError):
                self._data = {}
        self._migrate_legacy()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._persist()

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._persist()

    def flush(self) -> None:
        # Writes are eager; kept for API symmetry.
        self._persist()

    def _persist(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=str(self.out_dir)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, sort_keys=True, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def _migrate_legacy(self) -> None:
        """One-shot read-and-rewrite of the three legacy state files.

        Merges into ``self._data`` under stable keys, snapshots the originals
        under ``.legacy-state-backup/``, then removes them. Idempotent: if the
        legacy files don't exist, this is a no-op.
        """
        legacy_files = (
            _LEGACY_FETCH_STATE,
            _LEGACY_DATAGOV_CURSORS,
            _LEGACY_DATA_EUROPA_EU_STATE,
        )
        present = [n for n in legacy_files if (self.out_dir / n).exists()]
        if not present:
            return

        changed = False
        for name in present:
            src = self.out_dir / name
            try:
                with open(src) as f:
                    payload = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if name == _LEGACY_FETCH_STATE and isinstance(payload, dict):
                if "bytes_used" not in self._data and "bytes_used" in payload:
                    try:
                        self._data["bytes_used"] = int(payload["bytes_used"])
                        changed = True
                    except (TypeError, ValueError):
                        pass
            elif name == _LEGACY_DATAGOV_CURSORS and isinstance(payload, dict):
                if "datagov_cursors" not in self._data:
                    self._data["datagov_cursors"] = {
                        str(k): str(v) for k, v in payload.items() if v is not None
                    }
                    changed = True
            elif name == _LEGACY_DATA_EUROPA_EU_STATE and isinstance(payload, dict):
                if (
                    "data_europa_eu_next_page" not in self._data
                    and payload.get("next_page") is not None
                ):
                    try:
                        self._data["data_europa_eu_next_page"] = int(payload["next_page"])
                        changed = True
                    except (TypeError, ValueError):
                        pass

        backup_dir = self.out_dir / _LEGACY_BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        for name in present:
            src = self.out_dir / name
            dst = backup_dir / name
            try:
                shutil.copy2(src, dst)
                src.unlink()
            except OSError:
                # Best-effort: leave the source in place if backup fails;
                # next run will retry.
                continue

        if changed:
            self._persist()
