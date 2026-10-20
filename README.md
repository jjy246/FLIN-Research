# FLIN v23.0 — Feature-Link Intelligence Network

**Source-Grounded Memory Network · SSRS Fast Memory Groups · Desktop 3D Visualization**

FLIN 是 Brain_Project 的 Python 桌面原型。它將數學文件與文獻中的有效輸入，轉換為可持久化的**記憶元（memory units）**和**單向聯想連結（directed associative links）**，再依照多次觀測的證據決定哪些連結取得 **SSRS（感官塑路系統）高速傳遞資格**。

**v23 的重點：本機文件與線上文獻使用同一個 FLIN 記憶網路。**

讀取文件後形成的快速記憶元組不再只是另外一個實驗視窗裡的圖，它會存進原本的 SQLite，並以不同顏色直接疊加在主畫面的 3D 記憶網路上。

新建空白網路後，不需要預先下載論文或建立節點，便能直接讀取第一篇文件開始建網。

> **Research Status:** FLIN is an experimental brain-inspired associative learning system. It does not claim to reproduce biological neural mechanisms or mathematically verify theorems. SSRS fast roads represent learned transmission pathways supported by repeated observations.

---

## 1. Overview

FLIN explores a fundamental question:

**Can an intelligent system construct useful knowledge structures from repeated experiences instead of relying primarily on pretrained semantic representations?**

The system focuses on:

- Experience-driven memory formation
- Directed associative connections
- Repeated-input reinforcement
- Dynamic network construction
- SSRS fast transmission pathways
- Source-grounded mathematical knowledge
- Persistent memory structures
- Interactive 3D visualization

FLIN does not require semantic embeddings for constructing its associative memory network.

Its primary objective is to investigate whether structured memory and repeated associations can provide a foundation for more general learning capabilities.

---

## 2. Core Architecture

FLIN consists of four major components:

### 2.1 Memory Units

Memory units represent mathematical concepts extracted from observed information.

Examples:

- Matrix
- Eigenvalue
- Fourier Transform
- Differential Equation
- Linear Operator
- Stochastic Process

Memory units are stored in:

`abc_units`

Each memory unit maintains information about its identity, activation eligibility, evidence, and associated connections.

Memory units are persistent.

They are not automatically deleted when the application closes.

### 2.2 Directed Associative Network

Memory units are connected through directed associative links.

For example:

A → B

This connection does not automatically imply:

B → A

The associative network is stored in:

`abc_edges`

Each connection maintains information including:

- Source memory unit
- Destination memory unit
- Connection weight
- Observation count
- Supporting experience

Connection strengths may change as additional valid observations enter the network.

### 2.3 SSRS — Sensory Shaping Routing System

SSRS introduces fast transmission pathways into the associative network.

Repeated valid input observations can establish fast routes between existing memory units.

A fast route does not create a new mathematical relationship.

Instead, it gives an existing directed connection access to a faster transmission mechanism.

For example:

A → B → C

If repeated observations provide sufficient evidence, some of these connections may become SSRS fast roads.

The original memory units remain unchanged.

The fast transmission system is an additional routing mechanism rather than a replacement for the associative network.

Fast roads are stored in:

`ssrs_fast_roads`

Supporting observations are recorded in:

`ssrs_road_evidence`

### 2.4 SSRS Fast Memory Groups

Version 23 introduces persistent SSRS Fast Memory Groups.

A fast memory group consists of existing memory units connected through source-supported SSRS fast roads.

Groups are constructed using repeated observations from the same document or research paper.

For example:

Document A:

Matrix → Eigenvalue → Eigenvector

Document B:

Eigenvalue → Spectral Theory → Linear Operator

If sufficient evidence exists, FLIN may establish separate fast memory groups associated with these documents.

Different groups are displayed using different colors.

A memory unit can belong to multiple groups.

Groups do not create additional conceptual duplicates.

---

## 3. What's New in v23.0

| Feature | Description |
|---|---|
| Empty Network Initialization | Create a completely new FLIN memory network |
| Document-Based Learning | Build memory units directly from documents |
| Automatic SSRS Group Formation | Construct fast memory groups from repeated observations |
| Source-Specific Groups | Preserve the document or paper responsible for each group |
| Persistent Group Colors | Assign different colors to fast memory groups |
| Main 3D Network Integration | Display fast groups directly inside the original memory network |
| Group Filtering | Display all groups or focus on a specific group |
| Group Evidence Inspection | Examine memory members and supporting observations |
| Literature Learning Integration | Automatically update groups during literature collection |
| Persistent SQLite Storage | Preserve memory groups across application restarts |
| Network Export | Export groups together with the underlying memory network |
| Historical Group Reconstruction | Rebuild groups from previously recorded evidence |

---

## 4. Installation

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

### Installation

Create a Python virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install numpy matplotlib networkx requests beautifulsoup4 scikit-learn pymupdf
```

Launch FLIN:

```bash
python FLIN_v23.py
```

Ollama is optional for document ingestion and SSRS fast group construction.

Some additional mathematical generation and evaluation features may require Ollama.

---

## 5. Getting Started

### Step 1 — Create a New Memory Network

Launch FLIN:

```bash
python FLIN_v23.py
```

Navigate to:

`02A FLIN Directed Pulse Association`

Click:

`New Empty FLIN Network (no data copied)`

This creates an independent SQLite memory network.

The new network initially contains no learned memory units or associative connections.

### Step 2 — Import a Document

Click:

`Read Document → Learn FAST Groups (TXT/PDF/MD)`

Supported formats include:

- TXT
- PDF
- Markdown
- TeX
- Other supported text-based formats

Select a document.

The learning process does not automatically begin when a file is selected.

Click:

`▶ 開始讀取`

To interrupt the process:

`■ 結束讀取`

Previously completed and committed observations remain stored.

### Step 3 — Automatic Memory Construction

During document ingestion, FLIN attempts to:

1. Extract document text.
2. Divide text into effective input segments.
3. Identify mathematical concepts.
4. Match concepts with existing memory units.
5. Create new memory units when necessary.
6. Record effective input clusters.
7. Establish or reinforce directed associations.
8. Evaluate SSRS fast-road eligibility.
9. Construct source-specific fast memory groups.
10. Update the persistent memory network.

New documents extend the existing network rather than automatically creating completely separate networks.

### Step 4 — Visualize Memory Groups

After learning, return to the main 3D memory network.

Fast memory groups are displayed directly in the original network.

Different groups receive different colors.

Use:

`02B SSRS Fast Memory Groups`

Available operations include:

- Display all colored groups
- Select an individual group
- Inspect group members
- Inspect supporting evidence
- Focus on a selected group
- Show group connections in the main 3D network

Click:

`Inspect Groups + Evidence`

to examine the structure and evidence of each group.

### Step 5 — Continue Learning

Import additional documents.

FLIN continues learning within the same selected memory network.

Existing memory units may receive additional observations and connections.

New fast memory groups may emerge when the evidence requirements are satisfied.

---

## 6. SSRS Fast Memory Group Formation

### 6.1 Fundamental Principle

A fast memory group should not be established simply because several concepts appear somewhere in the same document.

FLIN considers repeated effective input observations and previously learned directed associations.

The current implementation requires sufficient evidence before an association can become part of a fast memory group.

This distinction is important:

**Co-occurrence alone is not equivalent to a validated mathematical relationship.**

### 6.2 Memory-Level Requirements

A memory unit must appear in at least two distinct effective input clusters from the same source.

Default parameter:

```python
SSRS_GROUP_MIN_MENTIONS = 2
```

This requirement helps identify repeatedly observed concepts.

### 6.3 Connection-Level Requirements

For an association:

A → B

to enter a source-specific fast memory group:

1. The directed connection must already exist in the associative network.
2. It must have SSRS fast-road eligibility.
3. The source document must provide sufficient supporting observations.
4. The connection must satisfy the source-specific evidence threshold.

Default parameter:

```python
SSRS_GROUP_MIN_PAIR_EVENTS = 2
```

### 6.4 Fast-Road Eligibility

The underlying SSRS fast-road mechanism uses separate evidence thresholds.

Current defaults:

```python
SSRS_EVIDENCE_MIN_CLUSTERS = 2
SSRS_EVIDENCE_MIN_EXPOSURES = 3
SSRS_EVIDENCE_MIN_WEIGHT = 0.5
```

These parameters describe:

- Minimum number of distinct supporting input clusters
- Minimum accumulated exposure requirement
- Minimum associative connection weight

The group formation process uses the fast roads that satisfy the underlying SSRS requirements.

### 6.5 Group Construction

Eligible source-supported fast roads are organized into connected groups for visualization.

For example:

A → B

B → C

may be displayed as one fast memory group.

Another independent connection:

D → E

may form a separate group.

Connectivity used for grouping is a visualization and organization rule.

It does not convert directed associations into bidirectional connections.

### 6.6 Performance Limits

The current implementation limits the source-specific candidate inspection process.

Default:

```python
SSRS_GROUP_MAX_SOURCE_MEMORIES = 160
```

This limit controls processing cost.

It is not a theoretical restriction on the possible number of memory units in a fast group.

---

## 7. Group Colors and Visualization

Fast memory groups are represented using different colors in the main 3D network.

### Visual Representation

| Visual Element | Meaning |
|---|---|
| Colored Memory Unit | Memory unit associated with a displayed SSRS fast group |
| Thick Colored Connection | Existing directed association recognized as a source-supported fast road |
| Blue-Gray Connection | Ordinary associative connection |
| Uncolored Memory Unit | Memory unit outside the currently displayed groups |
| Selected Group | Highlights the chosen source-specific fast memory group |

Colors identify groups.

They do not represent mathematical truth, causal certainty, or knowledge quality.

### Overlapping Memory Groups

A memory unit may belong to multiple groups.

Example:

Document A:

A → B

Document B:

B → C

Memory unit B may participate in both groups.

FLIN does not create two separate copies of B.

The same memory unit is shared.

When all groups are displayed, a memory unit receives one display color.

Selecting an individual group allows users to inspect its membership and connections independently.

### Interactive 3D Network

The main visualization supports interactive operations such as:

- Rotation
- Zooming
- Memory selection
- Group inspection
- Connection exploration
- Group-focused visualization

For performance reasons, the 3D visualization may display a subset of the complete stored network.

The SQLite database remains the authoritative source of memory and connection data.

---

## 8. Literature-Based Automatic Network Construction

FLIN can also construct its memory network using mathematical research literature.

Instead of manually importing individual documents, users may start the literature collection pipeline.

Click:

`Start Building (Literature → FLIN)`

The system uses its existing literature collection and filtering mechanisms.

Potential sources include:

- Wikipedia
- arXiv
- Crossref
- OpenAlex, when configured
- Previously collected local literature

Retrieved mathematical information can enter the FLIN learning pipeline.

Each document or paper contributes observations to the shared memory network.

After relevant input and associative processing, FLIN evaluates whether the source supports SSRS fast memory groups.

This makes document-based learning and literature-based network construction part of the same architecture.

---

## 9. Database Architecture

FLIN stores its memory network in SQLite.

### Main Tables

| Table | Purpose |
|---|---|
| `abc_units` | Persistent memory units |
| `abc_edges` | Directed associative connections |
| `abc_input_clusters` | Effective input clusters and their sources |
| `abc_cluster_features` | Memory units identified within input clusters |
| `ssrs_fast_roads` | SSRS high-speed transmission connections |
| `ssrs_road_evidence` | Evidence supporting fast-road eligibility |
| `ssrs_memory_groups` | Persistent fast memory group definitions |
| `ssrs_memory_group_members` | Membership relationships |
| `ssrs_memory_group_roads` | Fast roads belonging to individual groups |
| `ssrs_document_reads` | Document ingestion records |
| `ssrs_document_read_sessions` | Document reading session states |

### Data Persistence

Memory units, associations, fast roads, and fast memory groups are stored persistently.

Closing FLIN does not automatically reset the network.

Different networks can be created and selected independently.

Default storage location:

```text
~/.local/share/brain_project/
```

Independent networks:

```text
~/.local/share/brain_project/networks/
```

Network registry:

```text
~/.local/share/brain_project/network_registry.json
```

Shared literature catalog:

```text
~/.local/share/brain_project/literature_catalog.sqlite3
```

---

## 10. Command-Line Interface

FLIN provides command-line utilities for testing and network management.

### Run Self-Test

```bash
python FLIN_v23.py --ssrs-self-test
```

The self-test uses temporary SQLite data.

It does not intentionally modify the user's existing research network.

### Generate an Example Mathematical Document

```bash
python FLIN_v23.py --ssrs-example example_math.txt
```

This generates a synthetic mathematical document for testing.

It is not a real academic research paper.

### Create a New Network

```bash
python FLIN_v23.py --new-network "FLIN_SSRS_Experiment"
```

### Read a Document

```bash
python FLIN_v23.py --ssrs-read-document example_math.txt
```

The document is processed into the currently selected network.

### Inspect Fast Memory Groups

```bash
python FLIN_v23.py --ssrs-groups-report
```

### Rebuild Groups From Existing Evidence

```bash
python FLIN_v23.py --ssrs-rebuild-groups 300
```

### Inspect SSRS Fast Roads

```bash
python FLIN_v23.py --ssrs-report
```

### List Available Networks

```bash
python FLIN_v23.py --list-networks
```

---

## 11. Exporting and Backing Up Networks

FLIN supports persistent network export.

Users can export network data using the existing network export functions.

Supported export approaches include:

- Complete SQLite snapshot
- Portable JSONL-based network export

Version 23 includes SSRS group information in the exported network data.

Relevant information includes:

- Memory units
- Associative connections
- Fast roads
- Fast memory groups
- Group members
- Group road membership
- Supporting evidence

For a complete application backup, use the full SQLite export.

A visual screenshot of the network is not equivalent to a complete network backup.

---

## 12. Recommended Experiments

The purpose of FLIN is not simply to maximize the number of generated memory units.

A meaningful experiment should evaluate whether the network captures useful structural information.

### Experiment A — Single Document Learning

Create an empty network.

Import a mathematical document.

Measure:

1. Number of extracted mathematical concepts
2. Number of memory units created
3. Number of directed associations established
4. Number of SSRS fast roads formed
5. Number of fast memory groups generated
6. Supporting evidence for each group

Compare the resulting structure with manually identified concepts.

### Experiment B — Repeated Document Ingestion

Import the same document again.

Check whether previously processed source observations are handled consistently.

Duplicate ingestion should not artificially increase observation strength when the same source positions have already been recorded.

### Experiment C — Multi-Document Learning

Import multiple documents covering related mathematical topics.

Examples:

- Linear Algebra
- Spectral Theory
- Differential Equations
- Numerical Analysis

Observe whether different documents produce partially overlapping fast memory groups.

Check whether shared mathematical concepts remain represented by the same underlying memory units.

### Experiment D — Association and Fast Transmission

Select a memory unit and execute an associative pulse simulation.

Observe:

- Ordinary associative hops
- SSRS fast hops
- Activated memory units
- Traversed pathways

A fast road existing in the database does not mean every pulse must traverse it.

### Experiment E — Knowledge Structure Evaluation

Create a manually annotated reference network.

Compare it with the network produced by FLIN.

Suggested metrics:

**Precision**

How many extracted associations correspond to valid reference relationships?

**Recall**

How many important reference relationships were successfully recovered?

**Group Stability**

How consistent are the resulting groups under controlled repeated experiments?

**Source Consistency**

How accurately do group members and connections correspond to evidence in the original documents?

These measurements provide stronger evidence of learning performance than node counts alone.

---

## 13. Known Limitations

FLIN v23 remains an experimental research prototype.

### Mathematical Understanding

The current document learning process relies primarily on text extraction and rule-based mathematical concept identification.

It does not guarantee complete understanding of:

- Mathematical proofs
- Symbolic expressions
- Formula semantics
- Theorem dependencies
- Mathematical equivalence

### PDF Extraction

Text-based PDFs are supported.

Scanned image PDFs may require OCR.

Complex mathematical formatting can cause extraction errors.

Current document-processing limits include:

- Maximum file size: 35 MB
- Maximum PDF pages processed: 120
- Maximum extracted characters: 650,000
- Maximum text segments: 650

These limits are implementation constraints.

### Association Quality

Repeated co-occurrence does not necessarily imply a meaningful mathematical relationship.

FLIN records and reinforces observations according to its current associative learning rules.

Further research is required to establish whether its learned structures consistently represent mathematical knowledge.

### Visualization

The main 3D network uses performance-conscious sampling.

Not every memory unit or edge is necessarily visible simultaneously.

Display colors are identifiers, not confidence scores.

### Research Validation

The current implementation has been tested for core document learning, persistence, SSRS group construction, visualization, and related functions.

Large-scale academic literature collection still depends on external services, available research materials, and computing resources.

---

## 14. Research Roadmap

FLIN is part of the broader Brain_Project research initiative.

Its long-term direction is to investigate how structured experience and associative memory can support the development of intelligent systems.

Potential research directions include:

### Phase 1 — Persistent Associative Memory

Construct and maintain an experience-driven memory network.

### Phase 2 — Fast Memory Group Formation

Use repeated observations to establish source-grounded SSRS transmission pathways.

### Phase 3 — Knowledge Structure Evaluation

Determine whether fast memory groups reflect meaningful conceptual structures.

### Phase 4 — Cross-Document Association

Study how concepts learned from separate documents interact within a shared memory network.

### Phase 5 — Cross-Domain Knowledge Transfer

Investigate whether previously learned structures can support the formation of new conceptual relationships in unfamiliar domains.

### Phase 6 — Generalized Intelligent Behavior

Explore whether associative memory, structured experience, and adaptive routing can contribute to broader reasoning and learning capabilities.

These phases represent research objectives rather than demonstrated capabilities.

---

## 15. Project Philosophy

FLIN is based on the idea that intelligence may depend not only on how much information a system stores, but also on how previous experiences influence its future responses.

The project investigates whether repeated experiences can gradually shape a persistent associative network and create more efficient pathways for information transmission.

The central research question is:

**How can a system use its existing knowledge structures to construct, connect, and internalize previously unknown knowledge?**

Rather than treating intelligence as a collection of independent benchmark capabilities, FLIN explores the mechanisms through which memory structures may develop and reorganize through experience.

---

## 16. Project Status

**Current Version:** FLIN v23.0

**Project:** Brain_Project

**System:** Feature-Link Intelligence Network

**Primary Language:** Python

**Interface:** Desktop GUI with interactive 3D visualization

**Storage:** SQLite

**Primary Research Areas:**

- Associative Memory
- Brain-Inspired Artificial Intelligence
- Experience-Driven Learning
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
