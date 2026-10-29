# Tests

Run the suite from the repository root with:

```bash
.venv/bin/python -m pytest tests
```

Layout:
- `tests/pollution/`: pollution operator tests
- `tests/unit/`: helper, metrics, and data-generation tests
- `tests/process/`: process and CLI tests
- `tests/sut/`: parser and LLM backend tests

The goal is to keep the test surface small, explicit, and easy to grow.
