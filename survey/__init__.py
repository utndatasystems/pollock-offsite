"""Pollock CSV-pollution survey pipeline.

Top-level entry point: ``python -m survey <subcommand>`` (see ``cli.py``).
"""

from .config import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION"]
