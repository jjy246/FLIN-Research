# Install and run FLIN on Windows 10/11 (x64)

FLIN's desktop interface is a Python/Tk application, and the bundled Windows release is a native `.exe` built from that same code. **Windows has not been manually GUI-tested by the project packager;** GitHub Actions is configured to test and build on Windows. See [platform verification](PLATFORM_SUPPORT.md).

## Option A — Source install (recommended for research and debugging)

1. Download the repository as ZIP from **Code → Download ZIP**, or use `git clone YOUR_GITHUB_REPO_URL`. Extract it to a normal directory. Do not execute files from inside a compressed archive.
2. Install **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/windows/). Enable the Python Launcher if offered. A graphical Windows desktop session is required.
3. Install [Ollama for Windows](https://ollama.com/download/windows) only if you want model-assisted question generation. FLIN pulse routing itself does not need Ollama.
4. Double-click `start_windows.bat`. It creates `.venv` if missing, installs requirements, and launches the program. **It accesses PyPI** to install dependencies. Review the script before running it.
5. Alternatively, open **PowerShell** in the repository directory and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe flin_desktop.py --help
.\.venv\Scripts\python.exe flin_desktop.py
```

If your Windows installation uses a different supported Python command, substitute it for `py -3.12` (but Python **3.12** is the tested CI version).

## Option B — Windows `.exe` from GitHub Actions

When the repository is on GitHub, select **Actions → Build unsigned native desktop packages → Run workflow**. Download the `FLIN-windows-x64` artifact, unzip it, then open the **`FLIN` folder and run `FLIN.exe` inside it**. Keep all companion files inside that folder. The artifact is a **portable, unsigned folder application**, not an installer. The developer must code-sign releases separately if needed.

To package locally on Windows:

```powershell
py -3.12 -m pip install -r requirements-build.txt
py -3.12 scripts\build_native.py
```

The result is `dist\FLIN\FLIN.exe`. PyInstaller does **not** produce a Windows `.exe` by running on Linux or macOS.

## Windows-specific notes

- Local data: `%LOCALAPPDATA%\FLIN\BrainProject` for fresh installs, unless `BRAIN_DATA_DIR` overrides it or a legacy `~/.local/share/brain_project` directory already exists. Database files and exports are **not** included in GitHub packages.
- Before importing someone else's database, make a backup of your local data; **imports use isolated storage**, but some maintenance actions delete data.
- `Ctrl+C` in an open CLI terminal interrupts terminal commands; use **Stop & Save** in the GUI for ongoing builds.
- If opening the program displays an error, rerun in PowerShell to see the traceback.
- If package installation is blocked, check network/proxy settings; installing from source requires access to PyPI.
- Ollama listens on a local service (normally `localhost:11434`). Keep the service running during question generation; install models explicitly with `ollama pull`.
- Windows and macOS do not have Linux CPU-affinity APIs; FLIN falls back to worker limits, so CPU budget readouts are estimates.

Next: [Complete User Guide](USER_GUIDE.md) → [Theory](FLIN_THEORY.md).
