# Install and run FLIN on Linux (Ubuntu desktop tested as the primary development target)

Recommended: Ubuntu 24.04 desktop, Python 3.12 if available; Python 3.10+ is intended to work, but CI currently exercises 3.12. Tk requires a live graphical session, not a bare SSH shell.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-tk
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_environment.py
.venv/bin/python flin_desktop.py --cpu-info
.venv/bin/python flin_desktop.py
```

For optional PDF text extraction:

```bash
.venv/bin/python -m pip install -r requirements-optional.txt
```

For future launches use `./start_linux.sh` (which can install/update requirements), or `.venv/bin/python flin_desktop.py` without re-installing each time.

On a headless SSH server use CLI commands such as `--cpu-info`, `--list-networks`, `--flin-info`, `--flin-simulate "Graph theory"`; do not attempt to start the Tkinter GUI when `$DISPLAY` or Wayland graphics is unavailable. For remote GUI, configure X11 forwarding or a desktop-session remote display, accepting possible latency/security tradeoffs.

Build locally with `python scripts/build_native.py` after installing `requirements-build.txt`, or use the Linux artifact from GitHub Actions. Binary compatibility across Linux distributions is not guaranteed: the packaged program can still depend on system glibc, X11, Tk, and graphics libraries.

Linux data root: `~/.local/share/brain_project`, unless `BRAIN_DATA_DIR` is set. On Linux the collector attempts to respect CPU affinity/cgroup quotas; on Windows/macOS it falls back to worker counts.
