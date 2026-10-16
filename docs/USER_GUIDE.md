# FLIN Desktop — complete user and operating manual

This manual explains **what to click, why each operation exists, what changes in storage, what output means, and how to avoid making false scientific claims**. Begin with [the installation guide for your OS](PLATFORM_SUPPORT.md) and the [theory](FLIN_THEORY.md).

## 0. Understand the system before clicking “Build”

The research workflow is **source → effective input cluster → accepted memory units → learned directed links → pulse simulation → observed response**, with optional **local-model question drafting** afterward. FLIN is a **mathematics-focused, exploratory prototype**, not a proof engine or a general chatbot.

FLIN stores **two different graphs**. The literature/evidence graph (`units` and `edges`) is for reading and auditing research sources; the associative FLIN graph (`abc_units` and `abc_edges`) is for pulse routing. The strength of an association **does not verify a mathematical implication**. A question model score **does not certify novelty**. Many paths are stochastic: results may change with simulation seed.

## 1. Prepare the environment

Install Python 3.12, the dependencies in `requirements.txt`, and the GUI toolkit for your OS. Run:

```bash
python scripts/check_environment.py
python flin_desktop.py --cpu-info
python flin_desktop.py --diagnose
```

On Windows use `.venv\Scripts\python.exe` in PowerShell; on macOS/Linux use `.venv/bin/python`. GUI requires a graphical session; the `--help`, `--cpu-info` and diagnostic CLI options are headless. Ollama is **optional** until question generation.

### Separate the experimental data from source code

A fresh installation stores databases under the OS-specific application-data directory; see [Data & Safety](DATA_AND_SAFETY.md). Configure `BRAIN_DATA_DIR` *before launching* to choose a different location. Never upload `.sqlite3`, API keys or entire downloaded-paper collections to a public GitHub repository by accident.

## 1A. Optional offline tutorial: see the learning law work

Before collecting real research, run `python scripts/demo_offline.py` (with the correct venv Python for your operating system). The self-contained example uses **invented teaching-only input events**, with `Fourier transform` linked in observed order to two separate named mathematical terms. It demonstrates that repeating an *external* input changes edge weights while a pulse simulation does not; the program then discards its test database. These intentionally synthetic inputs must **never be cited as actual source evidence or semantic mathematical implications**.

## 2. Create or select a network (Section 01)

Use **Manage Networks / Create / Switch / Import** to inspect known networks. Create a new **independent FLIN network** for your first experiment; this avoids reusing a large legacy database. Network names are display labels; actual storage is SQLite. Switching networks changes the active database, not the network's scientific meaning.

Run `python flin_desktop.py --list-networks` to see IDs and on-disk paths. Do not manually rename a `net_*.sqlite3` file while it is registered. Import supports a saved SQLite snapshot or the app's portable manifest/JSONL archive. If importing files from others, review and trust the source.

### Use a published or approved community memory network instead of building from scratch

You do not need to download papers, build a new graph, or install Ollama to try a published FLIN network:

1. Open **Manage Networks / Create / Switch / Import → Browse Published Networks (GitHub Releases)** while online.
2. Choose any published maintainer or reviewed community `.sqlite3` release. Select **Download & Import Selected** and give the network a local name. FLIN checks the download size and its GitHub SHA-256 if supplied, then copies/validates the SQLite as an independent local database.
3. Switch to it. Use the network manager to verify that the imported copy exists, then look for **active FLIN memory units and directed edges**. On the FLIN pulse panel, use a **stored unit label** as the seed and run a simulation; optionally inspect the 3D viewer.
4. If the application cannot access GitHub, download a `.sqlite3` Release **asset** in your browser and use **Import SQLite** instead. The repository source-code ZIP is not a network snapshot.

The downloaded file is a publication-time snapshot. Local learning **does not upload anything** to GitHub or overwrite the published file. Import future versions separately to compare them. Release review verifies basic compatibility and provenance, but cannot guarantee mathematical truth or software/database safety. Only import trusted files.

## 3. Discover mathematics and build the first dataset (Section 04)

In **04 Automatic Build Network Settings**:

1. Choose a **small number of topics** and a **small paper budget per topic**. Recommended starting point: 3 topics × 5 papers; larger numbers request far more API traffic. The automatic discoverer visits mathematical Wikipedia categories; manually entered subjects can also be selected when supported by the UI.
2. **Disable continuous topic discovery** at first. Otherwise a run can continue attempting new topics/retries until you explicitly stop it.
3. Click **Apply recommended settings** and/or **Detect hardware again**. These estimate CPU budget and worker count, but do not benchmark throughput. Too many workers can cause rate limits and SQLite contention.
4. Enable **Scan Wikipedia references** to capture footnotes, DOI and arXiv identifiers for source auditability. This increases network/API work.
5. Leave **Attempt open-access PDF extraction** off during your first run. With it enabled, the program attempts to retrieve eligible open-access PDFs; install PyMuPDF separately. **No paywall bypass is implemented.**
6. Optionally configure OpenAlex and supported provider credentials through environment variables, but the default workflow can use other public sources. External APIs can rate-limit, change, fail or return zero matches.
7. Press **Start Build Network (Literature → FLIN)**. Follow the status/log fields and topic/source counters. **Pause** suspends supported collector work; **Stop & Save** stops future work and retains committed SQLite data. A still-running network request may have to finish its timeout before a stop takes effect.

**Expected effects:** accepted papers and extracted sources are recorded. Eligible source sentences become traceable input clusters. Qualified features may form new memory units, and source-order associations can strengthen existing directed links. A run that returns zero accepted units or zero edges may simply lack qualifying input, and is not proof of a broken UI.

**Do not** set topic/paper caps into the millions without a storage, quota and time plan. `MAX_THEORIES` and related hard caps are ceilings, not recommended usage.

## 4. Verify evidence before trusting a unit

Select **Inspect Source-Grounded Input Clusters**. Check the original quoted source sentence, citation/location, extracted mathematical features, and whether their ordering actually expresses an interpretable co-occurrence. Do not treat a model-extracted claim or an article citation as a formal proof.

Use **View Source** from the selected memory when the corresponding provenance URL is available. If a source was title-only or abstract-only, do not present it as a full-text review. Inspect coverage reports and related research-quality/maintenance screens when investigating sparse or noisy datasets.

**Healthy behavior:** a memory can become active after one qualified source-grounded input; independent sources can raise evidence counts and repeated *external* observations can reinforce link weights. **Replaying an internal pulse does not train those weights.**

## 5. Explore the 3D graph (main display and Section 02)

The large center panel shows a bounded **overview sample** of memory nodes and connections. A large SQLite network can contain millions of rows, but the viewer deliberately does not draw everything at once. The sample is an interactive visual aid, **not a complete topology or proof of closeness**.

- **Drag:** rotate the 3D scene.
- **Mouse wheel / trackpad scroll:** zoom.
- **Click a node:** select it, then inspect detail and source.
- **Shift-drag (where supported):** interact with node positioning; rendered behavior can vary by OS/backend.
- **Locate:** search for an existing stored label and focus its local neighborhood.
- **Show All:** return to overview.
- **Reset Camera:** restore the viewpoint.

Node spacing is a layout/visualization heuristic. Stronger directed links may be drawn as spatially closer, but this is not the same as a semantic metric or physically measured circuit distance. A local focus is a sampled view, not the whole database.

## 6. Simulate FLIN pulses (Section 02A)

1. Inspect **02A FLIN Directed Pulse Associations** and its network status. Use **Create an Independent FLIN Network** if needed.
2. Enter an **exact existing memory label** or a distinctive prefix. Multiple labels can be separated by commas; an unknown natural-language paragraph will usually not match. Input matching is lexical, not an LLM interpretation.
3. Configure pulse rate (Hz), input duration (seconds), response-frequency threshold (Hz), observation window, and revisit cap as needed. Start with the displayed defaults and change **one variable at a time**.
4. Click **Simulate Pulses & Response Distribution**. FLIN emits discrete pulses, chooses **one eligible directed exit per step** using learned weights, records arrivals and computes thresholded response frequencies.
5. Inspect pulse-path sequences, activated memory units, terminal feedback events and response distribution. A high response-frequency unit has been **visited more often above threshold**, not proven more logically relevant or correct.
6. Open **Show 3D Association Subnetwork** or **View Full Response Curves** from the result window, where available.

**How to reason about each control:**

| Control | What changing it affects | What it does NOT mean |
| --- | --- | --- |
| Pulse rate | Number of input events per second | Confidence in a theorem |
| Input duration | How long input pulses are emitted | The age of a memory |
| Threshold | Suppression of weak visible reaction frequencies | A learned truth threshold |
| Observation window | Time scale for measuring local arrival frequency | Biological membrane constant |
| Revisit cap | Safety limit for cycling paths | Proof that loops are absent |
| Link weight | Relative probability when choosing **one** eligible exit | A semantic equivalence or formal implication |

Unseeded or isolated nodes may yield no propagation. No generated pulse is allowed to immediately reverse along its incoming edge; longer cycles are bounded by visits and steps. The simulator does **not** add an independent pass/fail probability after choosing an exit, nor does it intrinsically decay pulse amplitude.

## 7. Generate and review ten research questions (optional, Sections 03 / question workspace)

Ollama is the local model runner for **authoring**; install separately and fetch your chosen models:

```bash
ollama pull qwen3:4b-instruct
ollama pull qwen2.5:3b
ollama list
```

Use **Check Local Ollama Models** first. Then click **Associate & Generate 10 Questions** or generate from a saved response, according to the current UI. The workflow saves **ten drafts**, then lets you choose **review rounds (1–20)**, and runs generation/judgment/critique/revision serially to reduce memory contention. Review completion is required before the final set is exposed by the intended workflow. You can inspect question versions and feedback history. Export **JSON + TXT** when ready.

**Scientific responsibility:** verify every question for real mathematical definitions, assumptions, nontriviality, novelty claims and feasibility. The generator/judge models can be wrong, especially with incomplete source text. Their role labels and numeric scores are internal workflow heuristics. **Ollama does not choose FLIN pulse paths.**

## 8. Pause, save, export, restore, and maintain

- **Stop & Save** retains committed work. It is not identical to exporting a copy.
- **Save Snapshot / Export complete memory network** makes a copy for recovery or sharing. **SQLite full snapshot** is the archival choice when you need history, question sets and logs. **Portable JSONL.gz** is a readable interoperability format; it may omit some auxiliary state.
- **Import Network** creates an isolated registered network rather than overwriting an existing network.
- **Clear the current FLIN network** and CLI `--purity-clean` are potentially destructive. Make a full SQLite backup first.
- **Maintenance/repair** actions may rebuild indexes or modify data. Run them after pausing collection; prefer an isolated backup and verify remaining free disk space.

### Backups recommended before every major batch

Use `python flin_desktop.py --export-network "DESTINATION_DIRECTORY" --export-format sqlite` while there is sufficient disk space. The command writes a new timestamped directory containing the snapshot; inspect `README.txt` next to the snapshot. Periodically restore **a copy** into a test network to verify it.

## 9. Three reproducible mini-experiments

**Experiment A — Is the evidence filter working?** Build one small topic with PDF extraction disabled. Compare the original paper title/abstract with its accepted input clusters. Count false-positive mathematical features before and after changing filters. Report rejected counts separately.

**Experiment B — Does link weight influence routing?** Select a memory with at least two eligible outgoing links. Run many pulses with identical input and configuration. Compare observed proportions against `weight / sum(eligible weights)`; use a fixed simulation seed for exact reproducibility when using the Python API.

**Experiment C — Is the reaction threshold meaningful?** Keep the same network/input/seed, compare several thresholds while holding window and duration fixed. A larger threshold should hide some low-frequency responses without deleting memory units. Export raw events or query the SQLite `abc_pulse_events` table for verification.

## 10. Common mistakes

**“FLIN output says a theorem is true.”** No: a graph walk shows observed routing preferences and candidate relation evidence. External proof is required.

**“The 3D picture shows every memory.”** No: large overviews are sampled/bounded for responsiveness.

**“I can paste a paragraph and FLIN understands it.”** Not generally: lexical entry matches accepted memory labels; free-form question generation is a separate local-model stage.

**“No Ollama means FLIN can't learn.”** Incorrect: FLIN collection, clustering and pulse simulation do not require Ollama; drafting/review does.

**“More review iterations proves originality.”** No: more model evaluations are not a novelty search or theorem verification.

For commands and troubleshooting, continue to [CLI Reference](CLI_REFERENCE.md) and [Troubleshooting](TROUBLESHOOTING.md).
