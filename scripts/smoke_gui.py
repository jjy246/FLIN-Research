#!/usr/bin/env python3
"""Create and close FLIN's Tk window; run inside an isolated virtual display.

Linux CI example: xvfb-run -a python scripts/smoke_gui.py
This does NOT test all UI interactions or native Windows/macOS rendering.
"""
from __future__ import annotations
import os
import tempfile
import sys
from pathlib import Path


if __name__ == '__main__':
    # Set storage before importing the application. Never touch real user data.
    with tempfile.TemporaryDirectory(prefix='flin-smoke-') as directory:
        os.environ['BRAIN_DATA_DIR'] = str(Path(directory).resolve())
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import flin_desktop
        window = flin_desktop.ABCNetworkWindow()
        window.root.update_idletasks()
        print('FLIN window created:', window.root.title(), flush=True)
        window.root.after(200, window.close)
        window.root.mainloop()
        print('FLIN window closed successfully.', flush=True)
