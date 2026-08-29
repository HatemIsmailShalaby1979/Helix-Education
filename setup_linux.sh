#!/usr/bin/env bash
# Helix Education - Linux/macOS setup
# Requires Python 3.11+ (falls back to python3 if 3.11 is unavailable).
set -euo pipefail

echo "============================================"
echo "  Helix Education - Linux/macOS Setup"
echo "============================================"

PYTHON_BIN="$(command -v python3.11 || command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: python3.11 (or python3) not found in PATH." >&2
  exit 1
fi

PY_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[0])')"
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[1])')"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  echo "ERROR: Helix Education requires Python 3.11+ (found $PY_MAJOR.$PY_MINOR)." >&2
  exit 1
fi
echo "[1/3] Using $("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"

if [ ! -f ".venv/bin/activate" ]; then
  echo "[2/3] Creating virtual environment (.venv)..."
  "$PYTHON_BIN" -m venv .venv || { echo "ERROR: failed to create .venv" >&2; exit 1; }
else
  echo "[2/3] Reusing existing .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "[3/3] Installing project + dev dependencies..."
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" || { echo "ERROR: dependency install failed" >&2; exit 1; }

echo "============================================"
echo "  Setup complete."
echo "  Run tests with:  python -m pytest -q"
echo "============================================"
