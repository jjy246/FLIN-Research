# Troubleshooting (Linux, Windows, macOS)

Start with `python scripts/check_environment.py`, `python flin_desktop.py --cpu-info`, and `python flin_desktop.py --diagnose`. On Windows use `.venv\Scripts\python.exe`; on macOS/Linux use `.venv/bin/python`.

| Symptom | Likely cause | Recommended action |
| --- | --- | --- |
| `ModuleNotFoundError: matplotlib` / `networkx` / `sklearn` | Wrong Python environment or missing install | Create `.venv`; install `requirements.txt` with that interpreter |
| `No module named _tkinter` | Python lacks Tk support | Ubuntu: `sudo apt install python3-tk`; macOS: official python.org Python; Windows: reinstall official Python with Tk support |
| `TclError: no display name and no $DISPLAY` | Running GUI from headless SSH | Use CLI flags only; or use remote desktop/X11 forwarding with a valid display |
| macOS GUI freezes immediately | Tcl/Tk/python package mismatch | Verify `python3.12 -m tkinter` then install from official Python macOS package |
| Windows `.bat` flashes and closes | Launcher failed to find Python/dependency | Run from cmd/PowerShell to read the error, or install Python 3.12 |
| “Windows protected your PC” / macOS unidentified developer | Native binary unsigned | Source-install or verify/release a signed/notarized build; do not disable device security globally |
| GitHub build succeeded but `.app` does not open | Tk/macOS bundle packaging/runtime issue | Inspect GitHub Actions logs; test on physical Mac; rebuild/sign/notarize as needed |
| 3D graph is blank/slow | No accepted units, backend/display issue, or too many samples | Run `--flin-info`, use smaller `BRAIN_OVERVIEW_NODES`, inspect selected graph |
| FLIN pulse produces no result | Query does not match a stored active label, or node has no exits | Inspect `--flin-clusters` / `--flin-info`; use exact stored concept; verify network was trained |
| No paper found / provider errors | Offline or quotas/terms/provider changes | Check network access and `--source-info`; reduce workers; retry without claiming data completeness |
| PDF extraction absent | Optional `PyMuPDF` missing, not an OA PDF or download blocked | `pip install -r requirements-optional.txt` and check source depth; never bypass paywalls |
| Ollama connection error | Ollama server/model absent | Install/start Ollama, `ollama list`, pull the configured model, retry |
| Ollama out-of-memory | Model, batch/context too large | Choose a smaller installed model, reduce context; leave calls serialized |
| `database is locked` | Competing writers/maintenance | Stop competing collector jobs, then retry; preserve DB/WAL, do not delete ad hoc |
| Storage fills up | Huge paper budgets, PDF reading, indexes, backups | Stop build, export/inspect safely, reduce caps and sample sizes |
| Mismatched memories after switching | Wrong active network | Run `--list-networks`, switch by exact ID, run `--flin-info` |
| `fts5` missing | SQLite compiled without FTS5 | Install an appropriate Python/SQLite distribution; rerun environment check |

## Data restoration

Use the application's **Import Network** workflow or `--import-network` with a full saved SQLite snapshot. The importer validates core tables and SQLite integrity. Keep the original backup intact and test a new network first. If data is missing after an OS migration, examine both the **native OS default** and the **legacy Linux-style data path**, plus any `BRAIN_DATA_DIR` value.

## Collecting a useful bug report

Include OS/version and architecture (e.g., Windows x64, Mac M2 arm64), Python version, FLIN commit SHA, invoked command, the last traceback **with secrets removed**, observed versus expected behavior, model tags (if relevant), and whether the bug reproduces on a fresh empty network. Do not attach private source PDFs, SQLite databases or API keys publicly.
