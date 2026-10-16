# FLIN — Feature-Link Intellegence Network

**Repository:** https://github.com/jjy246/FLIN-Research

FLIN is an experimental, source-grounded associative memory system for mathematical knowledge. It collects material from public research sources, extracts identifiable mathematical features, converts qualified observations into persistent memory units, and learns directed associations between those units. The network can then be inspected in 3D, stimulated with a pulse-based association model, and used as evidence-linked context for mathematical question generation.

This repository is a research prototype. Its learning rules, cost parameters, and pulse model are computational hypotheses; they have not been established as models of biological memory or as methods for proving mathematical statements.

## 1. Architecture

```text
Public mathematical literature
            |
            v
Source and mathematical-quality checks
            |
            v
Attention / feature extraction
            |
            v
Effective input clusters (source text + ordered features)
            |
            v
SSRS (Sensory Shaping and Routing System)
            |
            v
First-input memory formation + directed association learning
            |
            v
Observed-pattern and association-cost evaluation
            |
            +------ Reuse existing feature memories
            |
            +------ Create an optional shortcut memory group
            |
            v
Persistent FLIN graph (SQLite)
            |
            +------ 3D inspection and source provenance
            +------ Weighted, single-path pulse association
            +------ Association-assisted mathematical question generation
```

The current extractor uses explicit source text and lexical/mathematical feature rules. **It does not use semantic embeddings or a language model to decide which mathematical memories are equivalent.** A local language model can optionally assist with question drafting and review after an association is produced.

## 2. Effective Inputs and SSRS

A document does not directly become a graph node. Its text is screened for mathematical relevance, and the attention stage identifies qualifying terms that actually occur in the source. Accepted observations are stored as **effective input clusters** containing the original passage, document identity, source URL, feature identities, and observed positions.

SSRS orders and routes the observed features, using input position and learned routing priority. Features treated as simultaneous are not arbitrarily converted into a directional sequence. The resulting ordered groups provide the observations from which FLIN learns directed links.

A directed association records **experience-based routing**, not mathematical implication. Co-occurrence and ordering alone do not establish a proof, causal relationship, or equivalence.

## 3. Memory Formation

### 3.1 Primitive Feature Memories

A new mathematical feature that passes source-grounding and quality checks becomes an **active, triggerable memory unit on its first qualified input**. An additional paper is not required to activate it. Subsequent independent inputs can add evidence and reinforce associations.

The current implementation does **not** use the estimated shortcut cost to reject an otherwise qualified new primitive feature. This protects novel observations from being discarded by an unvalidated cost heuristic.

### 3.2 Directed Association Learning

SSRS-ordered effective input groups update directed edges in the associative graph. Replaying the same stored input does not repeatedly count as a new learning event. Edge weights change with qualified exposure, and weaker edges remain eligible during association.

### 3.3 Shortcut Memory Groups

Repeated, ordered sequences of existing active memories may justify a reusable **shortcut memory group**. Consider an observed route:

```text
A -> B -> C -> D
```

If the route is supported by enough distinct documents and passes the cost test, FLIN can create:

```text
A -> [Shortcut: A,B,C,D] -> D
```

The shortcut is itself an active memory unit containing the ordered member IDs and source evidence. **The original memories and A -> B -> C -> D route are retained.** The additional two-hop route is intended to reduce future association steps; it does not assert that `A` logically implies `D`.

Current eligibility rules:

- A candidate path contains **4–6 distinct, active feature memories**.
- The ordered sequence must be observed after SSRS processing; simultaneous groups, repeated members, and existing shortcut members are excluded.
- The same pattern must be supported by **at least 3 distinct document IDs**. Repeated occurrences in one document do not count as independent support.
- A shortcut is formed only when its estimated net savings is **strictly greater than 0.5** cost units.

These parameters are implementation defaults, not experimentally optimized constants.

## 4. Association-Cost Model

Let:

- `n` be the number of memories in the observed sequence;
- `s` be the number of distinct supporting documents;
- `h` be the estimated cost per traversed link;
- `F`, `S`, and `I` be formation, storage, and interference cost penalties.

The current prototype estimates reuse opportunity from the number of independent sources:

$$
U(s) = s\bigl(1 + \ln(1+s)\bigr).
$$

The estimated costs are:

$$
C_{\mathrm{original}} = U(s)(n-1)h,
$$

$$
C_{\mathrm{shortcut}} = 2U(s)h + F + S + I,
$$

$$
\Delta C = C_{\mathrm{original}} - C_{\mathrm{shortcut}}.
$$

A candidate satisfying the source and path constraints is materialized when `ΔC > 0.5`.

| Parameter | Default |
| --- | ---: |
| Minimum / maximum path length | 4 / 6 memories |
| Minimum independent documents | 3 |
| Per-link cost `h` | 1.0 |
| Formation penalty `F` | 2.5 |
| Storage penalty `S` | 0.8 |
| Interference penalty `I` | 0.6 |
| Minimum net savings | 0.5 |

**Interpretation:** `U(s)` is a proxy, not an observed future query count. The formula estimates savings in traversal steps under an assumed workload. It does not measure actual runtime, memory usage, mathematical accuracy, or cognitive efficiency. Validating these estimates requires controlled benchmarks with shortcuts enabled and disabled.

## 5. Associative Pulse Simulation

FLIN represents learned associations as a directed weighted graph. Under the current simulation:

1. An effective input activates matching memory units.
2. An external pulse source supplies a configurable pulse rate and duration.
3. Each pulse selects **one** eligible outgoing edge; selection is weighted by learned link strength.
4. Immediate backtracking is excluded. Longer revisits are bounded by a configurable limit.
5. A memory unit's reaction is measured from pulse arrivals in a sliding time window. The interface applies a reaction-frequency threshold for display.

The pulse model is a simulation of the project's proposed association rules, not a physical neural simulation. The availability of a shortcut does not force it to be selected: it participates in the same weighted routing mechanism as other outgoing links.

## 6. Sources and Collection

The application supports mathematical topic discovery and bibliographic retrieval through the following integrations:

| Source | Role |
| --- | --- |
| Wikipedia / MediaWiki | Topic discovery, article text, references |
| arXiv | Research preprints and available metadata |
| Crossref | Publication metadata and DOI resolution |
| OpenAIRE | Research-product discovery |
| DBLP | Computing-related publications |
| Europe PMC | Biomedical and interdisciplinary publications |
| OpenAlex | Optional research-index lookup |
| Semantic Scholar | Optional API-key-based lookup |
| Local SQLite catalog | Previously indexed publication metadata |

Availability, coverage, rate limits, and content depth vary across providers. A search result or bibliographic record is not equivalent to reading the full paper. The application records source information and, where available, whether it processed only a title, an abstract, or an extracted text excerpt. PDF extraction is optional and may fail for inaccessible or malformed files.

Continuous discovery periodically retries when no new work is available; a temporarily empty queue does **not** demonstrate that all mathematical knowledge has been collected.

## 7. Installation and Launch

### Windows

1. Install **Python 3.10 or newer** with Tcl/Tk support.
2. Clone or download this repository.
3. Double-click **`start_windows.bat`**.

The Windows launcher should execute **`flin_desktop.py`**, which is the complete application entry point in this repository. If maintaining a custom BAT file, keep its environment setup and dependency-installation steps while checking that its final command starts `flin_desktop.py`.

To run the application manually from a terminal:

```powershell
py -m pip install -r requirements.txt
py flin_desktop.py
```

### Ubuntu / Linux

Install system Tkinter support, create a virtual environment, and install dependencies:

```bash
sudo apt update
sudo apt install python3-tk python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python flin_desktop.py
```

Core dependencies include `matplotlib`, `networkx`, `numpy`, `requests`, `beautifulsoup4`, and `scikit-learn`. **PyMuPDF** is needed only if PDF text extraction is enabled. Running the GUI requires a graphical desktop session; the diagnostic CLI can run without one.

Some mathematical question-generation and review features additionally require a local **Ollama** service and compatible installed models. Ollama is **not required** for collecting sources, creating FLIN memories, evaluating shortcuts, or simulating associative pulses.

## 8. Building Your Own Memory Network

From the desktop application:

1. Select **New Empty FLIN Network (no data copied)** to create an isolated network.
2. Configure the mathematical discovery settings and source-reading options.
3. Select **Start Building (Literature → FLIN)**. Qualified documents update the active network as they are processed.
4. Use **Pause** or **Stop and Save** when needed; do not launch concurrent instances against the same SQLite database.
5. Inspect the 3D graph and **View Source-Grounded Input Clusters** to review what produced the memories.
6. Use **Run Pulse Simulation / Response Distribution** to examine associative routing.
7. Open **Shortcut and Cost Report** to inspect estimated savings and formed groups.

To evaluate historical SSRS clusters created by a previous version, use **Reevaluate Existing Input Costs (1,000 clusters)**. This processes saved input clusters incrementally, without requiring the original papers to be downloaded again.

Useful command-line operations (from the project directory):

```bash
# Create and activate an independent FLIN network
python flin_desktop.py --flin-create-network "My Mathematics Network"

# Inspect current FLIN network statistics
python flin_desktop.py --flin-info

# Inspect source coverage and recent collection status
python flin_desktop.py --flin-source-report

# Reevaluate up to 1,000 saved SSRS clusters
python flin_desktop.py --flin-retrofit --flin-retrofit-limit 1000

# Inspect estimated costs and existing shortcuts
python flin_desktop.py --flin-efficiency-report

# Simulate association from a known mathematical feature
python flin_desktop.py --flin-simulate "partial differential equation"
```

On Windows, replace `python` with `py` if that is how Python is installed.

## 9. Persistence and Provenance

FLIN persists its networks in SQLite, under a per-user application data directory (`~/.local/share/brain_project/` in the current code, relative to the user's home directory). Network files can be switched without replacing an existing database.

The associative graph uses historical `abc_*` table names for compatibility. The relevant structures include:

| Table | Purpose |
| --- | --- |
| `abc_units`, `abc_edges` | Active feature memories and directed weighted links |
| `abc_input_clusters`, `abc_cluster_features` | Source-grounded effective inputs and feature positions |
| `abc_ssrs`, `abc_evidence` | Routing priorities and per-source evidence |
| `flin_patterns`, `flin_pattern_evidence` | Observed multi-memory patterns and distinct-source support |
| `flin_shortcut_members` | Ordered primitive members of each shortcut |
| `flin_cost_decisions` | Recorded formation/reuse decisions and estimated costs |

New shortcut tables are added without deleting the original FLIN units, edges, or evidence. The application retains the legacy `units`/`edges` tables separately; those tables should not be confused with the active FLIN associative graph.

**Back up your SQLite files before upgrading or running large collections.** A code update should not require clearing the existing memory network.

## 10. Reproducibility and Current Limitations

The code implements source-grounded feature extraction, SSRS-based ordering, first-input activation, directed association learning, and experimental cost-based shortcut formation. The current cost policy is deterministic for a given observed pattern and source count, while pulse-path simulation can be randomized and should be controlled with a seed for comparable experiments.

Open research questions include:

- Whether shortcut formation measurably reduces association time or computation under realistic workloads.
- How to estimate future reuse and interference costs from observed behavior rather than document counts.
- How to distinguish compact representation of a theory from independently deriving or proving that theory.
- How to revise or remove shortcuts when new evidence conflicts with an earlier pattern.
- How to test network sufficiency within a specified mathematical domain without mistaking a lack of new inputs for complete knowledge.

**No global completeness claim is made.** Stagnant memory counts, idle discovery, or positive shortcut-cost estimates cannot prove that FLIN has learned all of mathematics. Knowledge coverage, source quality, formal correctness, and retrieval efficiency require separate evaluation.

## Project Link

https://github.com/jjy246/FLIN-Research
