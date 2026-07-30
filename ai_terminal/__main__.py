"""Entry point so the agent can be run with `python -m ai_terminal`."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())