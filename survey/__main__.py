"""Forward ``python -m survey`` to the fetch CLI.

The fetch CLI is the only user-facing entry point at this stage; running
``python -m survey`` is equivalent to ``python -m survey.fetch``.
"""

from .fetch.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
