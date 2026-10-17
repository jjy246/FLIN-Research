# FLIN — Feature-Link Intellegence Network

**Research repository:** https://github.com/jjy246/FLIN-Research  
**Application:** Python desktop software (Tkinter, Matplotlib, NetworkX, NumPy, SQLite)  
**Current visualization:** Original Topology + Association Dynamics Space

FLIN is an experimental, source-grounded associative memory system for mathematical knowledge. It discovers research material, extracts mathematical features from available source text, routes qualified inputs through an attention/SSRS pipeline, and learns persistent directed links between memory units. It also provides weighted single-path pulse simulations, experimental cost-based shortcut memories, and tools for inspecting the resulting network.

**Association Dynamics Space** adds an observation-oriented 3D representation derived from recorded pulse events. Its coordinates describe observed propagation depth, uncertainty at eligible branch points, and the locations where feedback is initiated. Pulse playback is separate from coordinate estimation: the positions summarize an entire recorded run, while the animation shows individual recorded events.

This is a research prototype. It does **not** claim to reproduce biological neurons, establish the truth of mathematical statements, or provide a complete model of human intelligence.

## 1. System overview

```text
Mathematical research sources
            |
            v
Source relevance and quality checks
            |
            v
Attention: source-grounded feature extraction
            |
            v
Effective Input Clusters
            |
            v
SSRS: Sensory Shaping and Routing System
            |
            v
First-qualified-input memory formation
            |
            v
Directed, weighted association learning
            |
            +---- Reuse existing feature memories
            |
            +---- Evaluate optional shortcut memory groups
            |
            v
Persistent FLIN associative graph (SQLite)
            |
            +---- Original Topology: editable 3D layout
            |
            +---- Weighted, single-path pulse simulation
            |          |
            |          v
            |    Pulse-level event trace
            |          |
            |          v
            |    Association Dynamics Space (X, Y, Z)
            |          |
            |          +---- Run/gate statistics
            |          +---- Time-indexed replay
            |          +---- Feedback origins and safety stops
            |
            +---- Association-assisted mathematical questions
```

Feature identification and association formation are rule-based and grounded in retrieved text. **FLIN does not use semantic embeddings, retrieval-augmented generation (RAG), or language models to place nodes in its 3D spaces.** A local language model is optional for a separate mathematical question generation and review workflow.

## 2. Attention, effective inputs, and SSRS

Documents are screened for mathematical relevance and usable evidence before they contribute to the associative memory network. The attention stage identifies mathematical features explicitly supported by the available source material.

An **Effective Input Cluster** retains the source/document identifier, the original evidence passage, the source URL, the participating feature memories, and feature positions. **SSRS** processes the accepted cluster, including input order and previously learned routing priorities, to determine which experiences can reinforce directed associations.

Simultaneously observed features are not silently converted into an arbitrary sequential path. Source-grounded association is **not** equivalent to logical implication, mathematical equivalence, or proof.

### First-input feature formation

A feature that passes the current evidence and quality checks can become an active, triggerable memory unit after its **first qualified input**; it does not need three supporting papers. Later independent experiences can reinforce the unit's evidence and its observed associations.

The cost policy described below concerns **additional composite/shortcut memories**. It does not suppress an otherwise qualified new primitive feature because of an estimated reconstruction cost.

## 3. Directed associations and pulse routing

The active associative graph consists of memory units and weighted **directed** edges. At each visited unit, one pulse chooses **one** eligible outgoing edge. For an eligible set \(A_i\), the routing probability is

$$
P(i\rightarrow j\mid A_i)=\frac{w_{ij}}{\sum_{k\in A_i}w_{ik}},\qquad j\in A_i.
$$

Eligibility preserves the existing simulation rules: positive-weight links to active destinations, no immediate return to the previous unit, and the configured revisit limit. The weighted sampler does not perform an additional transmission-success draw and does not attenuate a pulse merely because it travels.

The simulation uses an externally supplied pulse rate, input duration, transit-time parameter, and finite **computational safety bounds** (such as `max_steps`). These guards limit execution; they are not proposed physiological termination mechanisms. Pulse arrivals contribute to a response-frequency readout over a sliding time window.

Every pulse retains the identity of its **original input gate**. Different gates can be analyzed independently without treating their feedback records as interchangeable.

## 4. Efficiency-aware shortcut memory formation

FLIN can evaluate repeatedly observed, ordered SSRS patterns and add reusable composite units when a heuristic association-cost estimate indicates a benefit.

For a sequence

```text
A -> B -> C -> D
```

a qualified shortcut may add an alternative path:

```text
A -> [Shortcut: A, B, C, D] -> D
```

The original units and directed edges remain intact. A shortcut is an additional associative route, **not a proof** that `A` implies `D`.

Current requirements include a candidate sequence of **4–6 distinct active feature memories**, a valid SSRS-observed order (no invented order from simultaneous groups), at least **three distinct source documents**, and a positive estimated net benefit above the configured threshold. Existing shortcut units are excluded from shortcut candidates.

With \(n\) memories, \(s\) distinct supporting sources, link cost \(h\), formation cost \(F\), storage cost \(S\), and interference penalty \(I\):

$$
U(s)=s\bigl(1+\ln(1+s)\bigr),
$$

$$
C_{\mathrm{original}}=U(s)(n-1)h,
$$

$$
C_{\mathrm{shortcut}}=2U(s)h+F+S+I,
$$

$$
\Delta C=C_{\mathrm{original}}-C_{\mathrm{shortcut}}.
$$

| Experimental parameter | Default |
| --- | ---: |
| Minimum / maximum members | 4 / 6 |
| Independent source threshold | 3 |
| Per-link cost \(h\) | 1.0 |
| Formation penalty \(F\) | 2.5 |
| Storage penalty \(S\) | 0.8 |
| Interference penalty \(I\) | 0.6 |
| Required net benefit | \(\Delta C>0.5\) |

`U(s)` is a **reuse heuristic**, not a measured count of future retrievals. These parameters have not been calibrated against execution time, accuracy, or cognitive behavior. The feature extraction, memory formation, and cost model are separate from the new 3D observation metrics.

## 5. Association Dynamics Space: mathematical coordinates

For an observed memory unit \(i\), the new view uses

$$
\mathbf r_i=(X_i,Y_i,Z_i).
$$

Coordinates are computed from **recorded visits of a selected simulation run**. They are not used as inputs to learning, pulse routing, or weight updates. A separate analysis is available for the selected gate and for all gates combined.

### 5.1 X — Normalized propagation depth

For every recorded visit to memory \(i\), let \(d\) be the number of directed transmission steps since the pulse entered its input gate. Define

$$
X_i=\frac{1}{N_iD_{\mathrm{ref}}}
\sum_{v\in\operatorname{Visits}(i)}\min(d_v,D_{\mathrm{ref}}),
$$

where \(N_i\) is the number of visits and \(D_{\mathrm{ref}}>0\) is fixed for the run. The current implementation stores `D_ref = max_steps` from the simulation settings. The unnormalized mean depth, \(\sum_v d_v/N_i\), is also reported.

A node with no recorded visits is **Unknown / Unreached**, not a node with \(X=0\). An actual gate-entry visit at step zero can legitimately have \(X=0\).

### 5.2 Y — Normalized branching entropy

For each recorded visit \(v\) to unit \(i\), use the **eligible exits at that specific visit**, after applying the current pulse's previous-node and revisit restrictions. Let

$$
p_{v,j}=\frac{w_{ij}}{\sum_{k\in A_v}w_{ik}},
\qquad
H_v=-\sum_{j\in A_v}p_{v,j}\ln p_{v,j}.
$$

When there are zero or one eligible exits, \(H_v=0\). Otherwise, it is the Shannon entropy of the eligible-exit distribution. Average across visits and normalize:

$$
\overline H_i=\frac{1}{N_i}\sum_{v\in\operatorname{Visits}(i)}H_v,
\qquad
Y_i=\frac{\overline H_i}{\ln K_{\mathrm{ref}}}.
$$

`K_ref` is saved with the run and computed from the **full active network**, not the sampled render. It is the greater of 2 and the maximum positive-weight active outgoing degree in the simulation-time graph.

The node details also show average eligible-exit count, \(\exp(\overline H_i)\) (effective branching), average maximum exit probability, and mean probability of the selected exit when one was chosen.

**High entropy means uncertain selection among possible exits. It does not mean that one pulse divides into multiple paths.**

### 5.3 Z — Feedback initiation rate

A feedback initiation is counted only when a visited memory has **no eligible outgoing edge**:

$$
Z_i=\frac{N_{\mathrm{no\_eligible\_exit},i}}{N_{\mathrm{visits},i}}.
$$

`max_steps_guard` events are counted separately and **do not** increase \(Z_i\). The selected-gate view recomputes this ratio using only events tagged with that original gate; the all-gates view uses the complete run.

**Z measures where feedback is initiated, not whether a feedback signal subsequently reaches its gate.** The current code does not simulate the nodes, physical connections, or traversal events of an independent feedback tree. A dotted line, where shown, is labeled **logical gate mapping only**; it is not a fabricated feedback-transmission path.

### 5.4 Statistical positions versus event animation

A memory's XYZ coordinate is fixed by the **full selected run** (or selected gate's complete statistics). Playing or scrubbing the timeline does not recalculate the coordinate from only the frames already watched.

Playback separately highlights the recorded current visit and, when **two consecutive events of the same `pulse_id` confirm the transition**, interpolates a marker along that recorded directed edge for visual continuity. Interpolated positions are **rendering only**, not additional simulated events.

## 6. Pulse-level trace and historical-run compatibility

Older `abc_pulse_events` records retained the run, gate, memory, and time, but did not identify each pulse or its visit order. They cannot reliably reconstruct independent paths from timestamps alone.

The upgraded program records additional **observation-only** rows in `flin_pulse_trace`, including:

| Field | Meaning |
| --- | --- |
| `run_id` | Simulation run identifier |
| `pulse_id` | Individual pulse within the run |
| `gate` | Original input-gate label |
| `step_index` | Step count from that pulse's entry |
| `unit_id` | Memory visited at this step |
| `previous_unit` | Previous memory, if any |
| `selected_next_unit` | Chosen successor only if a traversal is recorded |
| `simulation_time` | Event time in simulated seconds |
| `terminal_reason` | `no_eligible_exit`, `max_steps_guard`, or null |
| `eligible_count` | Number of valid exits at that visit |
| `branch_entropy` | Exit-distribution entropy (nats) |
| `max_exit_probability` | Largest eligible-exit probability |
| `chosen_probability` | Probability of the chosen exit (where applicable) |

`flin_dynamics_meta` records the run's `D_ref`, `K_ref`, active graph unit/link totals, and trace version.

These tables are created with **non-destructive `CREATE TABLE IF NOT EXISTS` operations**, preserving the existing `abc_runs`, `abc_pulse_events`, `abc_feedback`, and `abc_positions` tables. If an older run has no full trace, the interface reports **Legacy / Insufficient Trace**. It does not infer missing pulse identities, fabricate paths, or create artificial feedback activity.

The event observer computes exit statistics during the existing sampling procedure without another random draw. Under the same graph snapshot, settings, and random seed, instrumentation does not intentionally alter the weighted single-path routing policy.

## 7. Using the 3D desktop interface

The main FLIN window reuses the existing Matplotlib 3D canvas and offers two `View Mode` values:

- **Original Topology** — the original spatial network layout, interaction, and positions persisted in `abc_positions`.
- **Mechanism** — **Association Dynamics Space**, with mathematically defined, run-based X/Y/Z coordinates and recorded event replay.

To inspect a run, execute an associative pulse simulation from a known memory, then choose `Mechanism` and select the resulting run under **Run Selection**. The run list shows recent records; **Open Run ID** supports an older run identifier.

| Control | Behavior |
| --- | --- |
| `Run Selection`, `Refresh Runs`, `Open Run ID` | Load recent or historical simulation data |
| `Gate Filter` | Show all recorded gates or one selected gate |
| `Play` / `Pause` | Start or stop pulse-event replay |
| `Step` / `Replay` | Advance one event or restart playback |
| `Playback Speed` | Choose a replay speed (0.25× to 8×) |
| `Simulation time (s)` | Scrub the recorded timeline |
| `Show Feedback` | Toggle observed feedback origins and safety-stop markers |
| `Directed Edges` | Toggle the rendered directed association links |
| `All measured` / `Activated through time` / `Selected gate` | Change display scope |
| `Focus Selected` / `Reset Camera` | Adjust the 3D viewpoint |
| `Show Metrics` | Inspect recorded per-unit and run-level statistics |

Use the existing mouse gestures for 3D rotation and selection; the Mechanism view also supports scroll zoom and focus/pan behavior. Selecting a memory displays the normalized X/Y/Z, raw mean depth, branching entropy, exit probabilities, visit and feedback counts, `max_steps_guard` count, current incoming/outgoing edges, and sampled event records.

### Visual notation

- **Highlighted node / active segment:** recorded association event and, when confirmed, its selected directed transition.
- **Directed edges:** real active association links; line thickness reflects the currently stored weight, not Euclidean similarity or logical implication.
- **Pink diamond:** observed `no_eligible_exit` feedback initiation.
- **Dotted pink line:** **logical association to the original input gate only**, not a simulated return path.
- **Red ×:** `max_steps_guard` computational stop, not a biological feedback event.

The XYZ coordinates and normalization references describe the chosen run; however, displayed **graph connections and their thickness come from the current network database**, not a full historical graph/weight snapshot. Network changes after a simulation may therefore change the displayed edge layer without changing that run's saved XYZ statistics or pulse trace. This limitation is explicitly reported in the interface.

### Structural preview without a full run

A bounded structural preview can estimate **directed shortest-path depth** from a selected input memory. The application labels this as **STRUCTURAL ESTIMATE ONLY**. It does **not** assign fictitious entropy or feedback coordinates: Y, Z, and feedback remain **Unknown / Not observed**. This preview is a one-axis reachability summary, not a three-dimensional reconstruction of measured dynamics.

## 8. Scale and reproducibility

The SQLite database, **not the display sample**, remains the source of truth for pulse events and per-memory statistics. A large run may render a bounded set of nodes and edges for responsiveness; the UI marks such views as sampled. The computation of `K_ref` uses the complete eligible active graph at simulation time, and run metrics use the full recorded trace rather than just the points shown in 3D.

Trace loading and structural-preview work are dispatched outside the Tkinter event loop. The 3D view caches loaded run data so ordinary camera adjustments do not cause an entire database-wide statistics pass.

A complete **historical topology/weight snapshot is not presently stored** with each run. The recorded per-visit entropy and probabilities support exact observation of what the selected run calculated, but recreating the complete historical network layout and every historical link weight after subsequent learning is not supported.

## 9. Research literature and optional question generation

FLIN can discover mathematical topics and retrieve available records from Wikipedia/MediaWiki, arXiv, Crossref, OpenAIRE, DBLP, and Europe PMC. OpenAlex and Semantic Scholar integrations are optional and may require API configuration. A local SQLite literature catalog can reuse previously indexed source records.

Provider availability, rate limits, content access, and PDF parsing vary. An article title, bibliographic record, abstract, and available full text have different evidence value. A source-grounded association is not automatically a verified theorem or causal relation.

The separate question-generation workflow can use **local Ollama models** to draft and review questions from retrieved evidence and FLIN association output. **Ollama is optional** for building memory networks, forming shortcuts, computing XYZ, and replaying pulse traces.

## 10. Installation

### Windows

Install Python **3.10+** with Tcl/Tk, clone/download this repository, then run:

```text
start_windows.bat
```

The Windows launcher must point to **`flin_desktop.py`**, the desktop application entry point in this repository. Alternatively, from the project directory:

```powershell
py -m pip install -r requirements.txt
py flin_desktop.py
```

If you replace the desktop program, keep the filename `flin_desktop.py` so the existing launcher continues to work. This README documents the program's intended launcher path; Windows-specific behavior depends on the `start_windows.bat` supplied with the repository.

### Ubuntu / Linux

```bash
sudo apt update
sudo apt install python3-tk python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python flin_desktop.py
```

Core third-party packages include `numpy`, `networkx`, `matplotlib`, `requests`, `beautifulsoup4`, and `scikit-learn`; `PyMuPDF` is optional for PDF extraction. A graphical desktop session is required for the Tkinter viewer. Supported maintenance/reporting CLI commands can be run over SSH without a `DISPLAY`.

## 11. Building and inspecting a network

From the desktop application, create an empty FLIN network, configure research discovery and source-reading settings, and start **Literature → FLIN** building. Qualified inputs create new active feature memories and strengthen observed links. Pause/stop collection when needed; retain and back up your persistent SQLite files when upgrading.

Use the original 3D view to inspect the topology. To observe dynamics, run a pulse simulation, then switch the same 3D canvas to `Mechanism` and choose a run. Use the gate filter, replay controls, and metrics panel to investigate how recorded pulse paths differ across the network.

These CLI commands can be run from the project directory:

```bash
# General help, including available simulation options
python flin_desktop.py --help

# Create and activate an independent mathematics FLIN network
python flin_desktop.py --flin-create-network "My Mathematics Network"

# Show current associative-memory status
python flin_desktop.py --flin-info

# Inspect persistent source/discovery state
python flin_desktop.py --flin-source-report
python flin_desktop.py --flin-discovery-info

# Reevaluate up to 1,000 previously stored SSRS clusters for shortcuts
python flin_desktop.py --flin-retrofit --flin-retrofit-limit 1000

# Inspect cost decisions and shortcuts
python flin_desktop.py --flin-efficiency-report

# Run a weighted, single-path pulse simulation
python flin_desktop.py --flin-simulate "partial differential equation"

# Read complete recorded run metrics (replace 42 with the desired run ID)
python flin_desktop.py --flin-dynamics-report 42

# Inspect available independent networks
python flin_desktop.py --list-networks
```

The dynamics report emits run metadata and per-memory X/Y/Z statistics in JSON. On a run without complete pulse identity and step traces, it reports an insufficient-trace status instead of reconstructed paths. Use `py` instead of `python` on Windows when appropriate.

## 12. Persistence and data compatibility

FLIN stores network state in SQLite files under a per-user application directory (`~/.local/share/brain_project/`, relative to the user's home directory, in the current implementation). Multiple network databases can be managed separately.

| Table | Purpose |
| --- | --- |
| `abc_units`, `abc_edges` | Active FLIN memory units and directed weighted associations |
| `abc_ssrs`, `abc_evidence` | Learned SSRS priorities and source evidence |
| `abc_input_clusters`, `abc_cluster_features` | Effective input clusters and feature positions |
| `flin_patterns`, `flin_pattern_evidence` | Observed candidate shortcut paths and independent source support |
| `flin_shortcut_members`, `flin_cost_decisions` | Composite-member identities and cost decisions |
| `abc_runs` | Pulse simulation settings and summarized results |
| `abc_pulse_events` | Legacy-compatible pulse arrival events |
| `abc_feedback` | Feedback-origin and safety-stop summaries with gate labels |
| `flin_pulse_trace` | New pulse-resolved visits, choices, entropy and terminal reasons |
| `flin_dynamics_meta` | New per-run normalization references and graph totals |
| `abc_positions` | Original user-facing 3D topology positions; not overwritten by XYZ analysis |

Legacy `units`/`edges` tables are retained separately from the active `abc_*` associative graph. Existing databases are **extended, not cleared or reconstructed**, by the new observation tables. Historical runs without full pulse traces remain accessible as records but cannot be honestly replayed as individual pulse paths.

**Before major upgrades:** stop active collectors, close other FLIN instances, and back up the user's SQLite database files (including relevant WAL state where applicable). Do not run multiple writers against the same application database during maintenance.

## 13. Research boundaries and evaluation

The present implementation provides **observability of its own simulated association dynamics**, not a validated biological model or a proof engine. In particular:

- A directed learned link is an observed association, not an established mathematical implication.
- Branching entropy measures uncertainty over eligible **single** exits; it does not encode simultaneous pulse splitting.
- `Z` counts feedback initiation at `no_eligible_exit`; it does not measure arrival at the original gate.
- No independent physical feedback-tree propagation is implemented or animated.
- `max_steps_guard` and revisit limits are computational safeguards, not physiological laws.
- The heuristic shortcut cost model has not been validated against measured long-term task efficiency.
- Render sampling does not define the statistics, and missing event data is not inferred from timestamps.
- Historical run metrics can be examined after learning, but the current edge display is not a complete frozen historical graph.
- Network growth or stalled discovery does not establish mathematical knowledge completeness.

Useful research comparisons include runs under fixed random seeds and matching graph snapshots, gate-conditioned differences in entropy and feedback origins, performance with/without shortcuts, and stability of the observed metrics across input conditions. These are experimental questions; this repository does not assert that they have already been resolved.

## Repository

https://github.com/jjy246/FLIN-Research
