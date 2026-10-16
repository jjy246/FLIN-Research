# FLIN command-line reference

Commands are run from the repository root. Replace `python` below with `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows PowerShell) to use the correct environment. Most commands access the current network and **may initialize tables on first use**.

## Basic information (safe to inspect)

```bash
python flin_desktop.py --help
python flin_desktop.py --cpu-info
python flin_desktop.py --diagnose
python flin_desktop.py --list-networks
python flin_desktop.py --source-info
python flin_desktop.py --catalog-info
python flin_desktop.py --math-coverage
python flin_desktop.py --flin-info
python flin_desktop.py --flin-source-report
python flin_desktop.py --flin-discovery-info
python flin_desktop.py --display-check
```

Use `--source-info` to check which providers are configured; use `--diagnose` for local databases, disk availability and a local Ollama status check. Some diagnostics make local service calls; no model download occurs automatically.

## Create, select and inspect networks

```bash
python flin_desktop.py --flin-create-network "FLIN experiment 001"
python flin_desktop.py --list-networks
python flin_desktop.py --flin-info
python flin_desktop.py --flin-clusters 10
python flin_desktop.py --switch-network NETWORK_ID
```

`--flin-create-network` creates a registered isolated SQLite database and activates FLIN. Ordinary `--new-network NAME` also creates a new network but may require `--flin-enable` separately. **Never directly change registry JSON or rename database files while FLIN is running.**

## Learn from existing sources

```bash
python flin_desktop.py --flin-enable
python flin_desktop.py --flin-learn-existing --flin-batch 100
python flin_desktop.py --flin-reconcile --flin-batch 100
python flin_desktop.py --flin-clusters 20
```

`--flin-learn-existing` learns **one batch** of source-backed material from papers already stored in the active database; rerun as appropriate to continue. It does not fetch arbitrary new research by itself. Reconcile can process pending clusters. Imported paper texts may be abstract-only.

## Simulate pulses

```bash
python flin_desktop.py --flin-simulate "Graph theory" \
  --flin-pulse-rate 18 --flin-duration 2 \
  --flin-threshold 2 --flin-window 0.25 --flin-revisits 2
```

The backslash is a Bash line continuation. **PowerShell:** put the command on one line (do not paste Bash backslashes):

```powershell
python flin_desktop.py --flin-simulate "Graph theory" --flin-pulse-rate 18 --flin-duration 2 --flin-threshold 2 --flin-window 0.25 --flin-revisits 2
```

The string must match a **stored active FLIN memory unit** (exact label or prefix). A Wikipedia article title existing somewhere on the Internet is insufficient. A missing match is expected on an empty graph.

## Import and export networks

**Full archival SQLite backup** (recommended before maintenance):

```bash
python flin_desktop.py --export-network "./backups" --export-format sqlite
```

Create the destination directory **first**. This command makes a new timestamped subfolder; no existing network is overwritten.

**Portable JSONL.gz interchange:**

```bash
python flin_desktop.py --export-network "./exports" --export-format portable
```

**Import a previously exported SQLite file / portable folder:**

```bash
python flin_desktop.py --import-network "PATH_TO_BACKUP_OR_PORTABLE_DIRECTORY" --network-name "Imported study"
```

The import stage performs schema and integrity checks and registers a *new* network; any external SQLite file should still be treated as potentially untrusted input. No paper PDFs or Ollama weights are shipped with exports by default.

For networks available through [GitHub Releases](https://github.com/jjy246/FLIN-Research-Desktop/releases), the desktop UI can list/download/import published `.sqlite3` assets under **Manage Networks → Browse Published Networks**. Manual downloads work with `--import-network` and are automatically activated by the CLI. To validate a snapshot before publishing as a **usable** FLIN associative network:

```bash
python scripts/inspect_network_snapshot.py /path/to/association.sqlite3 --require-flin
```

An enabled associative graph, active memory units and at least one usable directed link are necessary for this check. Successful structural validation is not a scientific or security certification.

## Academic catalog and indexes

```bash
python flin_desktop.py --catalog-search "stochastic control"
python flin_desktop.py --catalog-backfill-keys
python flin_desktop.py --catalog-import-network
python flin_desktop.py --build-fast-index
python flin_desktop.py --audit-math-quality --audit-limit 1000
python flin_desktop.py --purity-report
```

Large catalog operations can take time and disk space. `--build-fast-index` writes indexes. `--audit-math-quality` records a heuristic audit state; it does **not** certify mathematical correctness. **`--purity-clean` DELETES certain trivial stored nodes and associated links — back up first.**

## Console-only/SSH use

`--help`, `--cpu-info`, `--flin-info`, `--flin-clusters` and most maintenance flags run without a GUI display. Launching the application **without a subcommand** opens Tkinter and requires a desktop session. Avoid running a collector and a repair simultaneously against one active database.

The comprehensive flag list is always available through `--help`, which is more authoritative than this summary when options change.
