"""Line-level pollution scanner.

A stripped-down sibling of ``survey.detect`` that scans a directory of CSV
files for a fixed subset of pollutions and emits one JSON file per defect
listing the affected files and line numbers.

Invocation::

    python -m survey scan --in <dir> [--jobs N] [--out-dir <out>]

Output layout (under ``<out-dir>/scan/<dataset-prefix>/``)::

    comments.json
    long_fields.json
    variable_columns.json
    mixed_delimiter.json
    header_mismatch.json
    unquoted_multiline.json
    encoding_issues.json
    null_mismatch.json
    summary.json
"""

from __future__ import annotations


def run_scan(args) -> int:
    from .runner import run_scan as _run

    return _run(args)
