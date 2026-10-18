# FLIN — Feature-Link Intellegence Network

**A brain-inspired, source-grounded associative memory system for mathematical research.**

[GitHub Repository](https://github.com/jjy246/FLIN-Research)

FLIN is an experimental Python desktop application that builds a persistent network of mathematical memory units and directed, weighted associations from research literature. It is designed to investigate how source-grounded experiences can form reusable memories, how association pathways develop, and whether existing mathematical frameworks can help generate new, testable research questions.

> **Research status:** FLIN is an experimental research prototype. An association is not a proven mathematical implication. Model-generated questions, scores, and novelty claims require independent mathematical and literature review.

## Features at a glance

| Component | Current capability |
| --- | --- |
| Literature acquisition | Discovers mathematical topics and gathers source information using Wikipedia, arXiv, Crossref, local caches, and optional OpenAlex integration. |
| Attention / input extraction | Identifies source-grounded mathematical features and ordered effective-input clusters without semantic embeddings. |
| SSRS memory learning | Forms triggerable memories and learns directed associations from qualified input sequences. |
| Association maintenance | Reinforces existing links; supports auditing and bounded recovery of missed associations from stored sources. |
| Associative pulse simulation | Routes each pulse along one eligible outgoing edge using normalized connection weights. |
| Shortcut memory research | Experiments with source-supported reusable patterns under a heuristic association-cost model. |
| Interactive 3D graph | Provides a desktop topology viewer with node selection, navigation, and bounded rendering for large graphs. |
| Research question generation | Generates **1–20 questions** for **one or multiple requested topics** using optional local Ollama models. |
| Iterative model review | Runs **1–20 user-selected review rounds per question**, sequentially, with topic-linkage assessment and saved revisions. |
| Complete network export | Provides verified SQLite backups for continued training and a separate associative-graph database for analysis. |
| Hardware-aware operation | Detects available resources and provides adaptive CPU/worker recommendations. |

## 1. Learning architecture

```text
Mathematical topics / papers
             |
             v
  Source and quality checks
             |
             v
  Attention: feature extraction
             |
             v
   Effective input clusters
             |
             v
            SSRS
             |
             v
  Triggerable memory units
             |
             v
 Directed, weighted associations
             |
             +----> Reinforce observed associations
             +----> Evaluate shortcut patterns
             |
             v
     Persistent SQLite memory
             |
             +----> Single-path pulse simulation
             +----> Interactive 3D exploration
             +----> Research question generation
```

### Memory formation and evidence

FLIN can form a triggerable memory unit after its **first qualified effective input**. Later source-grounded observations can reinforce existing memories or their associations rather than creating duplicates.

The learning pipeline retains source identifiers and effective-input records to support inspection and recovery. Recent extraction improvements address missed mathematical terminology, multi-concept neighboring sentences, and cached papers that did not previously yield useful associative inputs.

**Important distinction:** Ordered, source-observed association does not establish theorem-level causality, logical implication, or equivalence. FLIN does not create an arbitrary mathematical relation merely because two terms appear in the same paper.

### Directed, weighted pulse routing

For memory unit \(i\), let \(A_i\) be the set of eligible outgoing neighbors at that instant. The probability of selecting \(i\to j\) is

$$
P(i\to j\mid A_i)=\frac{w_{ij}}{\sum_{k\in A_i}w_{ik}},\qquad j\in A_i.
$$

A pulse selects **one eligible outgoing connection at a time**; it does not split across multiple edges. The simulator respects immediate-backtracking restrictions and configured revisit limits. No independent link-transmission probability or spontaneous pulse-decay mechanism is added. Safety guards are implementation constraints, not biological hypotheses.

### Experimental shortcut memories

FLIN can evaluate repeatedly supported ordered patterns for reuse as composite/shortcut memories. The estimated association-cost reduction is an **experimental heuristic**, not evidence that biological learning or actual runtime costs have been optimized.

## 2. Mathematical research question generation

Research question generation is an **optional local Ollama workflow**, separate from the source-driven memory learning rules.

### Choose your question count and research topics

- Generate **1–20 questions per set** (default: 10).
- Enter **one topic or multiple topics**; the process is not restricted to three fields.
- For multiple topics, assess whether **each requested topic has a substantive mathematical role** and whether the proposed relationships are meaningful rather than keyword-only.
- For a single topic, assess genuine relevance and mathematical specificity without inventing artificial cross-disciplinary requirements.
- Save the chosen question count and review settings in SQLite to support resumption.

For example, a request involving `linear algebra, calculus, finance` should use mathematical objects from all three domains: such as covariance matrices, derivatives or optimization dynamics, and a financial objective. Merely mentioning the words is insufficient.

### User-controlled iterative review: no extra final model review

**Each question is processed sequentially to reduce competition for local GPU memory.** The user chooses **1–20 review rounds per question** (default: 3).

```text
Question 1: Draft
    |
    v
Review 1 --> Revise --> Review 2 --> Revise --> ... --> Review N
    |
    v
Select the highest-scoring ALREADY REVIEWED version from SQLite
    |
    v
Save result and proceed to Question 2
```

**There is no extra "final grand review."** A revision is evaluated in the next requested review round; the final requested round evaluates its candidate without creating another unreviewed revision. Thus **N rounds mean N evaluations and at most N−1 between-round revisions**. The program does not stop early just because a score plateaus; if an actual model error interrupts a question, the recorded versions remain available for resumption.

Review criteria include:

- Mathematical objects and definitions
- Explicit assumptions and quantifiers
- Verifiability (proof or counterexample)
- Available source evidence
- Mathematical depth
- **Topic coverage and substantive topic linkage**

The reviewer records numerical scores, specific weaknesses, topic-alignment information, and revision history. Reviews use bounded, structured JSON stages rather than requiring one essay-sized model response.

**Selection is not certification.** At the end, FLIN selects the highest-scoring **already evaluated** version from stored records. If that version still lacks required topics or has weak mathematics, the deficiency remains visible in the score and exported report. It is a **reviewed research candidate**, not an independently validated theorem or novel contribution. An unfinished review sequence must not be presented as completed.

### Reader-friendly question exports

Question sets can be exported in concise **TXT** form for reading and structured **JSON** form for further analysis. A human-readable question emphasizes:

1. Title and requested topics
2. Mathematical objects and essential assumptions
3. One precise research question or proposition
4. A short review summary and any unresolved warning

Detailed scoring, versions, and review metadata remain available through the stored records and structured export. Short output must not omit assumptions needed to make a claim mathematically meaningful.

## 3. Interactive 3D network

FLIN includes a **Tkinter + Matplotlib** desktop viewer for exploring memory units and directed associations. The viewer supports interactive navigation and inspection of selected memories and their outgoing weighted links.

The current implementation uses a **topology-based graph layout**; its displayed XYZ positions should **not** be interpreted as empirically measured propagation depth, branching entropy, and feedback-initiation rate. Those three proposed *Association Dynamics Space* coordinates remain a research direction rather than an implemented measurement in this source version.

Large networks use bounded rendering (the default overview budget is approximately **2,200 nodes** and **3,500 links**). These are **display limits only**. They do not limit the number of memory units or edges stored in the database or exported in a complete snapshot.

## 4. Learning health, recovery, and network growth

FLIN distinguishes newly created directed links from additional observations that reinforce existing links. Therefore, a stable **edge count** does not necessarily mean association learning has stopped.

Recent updates improve recovery for source material that previously formed isolated memories without enough usable ordered links. The recovery process re-examines cached source text in bounded batches and avoids treating the same previously learned input as an entirely new observation.

Use the read-only association audit to inspect active memory counts, link counts, isolated units, and input-cluster characteristics. Recovery modifies learning state: **back up the database and stop background collection before running it**.

Source acquisition can encounter provider quotas, failures, and timeouts. Finishing the **currently discovered** literature frontier does not mean FLIN has learned all available mathematics.

## 5. Installation

**Requirements:** Python **3.10+**, Tkinter, a graphical desktop for the GUI, and these Python packages:

- `numpy`
- `matplotlib`
- `networkx`
- `requests`
- `beautifulsoup4`
- `scikit-learn`

**Optional:** `PyMuPDF` for PDF extraction, `psutil` for richer hardware detection, and [Ollama](https://ollama.com/) for generating and reviewing questions locally.

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

Install Python with Tk support, then run:

```powershell
py -m pip install numpy matplotlib networkx requests beautifulsoup4 scikit-learn
py flin_desktop.py
```

If your checkout includes `start_windows.bat`, you can use that launcher instead.

**File naming:** The GitHub entry point is `flin_desktop.py`; the developer's Ubuntu working copy is named `questioning.py`. These are the same program when their contents are synchronized.

### Optional Ollama setup

Install and start Ollama, then download a compatible locally available instruct model. The review stage uses a single selected model to avoid repeated model switching on memory-constrained computers.

For example, to request an installed lighter review model:

```bash
export BRAIN_REVIEW_MODEL=qwen2.5:3b
python flin_desktop.py
```

On Windows Command Prompt:

```bat
set BRAIN_REVIEW_MODEL=qwen2.5:3b
py flin_desktop.py
```

The exact model choice and attainable review speed depend on available RAM, GPU memory, and Ollama configuration. Smaller models may be more resource-efficient but can be less reliable at mathematical review.

## 6. Useful command-line commands

Run from the project directory. Substitute `python3` (Linux) or `py` (Windows) for `python` if needed.

```bash
# Show all available options
python flin_desktop.py --help

# Inspect the active FLIN network and hardware recommendations
python flin_desktop.py --flin-info
python flin_desktop.py --cpu-info

# Inspect discovery, sources, and association-learning health
python flin_desktop.py --flin-discovery-info
python flin_desktop.py --flin-source-report
python flin_desktop.py --flin-association-audit

# Re-examine up to 200 stored sources for missed associations (modifies the DB)
python flin_desktop.py --flin-repair-associations 200

# Inspect source-supported shortcut-memory decisions
python flin_desktop.py --flin-efficiency-report

# Simulate an associative pulse response
python flin_desktop.py --flin-simulate "eigenvalue"

# Manage independent networks
python flin_desktop.py --list-networks
python flin_desktop.py --new-network "Mathematics Lab"

# Export and verify a complete network snapshot
python flin_desktop.py --export-network ./exports --export-format sqlite
python flin_desktop.py --verify-export ./exports/EXPORT_FOLDER
```

`EXPORT_FOLDER` is a placeholder for the actual directory generated by the export command. Read-only diagnostics do not replace a backup before repair or import operations.

## 7. SQLite data and pretrained-network sharing

FLIN stores its active associative graph primarily in:

- **`abc_units`** — FLIN memory units and activation status
- **`abc_edges`** — directed, weighted FLIN associations
- **`abc_input_clusters`** and related tables — effective input and learning evidence

Legacy `units` / `edges` tables serve a different purpose and should not be mistaken for the complete FLIN associative graph.

### Complete SQLite export

The full SQLite export provides:

| File | Purpose |
| --- | --- |
| **`association.sqlite3`** | Full FLIN application snapshot, including training state and supporting tables. **Use this to import and continue training.** |
| `flin_graph.sqlite3` | Standalone representation of the associative nodes and directed edges for external graph tools. **For analysis, not continuation training.** |
| `FLIN_EXPORT_VERIFICATION.json` | Export integrity results and source/snapshot graph counts. |

The complete export checks database integrity and FLIN memory/link counts; the 3D display sample is **not** used as the export source. Portable compressed JSONL export is also supported.

To share a pretrained network, publish a verified `association.sqlite3` and the verification report as GitHub Release assets. Users can import the full snapshot and continue training from its saved state. Before distribution, inspect the archive for private source data or other information not intended for publication.

## 8. Research boundaries and next steps

FLIN is intended for reproducible experiments in associative learning and mathematical knowledge transfer, not for automatic proof certification.

- Learned directed edges encode qualified associative evidence, **not** proven logical or causal relationships.
- A model's review score is a heuristic judgment, **not** a verified mathematical result.
- Topic linkage is checked during the selected review rounds; missing topics remain visible rather than being hidden by a final acceptance filter.
- Actual CPU/GPU throughput depends on model size, API limits, RAM, disk I/O, and SQLite contention; hardware recommendations are estimates, not performance guarantees.
- Current 3D geometry is primarily a network-layout visualization, not yet an observational XYZ measurement of pulse dynamics.
- Large-scale accuracy, research novelty, and real-world speedup require external benchmarks and independent replication.

**Long-term objective:** Investigate whether a persistent associative memory system can reuse known mathematical structures to formulate and test meaningful relationships across research fields.

---

**FLIN is an experimental platform for researching associative intelligence—not a finished model of human cognition.**
