#!/usr/bin/env bash
# On Debian/Ubuntu install python3-venv and python3-tk first.
set -euo pipefail
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python flin_desktop.py
