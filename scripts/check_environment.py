#!/usr/bin/env python3
"""Non-destructive cross-platform FLIN environment and dependency diagnostics."""
from __future__ import annotations
import importlib.util
import os
import platform
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print('FLIN environment check (no external network requests)')
    print('OS:', platform.platform())
    print('Python:', sys.version.split()[0], '(' + sys.executable + ')')
    print('Source root:', root)
    result = 0
    for module in ('tkinter', 'numpy', 'matplotlib', 'networkx', 'requests', 'bs4', 'sklearn'):
        found = importlib.util.find_spec(module) is not None
        print(f'{module:<14}:', 'OK' if found else 'MISSING')
        if not found:
            result = 1
    try:
        con = sqlite3.connect(':memory:')
        con.execute('CREATE VIRTUAL TABLE ft USING fts5(content)')
        con.close()
        print('SQLite FTS5     : OK')
    except sqlite3.DatabaseError:
        print('SQLite FTS5     : UNAVAILABLE (local catalog search will fail)')
        result = 1
    print('Optional PyMuPDF:', 'available' if importlib.util.find_spec('fitz') else 'not installed')
    print('GUI Tk version : run "python -m tkinter" in a graphical session')
    print('Data override  :', os.environ.get('BRAIN_DATA_DIR', '(use OS default)'))
    print('No GUI window, Ollama call, network request, or database migration was performed.')
    return result


if __name__ == '__main__':
    raise SystemExit(main())
