#!/usr/bin/env python3
"""Build an unsigned, platform-native FLIN desktop bundle on THIS OS."""
from __future__ import annotations
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if importlib_missing('PyInstaller'):
        print('Install build dependencies: python -m pip install -r requirements-build.txt', file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[1]
    args = [
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onedir', '--windowed', '--name', 'FLIN',
        '--collect-data', 'matplotlib',
        str(root / 'flin_desktop.py'),
    ]
    print('Building on', platform.platform(), '(no cross-compilation supported)', flush=True)
    print('Command:', ' '.join(args), flush=True)
    subprocess.run(args, cwd=root, check=True)
    path = root / 'dist' / ('FLIN.app' if sys.platform == 'darwin' else 'FLIN')
    print('Native bundle:', path)
    print('NOTE: macOS bundles are unsigned and not notarized; this is NOT a signed installer.')
    return 0


def importlib_missing(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is None


if __name__ == '__main__':
    raise SystemExit(main())
