#!/usr/bin/env bash
# ============================================================
# PaperSummar - one-command launcher (macOS / Linux)
# Python detection only; the heavy lifting is in scripts/launch.py.
# Override python with:  PAPERSUMMAR_PYTHON=/path/to/python3 ./start.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo "[1/4] Checking Python ..."
PYBIN="${PAPERSUMMAR_PYTHON:-}"
if [ -z "$PYBIN" ]; then
  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
      PYBIN="$cand"
      break
    fi
  done
fi
if [ -z "$PYBIN" ]; then
  echo "[ERROR] Python 3.11+ not found. Set PAPERSUMMAR_PYTHON to a python3 binary."
  exit 1
fi
echo "      Using Python: $PYBIN"

echo "[2/4] Running setup and launch ..."
exec "$PYBIN" "$(pwd)/scripts/launch.py"
