# FLIN — Feature-Link Intellegence Network

**A source-grounded, brain-inspired associative memory system for mathematical research.**

[GitHub Repository](https://github.com/jjy246/FLIN-Research)

FLIN is an experimental Python desktop application that learns persistent, directed associations from mathematical literature. Instead of placing papers into a static keyword list, it extracts supported mathematical features, forms triggerable memory units, and strengthens associations when qualified input experiences provide evidence.

The goal is to investigate whether a growing associative memory network can help a machine reuse existing knowledge, connect mathematical frameworks, and propose research questions that can be rigorously tested.

> **Research status:** FLIN is an experimental prototype, not a proof engine or a validated biological model. Learned associations are not mathematical implications, and AI-generated research questions require independent verification.

## Core capabilities

| Component | What it does |
| --- | --- |
| Literature discovery | Explores mathematical topics and retrieves available academic metadata and source text. |
| Attention and effective inputs | Extracts source-grounded mathematical terms and ordered input clusters. |
| SSRS | Processes qualified input clusters and their observed order for associative learning. |
| Memory formation | Creates persistent, triggerable feature memories from qualified new inputs. |
| Directed association learning | Adds or reinforces weighted links supported by observed input order. |
| Pulse simulation | Explores one eligible outgoing edge per pulse using weight-proportional sampling. |
| Shortcut memories | Experiments with reusable, source-supported patterns under a heuristic cost model. |
| 3D network exploration | Displays an interactive, sampled topology while retaining the complete graph in SQLite. |
| Research question workflow | Generates 1–20 questions with local Ollama models and optional iterative reviews. |
| Network auditing and repair | Diagnoses isolated memories and reprocesses cached sources for missed associations. |
| Complete network export | Creates verified SQLite snapshots for continuation training and separate graph-analysis files. |

## How FLIN learns

```text
Mathematical topics and research papers
                |
                v
       Source quality checks
                |
                v
  Attention / feature extraction
                |
                v
     Effective Input Clusters
                |
                v
              SSRS
                |
                v
      Triggerable memories
                |
                v
   Directed, weighted associations
                |
                +--> Reuse and reinforce existing memories
                +--> Evaluate optional shortcut patterns
                |
                v
       Persistent SQLite network
                |
                +--> Pulse-based associative exploration
                +--> Interactive 3D topology
                +--> Source-grounded research questions
```

### Source-grounded memory formation

A qualified feature can become an active memory unit on its **first valid effective input**. Subsequent independent observations may reinforce the same memory and its connections.

FLIN preserves source identifiers, supporting passages, and input-cluster records so that associations can be audited.

Two concepts appearing in the same paper do **not** automatically establish a valid mathematical implication or even a directed association. The directed-learning process uses qualified, ordered input evidence rather than unrestricted co-occurrence.

### Weighted, single-path associative pulses

For a memory unit with eligible outgoing neighbors \(A_i\), the probability of choosing edge \(i \to j\) is

$$
P(i\to j\mid A_i)=\frac{w_{ij}}{\sum_{k\in A_i}w_{ik}}.
$$

Each pulse chooses **one** eligible exit at a time.

The simulator respects immediate-backtracking restrictions and configured revisit limits. It does not split a pulse across every outgoing link or add an independent transmission-success probability.

Computational safety limits are not treated as biological mechanisms.

### Experimental shortcut memories

FLIN can identify repeatedly observed ordered sequences and evaluate whether an additional composite memory could reduce an estimated association cost.

Shortcut formation requires independent source support and preserves the original memories and links.

The cost model is a research heuristic, **not** a demonstrated reduction in real-world computation time or proof of cognitive efficiency.

## Mathematical research question generation

The question-generation workflow is optional and uses **local Ollama models**. It is separate from the rule-based memory-formation process.

- Choose **1–20 questions** per set; the selected count is stored for resuming and export.
- Specify **one or multiple research topics** (for example, `linear algebra, calculus, finance`).
- Review each required topic for a substantive mathematical role, not just the presence of a keyword.
- Assess mathematical objects, assumptions, verifiability, source evidence, mathematical depth, and **topic linkage**.
- Review questions sequentially with a single active model call, reducing GPU memory contention.
- Configure up to **20 review rounds** per question, with early stopping when further revision is unproductive.
- Save intermediate drafts, scores, reviews, and revisions in SQLite.
- Export concise, reader-friendly TXT questions and structured JSON records.

A question missing a required topic or failing the linkage check is not considered a successfully validated cross-topic candidate.

**Model scores remain model judgments**, not formal verification, literature novelty checks, or guarantees of mathematical correctness.

### Example output format

**Title:** Convergence of Portfolio Optimization

**Topics:** Linear Algebra · Calculus · Finance

**Mathematical objects:** Portfolio weights \(w\), covariance matrix \(\Sigma\), and a differentiable objective \(F(w)\).

**Assumptions:** \(\Sigma\) is positive definite; \(w\) belongs to a specified feasible set.

**Research question:** Under which step-size and constraint conditions does projected gradient descent converge to the portfolio optimum?

**Review summary:** Mathematical quality, topic coverage, linkage score, and the main unresolved issue. Detailed reviews are retained separately.

*This example illustrates formatting, not a claim of research novelty.*

## Network visualization and scalability

The desktop application provides an interactive **3D topology viewer** using Tkinter and Matplotlib, with NetworkX/NumPy-based layout operations.

It supports browsing, focusing, selecting memories, and inspecting learned links and source information.

For large networks, only a bounded portion is drawn at once to keep the interface responsive.

**Visualization limits do not limit the number of memories or links stored in SQLite or included in a full export.**

**Implementation note:** The current source snapshot uses a topology-oriented approximate 3D layout.

The previously proposed *Association Dynamics Space* with measured propagation-depth, branching-entropy, and feedback-initiation XYZ coordinates is a separate research design and should not be considered implemented in this snapshot.

## Literature acquisition and recovery

FLIN supports mathematical-topic discovery and research-source acquisition through supported literature services and local caching.

Available provider integrations include Wikipedia/MediaWiki, arXiv, Crossref, and optional additional academic services.

Actual coverage depends on API availability, rate limits, metadata quality, and full-text access.

The collection pipeline records discovery and source progress, supports bounded retry/recovery behavior, and distinguishes a temporarily unavailable source from a completed known discovery frontier.

Exhausting the **currently discovered** sources does **not** mean all mathematical knowledge has been learned.

Recent association-learning improvements address cases where valid concepts formed memories but ordered links were missed, including multi-concept neighboring sentences and previously cached abstracts.

Recovery is designed to avoid replaying the same learning event as new evidence twice.

## Installation

### Requirements

- Python **3.10+**
- Tkinter and a graphical desktop for the GUI
- Core Python packages: `numpy`, `matplotlib`, `networkx`, `requests`, `beautifulsoup4`, `scikit-learn`
- Optional: `PyMuPDF` for PDF text extraction, `psutil` for richer resource detection
- Optional: [Ollama](https://ollama.com/) for local research-question generation and review

### Ubuntu / Linux

```bash
sudo apt update
sudo apt install python3-tk python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy matplotlib networkx requests beautifulsoup4 scikit-learn
python flin_desktop.py
```

### Windows

Install Python with Tk support and the required Python packages.

Run the repository's Windows launcher if supplied, or start the desktop program directly:

```powershell
py -m pip install numpy matplotlib networkx requests beautifulsoup4 scikit-learn
py flin_desktop.py
```

**File naming:** The publicly released entry point is `flin_desktop.py`.

The developer's local Ubuntu working copy may be named `questioning.py`; both names refer to the same application when their contents are synchronized.

### Optional local models

Install and start Ollama, then pull a supported local model.

A smaller installed model can be requested for reviews through the `BRAIN_REVIEW_MODEL` environment variable.

Model availability, output quality, and speed depend on system memory, GPU VRAM, and the Ollama server configuration.

## Useful CLI commands

Run commands from the repository directory.

Replace `python` with `python3` or `py` as appropriate.

```bash
# Available commands and configuration
python flin_desktop.py --help

# Current network and hardware information
python flin_desktop.py --flin-info
python flin_desktop.py --cpu-info

# Source acquisition and association health
python flin_desktop.py --flin-source-report
python flin_desktop.py --flin-discovery-info
python flin_desktop.py --flin-association-audit

# Recover missed associations from up to 200 cached sources
python flin_desktop.py --flin-repair-associations 200

# Inspect the experimental shortcut-memory policy
python flin_desktop.py --flin-efficiency-report

# Run an association simulation
python flin_desktop.py --flin-simulate "eigenvalue"

# List independent networks
python flin_desktop.py --list-networks

# Export a verified complete database and a separate FLIN graph
python flin_desktop.py --export-network ./exports --export-format sqlite

# Verify an exported snapshot or its containing directory
python flin_desktop.py --verify-export ./exports/EXPORT_FOLDER
```

`--flin-association-audit` is read-only.

`--flin-repair-associations` **changes learning state**, so back up the network and stop active collectors before performing a repair.

## Complete SQLite exports and continued training

Choose **Export Complete Network** in the desktop application, or use the CLI export command above.

The verified SQLite export creates a folder containing:

| File | Purpose |
| --- | --- |
| `association.sqlite3` | **Complete FLIN application snapshot**, including learning state and supporting tables; use this for import and continued training. |
| `flin_graph.sqlite3` | **Standalone associative graph** with all FLIN units and directed links mapped to convenient `units`/`edges` tables for external analysis. |
| `FLIN_EXPORT_VERIFICATION.json` | Exact memory/link counts and export-integrity summary. |

The active FLIN graph is stored in **`abc_units`** and **`abc_edges`**.

Older `units`/`edges` tables serve different legacy research functions. Confusing these sets of tables can make a complete network look incomplete.

The full export is made from a consistent SQLite snapshot; display sampling is not applied.

The standalone graph file is intended for analysis and is **not** a substitute for the complete application snapshot when resuming training.

To share a pretrained network, publish the verified `association.sqlite3` as a GitHub Release asset (together with its verification report and a description of the source data).

Check the database for private content before sharing.

Importing a complete snapshot into FLIN allows another researcher to continue from the saved network state.

## Data integrity and research limits

- Persistent memory state is stored in SQLite; independent networks can be created, imported, exported, and switched.
- Links are **directed associations** formed from qualified input evidence, not verified mathematical implications.
- A plateau in the number of new links can mean stronger existing links, singleton input clusters, limited new evidence, or an extraction bottleneck. The association audit helps distinguish these cases.
- Local LLM reviews can be wrong. Human mathematical review and external literature checks remain necessary before calling a question novel or a theorem proved.
- The 3D display is a sampled view of the network, not an exhaustive rendering or a numerical proof about cognition.
- Hardware recommendations are adaptive estimates. Actual performance also depends on academic APIs, PDF processing, model size, and SQLite write contention.

## Research direction

FLIN aims to study how a machine can use previously learned mathematical structures to **construct and test new connections between frameworks**.

Next steps include large-scale learning-quality benchmarks, reproducible association experiments, stronger mathematical verification, and analysis of whether network structure predicts useful knowledge transfer.

**FLIN is a research tool for studying associative learning—not a finished model of human intelligence.**
