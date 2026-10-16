# Install and run FLIN on macOS (Intel and Apple Silicon)

FLIN uses Tkinter/Tk, NumPy, Matplotlib, NetworkX and SQLite. It is intended to run on both **Intel x64** and **Apple Silicon arm64** macOS through their respective native Python installations and CI-built `.app` bundles. **Cross-platform GUI functionality is not independently verified on physical Macs in this release.**

## Option A — Install from source (recommended)

1. Install **Python 3.12 for macOS** from [python.org](https://www.python.org/downloads/macos/). The official installer includes Tk support; **do not use macOS's old Apple-supplied `/usr/bin/python`** for the GUI. You can verify Tk with `python3.12 -m tkinter` (should open a small test window).
2. Extract or clone this GitHub repository and open **Terminal** in the repository directory.
3. Run:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_environment.py
.venv/bin/python flin_desktop.py --help
.venv/bin/python flin_desktop.py
```

You can subsequently double-click `start_macos.command` from Finder. If Finder refuses to execute it because permission was removed by your ZIP extractor, run `bash start_macos.command` from Terminal. The launcher installs Python packages from PyPI before starting; inspect it first.

Optional open-access PDF text extraction:

```bash
.venv/bin/python -m pip install -r requirements-optional.txt
```

## Option B — GitHub Actions `.app` bundle

After publishing to GitHub, run **Actions → Build unsigned native desktop packages → Run workflow** and choose the artifact matching your processor:

- `FLIN-macos-intel-x64`: Intel processor.
- `FLIN-macos-apple-silicon-arm64`: Apple M-series processor.

Unzip and move `FLIN.app` to Applications or launch from the extracted folder. These are **unsigned, unnotarized experimental builds**; macOS may display a security prompt or refuse to run them until a trusted developer signs and notarizes the build. For public downloads, the maintainer should configure Apple Developer ID signing/notarization. Review the app source and use Apple's official security guidance; do not disable macOS security globally.

To build a native `.app` on your own Mac:

```bash
python3.12 -m pip install -r requirements-build.txt
python3.12 scripts/build_native.py
```

Result: `dist/FLIN.app`. Build Intel and Apple Silicon distributions on the relevant architecture. PyInstaller is **not a cross-compiler**.

## macOS-specific notes

- Fresh-install data: `~/Library/Application Support/FLIN/BrainProject` unless overridden; the old `~/.local/share/brain_project` data directory remains selected if it already exists.
- Tkinter's Aqua rendering and trackpad interaction can differ from Linux. The 3D viewer is an interactive Matplotlib figure, not a hardware-accelerated game engine.
- Python installed through a different package manager may use a different Tk library; try the official Python installer if you see blank or frozen GUI windows.
- For Apple Silicon, install the matching native Python and packages to avoid accidental Rosetta/x64 dependency mixing.
- A `.app` contains its Python runtime but **does not include Ollama, model weights, API keys or research data**. Install Ollama separately when needed.

Next: [Complete User Guide](USER_GUIDE.md) → [Theory](FLIN_THEORY.md).
