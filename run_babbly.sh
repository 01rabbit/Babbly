#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Warning: run_babbly.sh is the Mac-first development launcher."
fi

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Create it first with:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  python -m pip install --upgrade pip"
  echo "  python -m pip install pipenv"
  echo "  pipenv requirements > /tmp/babbly-requirements.txt"
  echo "  python -m pip install -r /tmp/babbly-requirements.txt"
  exit 2
fi

source .venv/bin/activate

MODE="${1:-ja}"
case "$MODE" in
  ja)
    exec python babbly_ja.py
    ;;
  en)
    exec python babbly_en.py
    ;;
  test)
    exec python -m pytest -q tests
    ;;
  *)
    echo "Usage: ./run_babbly.sh [ja|en|test]"
    exit 2
    ;;
esac
