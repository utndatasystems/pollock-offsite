"""Logging setup for ``survey.fetch``.

Replaces the previous ``from sut.utils import print as ts_print`` import,
which couples the fetch package to the parent project's logger and breaks
fresh checkouts. Uses stdlib :mod:`logging` exclusively so the package
imports cleanly without ``sut`` on the path.

Output style mirrors ``sut.utils.print``: an ANSI-blue ``HH:MM:SS:`` prefix
followed by the message. Console colour is auto-disabled when stderr is
not a TTY (e.g. when redirected to a file or captured by CI).

Environment variables
---------------------
``POLLOCK_SURVEY_LOG_LEVEL``
    Logger level. Accepts standard names (``DEBUG``/``INFO``/``WARNING``/
    ``ERROR``). Defaults to ``INFO``.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime


_BLUE = "\033[94m"
_RESET = "\033[0m"
_ROOT_NAME = "survey.fetch"
_ENV_LEVEL = "POLLOCK_SURVEY_LOG_LEVEL"
_configured = False


class _TimePrefixFormatter(logging.Formatter):
    """Format records as ``HH:MM:SS: <message>`` with optional ANSI colour."""

    def __init__(self, *, use_colour: bool) -> None:
        super().__init__()
        self._use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        prefix = f"{_BLUE}{ts}:{_RESET}" if self._use_colour else f"{ts}:"
        return f"{prefix} {record.getMessage()}"


def _configure_root() -> None:
    """Attach a single stderr handler to ``survey.fetch`` once."""
    global _configured
    if _configured:
        return
    root = logging.getLogger(_ROOT_NAME)
    if not root.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(_TimePrefixFormatter(use_colour=sys.stderr.isatty()))
        root.addHandler(handler)
    level_name = (os.environ.get(_ENV_LEVEL) or "INFO").upper()
    root.setLevel(getattr(logging, level_name, logging.INFO))
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``survey.fetch`` namespace.

    ``name`` may be a bare suffix (``"datagov"``) or a fully-qualified name
    (``"survey.fetch.datagov"``). Either way the returned logger lives below
    ``survey.fetch`` so it inherits the configured handler and level.
    """
    _configure_root()
    if name == _ROOT_NAME or name.startswith(_ROOT_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


def set_level(level: int | str) -> None:
    """Override the package log level at runtime (e.g. from CLI flags)."""
    _configure_root()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger(_ROOT_NAME).setLevel(level)
