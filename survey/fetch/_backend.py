"""``Backend`` Protocol shared by every fetch backend module.

Using ``Protocol`` (rather than an ABC) means each backend is just a module
with four module-level attributes — no class boilerplate, no MRO surprises.
The Phase 5 / 6 rewrites populate ``BACKENDS`` in ``survey/fetch/__init__.py``
with the modules themselves.
"""

from __future__ import annotations

import argparse
from typing import Protocol, runtime_checkable

from .config import BackendOptions


@runtime_checkable
class Backend(Protocol):
    name: str

    def add_subparser(self, sp: argparse._SubParsersAction) -> argparse.ArgumentParser: ...

    def options_from_args(self, args: argparse.Namespace) -> BackendOptions: ...

    def run(self, opts: BackendOptions) -> int: ...
