#!/bin/bash
# Double-click in Finder, or run: bash start_macos.command
set -e
cd "$(dirname "$0")"
PY="$(command -v python3.12 || command -v python3)"
if [ -z "$PY" ]; then
  echo 'Python 3.12 is missing; install the official python.org macOS package.'
  exit 1
fi
if [ ! -x .venv/bin/python ]; then "$PY" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python flin_desktop.py
