# FLIN

**Feature-Link Intelligence Network | Brain_Project**

**Automatic Mathematical Literature Discovery · Persistent Associative Memory · Color-Coded SSRS Fast Memory Groups**

FLIN is an experimental, brain-inspired associative learning system written in Python.

It investigates how repeated, source-grounded experiences can build persistent memory units, directed connections, and faster transmission routes.

**No manual document upload is required.**

Starting with an empty network, FLIN can automatically discover mathematical literature, extract available text, build memory units, and form SSRS fast memory groups as part of the same network-building process.

> **Research Status:** FLIN is an experimental research prototype. It does not claim to reproduce biological neural mechanisms or mathematically verify theorems. SSRS is an experimentally testable engineering model.

---

## 1. Project Overview

FLIN explores a fundamental question:

**Can an intelligent system construct useful knowledge structures from repeated experiences rather than relying primarily on pretrained semantic representations?**

The system focuses on:

- Experience-driven memory formation
- Persistent memory construction
- Directed associative connections
- Repeated-input reinforcement
- Dynamic network construction
- SSRS fast transmission pathways
- Automatic fast memory group formation
- Source-grounded mathematical knowledge
- Cross-document knowledge integration
- Interactive 3D visualization

FLIN does not require semantic embeddings for constructing its core associative memory network.

Its primary objective is to investigate whether structured memory and repeated associations can provide a foundation for more general learning capabilities.

---

## 2. What's New in v24.0?

FLIN v24.0 integrates automatic SSRS formation directly into the literature-driven network construction process.

When the user clicks **Start Auto Building (Literature + SSRS)**, FLIN attempts to:

1. Discover mathematical subjects using Wikipedia and its research-discovery pipeline.
2. Find relevant papers through available academic sources and the local literature catalog.
3. Read available article excerpts, abstracts, and optionally extractable open-access PDF text.
4. Divide source material into effective input clusters.
5. Identify mathematical concepts and create or update memory units.
6. Learn and reinforce directed associative connections.
7. Measure how frequently memory units co-occur in distinct input clusters within the same source.
8. Promote qualifying existing directed connections to SSRS fast roads.
9. Organize source-supported fast roads into persistent fast memory groups.
10. Display these groups directly in the main 3D memory network using distinct colors.

Memory units, connections, fast roads, groups, and supporting evidence are saved in SQLite.

Users do not need to manually import documents, separately trigger SSRS learning, or apply the resulting groups to another network.

### Key Features

| Feature | Description |
|---|---|
| Automatic Literature Discovery | Automatically discovers mathematical subjects and research papers |
| Automatic Memory Construction | Creates persistent memory units from available academic text |
| Directed Association Learning | Establishes and reinforces directed associative connections |
| Co-occurrence Analysis | Measures repeated concept co-occurrence within individual sources |
| Automatic SSRS Formation | Promotes qualifying connections to fast transmission pathways |
| Fast Memory Groups | Organizes source-supported fast roads into persistent groups |
| Automatic Group Coloring | Assigns distinguishable colors to different groups |
| Main 3D Network Integration | Displays SSRS groups directly inside the primary memory network |
| Persistent Learning | Preserves memory structures across application restarts |
| Source Evidence Tracking | Retains supporting text and source information |
| Network Export | Supports exporting memory structures and associated evidence |

---

## 3. System Architecture

FLIN v24.0 uses the following architecture:

```text
┌────────────────────────────────┐
│       Empty FLIN Network       │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│    Automatic Literature        │
│          Discovery             │
│                                │
│   Wikipedia / arXiv / Crossref │
│   Other Available Sources      │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│    Mathematical Text           │
│         Extraction             │
│                                │
│  Abstracts / Articles / PDFs   │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│     Effective Input Clusters   │
│                                │
│    Source + Position + Text    │
└───────────────┬────────────────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
┌────────────────┐ ┌────────────────┐
│  Memory Unit   │ │ Co-occurrence  │
│  Construction  │ │    Analysis    │
└────────┬───────┘ └────────┬───────┘
         │                  │
         ▼                  │
┌────────────────┐          │
│   Directed     │          │
│ Associations   │◄─────────┘
└────────┬───────┘
         │
         ▼
┌────────────────────────────────┐
│    Automatic SSRS Road         │
│          Formation             │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│    SSRS Fast Memory Groups     │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│       Colored 3D FLIN          │
│        Memory Network          │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│       Persistent SQLite        │
└────────────────────────────────┘
```

All memory units, associative connections, and SSRS transmission pathways belong to the same persistent FLIN network.

---

## 4. Memory Units

Memory units represent mathematical concepts extracted from observed information.

Examples include:

- Matrix
- Eigenvalue
- Eigenvector
- Fourier Transform
- Laplace Transform
- Differential Equation
- Stochastic Process
- Spectral Theory
- Linear Operator
- Numerical Analysis

When the system identifies a mathematical concept, it checks whether a corresponding memory unit already exists.

If the memory unit does not exist, a new unit may be created.

If it already exists, additional source-grounded observations can be incorporated into the existing memory structure.

Memory units are stored in:

`abc_units`

The network persists after the application closes.

---

## 5. Directed Associative Network

FLIN uses directed associative connections between memory units.

For example:

```text
A → B
```

This connection does not automatically imply:

```text
B → A
```

Each directed connection maintains information about its strength and previous observations.

Connections are stored in:

`abc_edges`

### Connection Strength

The strength of a directed connection is represented by:

\[
w_{ij}
\]

where:

- \(i\): Source memory unit
- \(j\): Destination memory unit
- \(w_{ij}\): Strength of the directed association

Connection strengths can change as additional valid observations enter the network.

In the associative pulse simulation, a pulse selects one available route at a time.

Stronger connections generally have a greater probability of being selected under the model's routing rules.

The associative network serves as the foundation for SSRS fast transmission pathways.

---

## 6. SSRS — Sensory Shaping Routing System

SSRS is FLIN's fast transmission mechanism.

It investigates whether repeatedly reinforced associative connections can become more efficient pathways for information transmission.

SSRS does not replace the original memory network.

Instead, it adds fast transmission eligibility to existing directed connections.

### Normal Associative Transmission

```text
A ────────► B ────────► C
```

### SSRS Fast Transmission

```text
A ════════► B ════════► C
```

Here:

- `────►` represents an ordinary associative connection.
- `════►` represents an SSRS fast transmission pathway.

Fast transmission pathways preserve the original direction of their underlying associative connections.

They do not automatically create reverse connections.

SSRS fast roads are stored in:

`ssrs_fast_roads`

Supporting ordered-input observations are recorded in:

`ssrs_road_evidence`

---

## 7. Automatic SSRS Formation

Version 24 introduces automatic SSRS construction based on repeated co-occurrence within individual research sources.

### 7.1 Concept Co-occurrence

Consider a research paper containing the following effective input clusters:

```text
Input Cluster 1:
Matrix, Eigenvalue, Eigenvector

Input Cluster 2:
Matrix, Eigenvalue

Input Cluster 3:
Matrix, Eigenvalue, Spectral Theory

Input Cluster 4:
Eigenvalue, Eigenvector
```

The system calculates how frequently different memory units appear together.

For example:

```text
Matrix + Eigenvalue = 3

Matrix + Eigenvector = 1

Eigenvalue + Eigenvector = 2
```

These observations provide evidence of repeated associations within the same source.

However, co-occurrence alone does not establish mathematical implication, causality, or semantic equivalence.

### 7.2 Mathematical Definition

Let:

\[
X_k
\]

represent the \(k\)-th effective input cluster within source document \(s\).

The co-occurrence count of memory units \(u\) and \(v\) is:

\[
C_s(u,v)
=
\sum_{k=1}^{N_s}
\mathbf{1}
\left(
u\in X_k
\land
v\in X_k
\right)
\]

where:

- \(s\): Source document
- \(N_s\): Number of effective input clusters in that document
- \(u,v\): Memory units
- \(C_s(u,v)\): Number of clusters containing both memory units
- \(\mathbf{1}\): Indicator function

Two memory units contribute to the count only when they appear within the same effective input cluster.

Simply appearing somewhere in the same research paper is insufficient.

### 7.3 Fast-Road Qualification

For source document \(s\), define:

- \(M_s(u)\): Number of distinct input clusters containing \(u\)
- \(C_s(u,v)\): Number of distinct clusters containing both \(u\) and \(v\)
- \(E(u,v)\): Whether the directed connection \(u \rightarrow v\) already exists
- \(N(u,v)\): Accumulated observations of the directed connection
- \(X(u)\): Effective exposure count of memory unit \(u\)
- \(W(u,v)\): Current connection strength

The default co-occurrence-driven eligibility conditions are:

```text
M_s(u) >= 2
M_s(v) >= 2
C_s(u,v) >= 2
E(u,v) = True
N(u,v) >= 2
X(u) >= 3
X(v) >= 3
W(u,v) >= 0.5
```

When these conditions are satisfied, an existing directed connection may be promoted to an SSRS fast road.

The ordered-input SSRS mechanism remains available as another source of supporting evidence.

### 7.4 Important Constraints

SSRS does not create arbitrary associations solely because two concepts appear together.

For example:

```text
A → B
```

may become:

```text
A ═════► B
```

However, this does not automatically create:

```text
B ═════► A
```

Repeated co-occurrence is treated as evidence for routing eligibility, not proof of a mathematical relationship.

### 7.5 Default Parameters

The current default values in `flin_desktop.py` are:

```python
SSRS_GROUP_MIN_MENTIONS = 2

SSRS_AUTO_COOCCURRENCE_MIN_CLUSTERS = 2

SSRS_GROUP_MIN_PAIR_EVENTS = 2

SSRS_GROUP_MAX_SOURCE_MEMORIES = 160

SSRS_EVIDENCE_MIN_CLUSTERS = 2

SSRS_EVIDENCE_MIN_EXPOSURES = 3

SSRS_EVIDENCE_MIN_WEIGHT = 0.5
```

These values are experimental parameters.

Increasing the thresholds generally reduces the number of qualifying fast roads.

Decreasing them may increase the influence of incidental co-occurrence.

---

## 8. SSRS Fast Memory Groups

SSRS Fast Memory Groups are collections of existing memory units connected through source-supported fast transmission pathways.

For example, one research paper may repeatedly discuss:

```text
Matrix
Eigenvalue
Eigenvector
```

Another paper may repeatedly discuss:

```text
Eigenvalue
Spectral Theory
Linear Operator
```

If their supporting evidence and directed connections satisfy the SSRS requirements, separate groups may emerge.

### Group A

```text
Matrix ═══► Eigenvalue ═══► Eigenvector
```

### Group B

```text
Eigenvalue ═══► Spectral Theory ═══► Linear Operator
```

The groups exist directly within the main FLIN associative network.

They do not require separate memory databases.

### Overlapping Groups

A memory unit may participate in multiple fast memory groups.

For example:

`Eigenvalue`

may belong to both Group A and Group B.

FLIN does not need to create duplicate memory units.

The same underlying memory unit can participate in several source-supported associative structures.

---

## 9. Automatic Group Coloring

FLIN automatically assigns different colors to distinguish SSRS fast memory groups.

Example:

```text
Group A → Blue

Group B → Orange

Group C → Green

Group D → Purple
```

Actual colors are assigned by the application.

Group information and colors are stored persistently.

### Visualization Rules

| Visual Element | Meaning |
|---|---|
| Normal Memory Unit | A learned mathematical concept |
| Colored Memory Unit | A memory unit belonging to a displayed SSRS group |
| Ordinary Connection | A regular directed associative link |
| Colored Fast Connection | A directed connection eligible for SSRS fast transmission |
| Different Group Colors | Different source-supported fast memory groups |
| Selected Group | Focused inspection of one group's structure and evidence |

Colors identify groups.

They do not represent mathematical accuracy, confidence, or importance.

When a memory unit belongs to multiple groups, the overview may display only one group color.

Users can select individual groups to inspect overlapping membership.

---

## 10. Installation

### Requirements

- Python 3.10+
- Ubuntu 24.04 recommended
- Tkinter
- NumPy
- Matplotlib
- NetworkX
- Requests
- BeautifulSoup4
- Scikit-learn
- PyMuPDF

### Install System Dependencies

```bash
sudo apt update
sudo apt install python3-tk python3-venv
```

### Create a Python Virtual Environment

```bash
python3 -m venv .venv
```

Activate the environment:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install Python dependencies:

```bash
python -m pip install numpy matplotlib networkx requests beautifulsoup4 scikit-learn pymupdf
```

Ollama is optional for automatic literature ingestion and SSRS formation.

Some separate mathematical generation and evaluation features may require Ollama.

---

## 11. Getting Started

### Step 1 — Launch FLIN

```bash
python flin_desktop.py
```

### Step 2 — Create an Empty Memory Network

Navigate to:

`02A FLIN Directed Pulse Association`

Click:

`New Empty FLIN Network (no data copied)`

FLIN creates a separate SQLite memory network without overwriting existing networks.

### Step 3 — Start Automatic Network Building

Navigate to:

`04 Automatic Network Building`

Optionally enable:

`Read Open-Access PDFs When Available`

Then click:

`Start Auto Building (Literature + SSRS)`

The system begins automatically:

1. Discovering mathematical research topics.
2. Searching for academic literature.
3. Extracting available mathematical text.
4. Constructing effective input clusters.
5. Creating memory units.
6. Learning directed associative connections.
7. Measuring source-specific co-occurrence.
8. Establishing qualifying SSRS fast roads.
9. Constructing fast memory groups.
10. Updating the main 3D network.

**No manual document input is required.**

### Step 4 — Observe the 3D Network

The main 3D visualization displays:

- Learned memory units
- Ordinary associative connections
- SSRS fast transmission pathways
- Color-coded fast memory groups

As new literature is processed, the network visualization updates.

### Step 5 — Inspect Fast Memory Groups

Navigate to:

`02B SSRS Fast Memory Groups`

Click:

`Inspect Groups + Evidence`

Available information includes:

- Group identity
- Source literature
- Group color
- Memory unit members
- Observation counts
- Fast-road directions
- Supporting source passages

### Step 6 — Stop Network Building

Click:

`Stop and Save`

Previously committed memory units, associative connections, fast roads, and groups remain stored in SQLite.

### Continuous Discovery

The option:

`Continuous discovery and periodic retry (until stopped)`

is enabled by default.

Disabling it allows a bounded collection based on the configured topic and paper limits.

Continuous discovery does not guarantee unlimited new literature or unrestricted access to external research APIs.

---

## 12. Literature Sources

FLIN uses its existing research discovery and retrieval workflow.

Potential sources include:

- Wikipedia
- arXiv
- Crossref
- Local Literature Catalog
- Other supported academic sources

Optional providers, including OpenAlex, may require additional configuration.

Literature availability depends on external services, licensing, API limits, and open-access availability.

FLIN cannot guarantee that every research paper has an accessible full-text PDF.

When full text is unavailable, the system may learn from available abstracts or article excerpts.

---

## 13. Database Architecture

FLIN stores its persistent memory network using SQLite.

### Main Tables

| Table | Purpose |
|---|---|
| `abc_units` | Persistent memory units |
| `abc_edges` | Directed associative connections |
| `abc_ssrs` | Memory exposure and routing-related state |
| `abc_sources` | Literature source metadata |
| `abc_input_clusters` | Effective input clusters |
| `abc_cluster_features` | Memory units detected in each cluster |
| `ssrs_fast_roads` | SSRS high-speed transmission pathways |
| `ssrs_road_evidence` | Ordered-input evidence for fast roads |
| `ssrs_cooccurrence_evidence` | Source-specific co-occurrence evidence |
| `ssrs_memory_groups` | Persistent fast memory groups |
| `ssrs_memory_group_members` | Group membership and observations |
| `ssrs_memory_group_roads` | Fast roads belonging to each group |

### Default Storage Location

```text
~/.local/share/brain_project/
```

Independent memory networks:

```text
~/.local/share/brain_project/networks/
```

Network registry:

```text
~/.local/share/brain_project/network_registry.json
```

Stored memory networks remain available after the application closes.

Version 24 also supports incremental reconstruction of SSRS group evidence for previously saved literature.

---

## 14. Command-Line Interface

### Run Offline Self-Test

```bash
python flin_desktop.py --ssrs-self-test
```

### List Available Networks

```bash
python flin_desktop.py --list-networks
```

### Inspect SSRS Fast Roads

```bash
python flin_desktop.py --ssrs-report
```

### Inspect Fast Memory Groups

```bash
python flin_desktop.py --ssrs-groups-report
```

### Rebuild Historical SSRS Groups

```bash
python flin_desktop.py --ssrs-rebuild-groups 300
```

This command rebuilds groups for up to 300 previously stored sources.

It is intended for diagnostics and historical-data migration.

Regular automatic network building already includes SSRS formation.

### Show Available Arguments

```bash
python flin_desktop.py --help
```

---

## 15. Network Export and Persistence

FLIN supports network export and backup.

Stored information includes:

- Memory units
- Directed associative links
- Effective input clusters
- Source evidence
- SSRS fast roads
- Co-occurrence evidence
- Fast memory groups
- Group membership

Export options include:

- Complete SQLite snapshots
- Portable JSONL-based network data

A screenshot of the 3D visualization is not equivalent to a complete network backup.

The database remains the authoritative source of network information.

---

## 16. Known Limitations

FLIN v24.0 remains an experimental research prototype.

### Mathematical Understanding

The current mathematical concept extraction process relies primarily on text analysis and rule-based identification.

It does not guarantee complete understanding of:

- Mathematical proofs
- Symbolic expressions
- Mathematical equivalence
- Theorem dependencies
- Formula semantics

### Co-occurrence Is Not Mathematical Implication

Two concepts frequently appearing together does not mean they have a mathematically necessary relationship.

SSRS constructs fast transmission pathways based on repeated observations and existing associative structures.

### Literature Availability

Not all research papers provide accessible full text.

External APIs, network availability, and PDF extraction quality may limit the available information.

### Directionality

SSRS preserves the original direction of associative connections.

It does not automatically introduce reverse connections.

### Fast Hops

A pulse simulation may report zero fast hops even when SSRS fast roads exist.

This can occur when the simulated pulse does not select an available fast route.

### Visualization

Large networks may exceed the number of nodes that can be rendered interactively.

The 3D display may show only a subset of the complete stored graph.

### Research Validation

SSRS formation rules are experimental engineering assumptions.

Their effectiveness must be evaluated through reproducible experiments and comparison with appropriate reference structures.

---

## 17. Suggested Experiments

### Experiment A — Automatic Memory Construction

Create a new empty memory network.

Automatically collect a bounded set of related mathematical research papers.

Measure:

1. Number of memory units created.
2. Number of directed associations established.
3. Number of effective input clusters.
4. Number of SSRS fast roads.
5. Number of fast memory groups.

### Experiment B — Co-occurrence Threshold Analysis

Use a fixed collection of research documents.

Compare different SSRS co-occurrence thresholds.

Evaluate how threshold changes affect group formation, noise, and structural stability.

### Experiment C — Cross-Document Learning

Automatically collect literature from related research areas.

Examples:

- Linear Algebra
- Spectral Theory
- Numerical Analysis
- Differential Equations

Investigate whether shared concepts participate in multiple source-supported fast memory groups.

### Experiment D — Directionality Validation

Sample established SSRS fast roads.

Verify that each road corresponds to an existing directed association in `abc_edges`.

### Experiment E — Knowledge Structure Evaluation

Construct a manually annotated reference network.

Compare the automatically generated FLIN structures against it.

Suggested metrics:

- Precision
- Recall
- Group Stability
- Source Consistency
- Association Reproducibility

### Experiment F — Fast Transmission

Select an identical starting memory unit across repeated pulse simulations.

Measure:

- Ordinary associative hops
- SSRS fast hops
- Activated memory units
- Transmission time
- Response distribution

These measurements can help evaluate whether SSRS pathways provide functional benefits beyond ordinary associative connections.

---

## 18. Research Roadmap

### Phase 1 — Persistent Associative Memory

Construct and maintain a source-grounded memory network.

### Phase 2 — Automatic SSRS Formation

Automatically establish fast associative transmission pathways through repeated observations.

### Phase 3 — Knowledge Structure Validation

Evaluate whether fast memory groups represent useful conceptual structures.

### Phase 4 — Cross-Document Knowledge Integration

Investigate how knowledge extracted from different sources interacts within a shared associative network.

### Phase 5 — Cross-Domain Knowledge Transfer

Explore whether previously learned structures can support the formation of new relationships in unfamiliar domains.

### Phase 6 — Generalized Intelligent Learning

Investigate whether persistent associative memory and adaptive routing can contribute to broader intelligent behavior.

These phases represent research objectives rather than demonstrated capabilities.

---

## 19. Project Philosophy

FLIN is based on a central idea:

**Intelligence may depend not only on what a system knows, but also on how previous experiences reshape the way it processes new information.**

The project investigates whether repeated experiences can gradually shape a persistent associative network and create more efficient pathways for information transmission.

Rather than treating intelligence as a collection of independent benchmark capabilities, FLIN explores how memory structures may develop and reorganize through experience.

The central research question is:

**How can a system use its existing knowledge structures to construct, connect, and internalize previously unknown knowledge?**

---

## 20. Project Status

**Version:** FLIN v24.0

**Project:** Brain_Project

**System:** Feature-Link Intelligence Network

**Executable:** `flin_desktop.py`

**Primary Language:** Python 3.10+

**Interface:** Tkinter + Matplotlib 3D

**Storage:** SQLite

**Primary Research Areas:**

- Brain-Inspired Artificial Intelligence
- Associative Learning
- Persistent Memory
- Experience-Driven Intelligence
- Dynamic Memory Networks
- Mathematical Knowledge Representation
- Fast Transmission Pathways

FLIN is an actively developed research prototype.

Its architecture and learning mechanisms may evolve as experiments reveal new requirements.

---

## Final Research Objective

The ultimate goal of FLIN is not merely to create a larger knowledge database.

It is to investigate whether an intelligent system can continuously construct and reorganize its own memory structures from experience, allowing previously learned knowledge to influence how new information is interpreted and connected.

**FLIN — Rethinking How AI Learns.**
