# Tests

This directory contains the real pytest surface for the repo.

Layout:
- `tests/pollock/test_polluters_v2.py`: current Pollock 2.0 coverage
- `tests/pollock/test_polluters_v1.py`: placeholder for Pollock 1.0 coverage
- `tests/unit/`: low-level helper and data-generation tests
- `tests/process/`: end-to-end process and CLI tests

The goal is to keep the test surface small, explicit, and easy to grow.
