from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests._helpers import FakeCSVFile, load_polluters_module, make_csv_file


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root directory used by the tests."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def polluters_module_name() -> str:
    """Return the polluters module import path used by the test suite."""
    return "pollock.polluters_stdlib_v2"


@pytest.fixture(scope="session")
def polluters_module(polluters_module_name: str):
    """Import and return the polluters module under test."""
    return load_polluters_module(default=polluters_module_name)


@pytest.fixture
def csv_file() -> FakeCSVFile:
    """Build a small CSVFile-like fixture with one header row and two data rows."""
    return make_csv_file()
