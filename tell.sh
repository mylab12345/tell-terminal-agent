#!/usr/bin/env bash
# Cross-platform launcher for Tell (Unix/macOS).
# Usage: ./tell.sh [query]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer a local virtualenv if present.
if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python -m ai_terminal "$@"
fi

# Otherwise use system python.
if command -v python3 &>/dev/null; then
    exec python3 -m ai_terminal "$@"
elif command -v python &>/dev/null; then
    exec python -m ai_terminal "$@"
fi

echo "Python not found on PATH. Install Python 3.10+ first."
exit 1
