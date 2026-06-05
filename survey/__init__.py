"""Pollock CSV-pollution survey pipeline.

Top-level entry point: ``python -m survey`` (forwards to the fetch CLI;
``python -m survey.fetch <backend>`` is the canonical invocation).
"""

from .config import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION"]
