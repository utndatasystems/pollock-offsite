"""Unit tests for ``_state.State`` (round-trip, atomic write, legacy migration)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from survey.fetch import _state
from survey.fetch._state import State


STATE_FILE = ".pollock_survey_state.json"


def test_round_trip_set_get_delete(tmp_path: Path) -> None:
    s = State(tmp_path)
    assert s.get("missing") is None
    assert s.get("missing", "fallback") == "fallback"

    s.set("key", {"a": 1, "b": 2})
    assert s.get("key") == {"a": 1, "b": 2}

    on_disk = json.loads((tmp_path / STATE_FILE).read_text())
    assert on_disk["key"] == {"a": 1, "b": 2}

    s.delete("key")
    assert s.get("key") is None
    assert "key" not in json.loads((tmp_path / STATE_FILE).read_text())


def test_set_uses_atomic_replace(tmp_path: Path) -> None:
    """Each mutation should go through ``os.replace`` exactly once."""
    s = State(tmp_path)
    real_replace = _state.os.replace
    with patch.object(_state.os, "replace", side_effect=real_replace) as m:
        s.set("a", 1)
        s.set("b", 2)
    assert m.call_count == 2


def test_persistence_across_instances(tmp_path: Path) -> None:
    s1 = State(tmp_path)
    s1.set("datagov_cursors", {"csv": "abc"})

    s2 = State(tmp_path)
    assert s2.get("datagov_cursors") == {"csv": "abc"}


def test_legacy_file_migration(tmp_path: Path) -> None:
    """All three legacy files merge into the new schema and get archived."""
    (tmp_path / ".fetch_state.json").write_text(json.dumps({"bytes_used": 12345}))
    (tmp_path / ".datagov_cursors.json").write_text(
        json.dumps({"csv": "cursor-token"})
    )
    (tmp_path / ".data_europa_eu_state.json").write_text(
        json.dumps({"next_page": 7})
    )

    s = State(tmp_path)

    assert s.get("bytes_used") == 12345
    assert s.get("datagov_cursors") == {"csv": "cursor-token"}
    assert s.get("data_europa_eu_next_page") == 7

    # Originals moved aside.
    assert not (tmp_path / ".fetch_state.json").exists()
    assert not (tmp_path / ".datagov_cursors.json").exists()
    assert not (tmp_path / ".data_europa_eu_state.json").exists()

    backup = tmp_path / ".legacy-state-backup"
    assert backup.is_dir()
    assert (backup / ".fetch_state.json").exists()
    assert (backup / ".datagov_cursors.json").exists()
    assert (backup / ".data_europa_eu_state.json").exists()


def test_legacy_migration_is_noop_when_absent(tmp_path: Path) -> None:
    s = State(tmp_path)
    s.set("k", "v")
    assert not (tmp_path / ".legacy-state-backup").exists()


def test_corrupt_existing_state_starts_empty(tmp_path: Path) -> None:
    (tmp_path / STATE_FILE).write_text("not valid json {")
    s = State(tmp_path)
    assert s.get("anything") is None
    s.set("k", 1)
    assert s.get("k") == 1
