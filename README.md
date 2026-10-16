# FLIN — Feature-Link Intellegence Network

**Repository:** https://github.com/jjy246/FLIN-Research

FLIN is an experimental, source-grounded associative memory system for mathematical knowledge.

It collects mathematical research materials, extracts identifiable mathematical features, converts qualified observations into persistent memory units, and establishes directed associations based on effective input experiences.

The resulting memory network supports:

- Automated mathematical knowledge acquisition
- Attention-based feature extraction
- SSRS-based input routing
- Persistent associative memory formation
- Efficiency-aware shortcut memory formation
- Weighted, single-path pulse propagation
- Interactive 3D network visualization
- Association-assisted mathematical question generation

FLIN is a research prototype. Its memory formation rules, cost model, and pulse propagation mechanism are computational hypotheses rather than established models of biological memory.

---

## 1. System Architecture

The system follows an experience-driven learning architecture.

```text
Mathematical Literature
         |
         v
Source and Mathematical Quality Screening
         |
         v
Attention Mechanism
         |
         v
Effective Input Clusters
         |
         v
SSRS
(Sensory Shaping and Routing System)
         |
         v
Memory Formation
         |
         v
Directed Association Learning
         |
         v
Association Cost Evaluation
         |
         +------ Reuse Existing Memory Units
         |
         +------ Create Shortcut Memory Groups
         |
         v
Persistent FLIN Network
         |
         +------ 3D Network Visualization
         |
         +------ Associative Pulse Simulation
         |
         +------ Mathematical Question Generation
```

The associative memory system does not depend on semantic embeddings or language models for concept equivalence.

Mathematical features are identified through source-grounded textual evidence and explicit extraction rules.

Language models are used separately for optional mathematical question generation and review.

---

## 2. Attention and Effective Input Clusters

FLIN processes research documents before admitting their contents into memory.

The attention mechanism extracts mathematical features from source material.

Features must satisfy mathematical relevance and source-grounding requirements.

An effective input cluster contains:

- Source document identity
- Original text evidence
- Extracted mathematical features
- Feature positions within the source
- Source URL
- Associated quality information

An effective input cluster can be represented as:

\[
X_i = \{f_1,f_2,\ldots,f_n\}
\]

where each \(f_i\) is a feature extracted from a qualified input.

The features are processed together rather than treated as unrelated observations.

The original source evidence is retained for inspection and subsequent processing.

### Source-Grounded Learning

The extraction mechanism requires features to originate from actual source material.

It does not construct mathematical relationships solely because two terms appear near each other.

A detected association represents an observed input relationship, not necessarily a mathematically valid implication.

---

## 3. Sensory Shaping and Routing System (SSRS)

SSRS determines how effective input features are routed into the associative memory network.

Its purpose is to organize accepted features before association learning.

Routing is influenced by:

1. Observed input position
2. Previously learned routing priorities
3. Existing feature memory identities
4. Input concurrency

The system preserves the distinction between ordered and simultaneous inputs.

Features observed simultaneously are not automatically converted into an arbitrary sequential relationship.

A simplified representation is:

\[
R(X_i,M_t)\rightarrow G_i
\]

where:

- \(X_i\) is an effective input cluster.
- \(M_t\) is the current memory state.
- \(R\) represents SSRS processing.
- \(G_i\) is the resulting ordered collection of input groups.

The routing process is independent of associative pulse propagation.

SSRS determines how external experiences enter the memory system.

The associative network subsequently determines how previously formed memories are activated.

---

## 4. Memory Unit Formation

FLIN distinguishes between primitive feature memories and reusable composite structures.

### 4.1 Primitive Memory Units

A primitive memory unit represents an identifiable mathematical feature.

Examples include:

- Partial derivative
- Linear operator
- Eigenvalue
- Boundary condition
- Fourier transform
- Stochastic process

A new feature can become an active memory unit after its first qualified effective input.

Independent confirmation from multiple documents is not required for initial activation.

Additional effective inputs provide evidence and reinforce existing associations.

This implements the principle:

> A qualified new experience can immediately produce a triggerable memory.

The current system does not reject an otherwise qualified new primitive feature solely because an estimated reconstruction cost is low.

This prevents the experimental cost model from suppressing potentially novel mathematical information.

### 4.2 Composite Memory Structures

A complex mathematical concept may be represented through multiple existing memory units.

For example:

```text
Differential Operator
        |
Boundary Condition
        |
Eigenvalue Problem
        |
Orthogonality
```

Such a structure can be reconstructed through existing associations.

However, repeatedly reconstructing a long association sequence may require unnecessary processing.

FLIN therefore evaluates whether a reusable shortcut memory group could reduce the estimated cost of future associations.

---

## 5. Efficiency-Aware Memory Formation

A central research hypothesis of FLIN is that memory organization should account for processing efficiency.

The objective is not simply to minimize the number of memory units.

Instead, the system investigates whether additional composite structures can reduce the cost of future associative processing.

### 5.1 Reconstruction Versus Shortcut Retrieval

Consider an existing association route:

```text
A -> B -> C -> D
```

The original route requires three directed transitions.

A shortcut memory group can provide an alternative route:

```text
A -> [Shortcut: A,B,C,D] -> D
```

This requires two directed transitions.

The original memories and associations remain available.

The shortcut provides an additional routing option rather than replacing the original knowledge structure.

### 5.2 Association Cost Function

Let:

- \(n\): Number of memory units in the original path
- \(s\): Number of independent supporting documents
- \(h\): Estimated cost per association transition
- \(F\): Shortcut formation cost
- \(S\): Shortcut storage cost
- \(I\): Estimated associative interference cost

The current implementation uses:

\[
U(s)=s(1+\ln(1+s))
\]

as an experimental estimate of future reuse opportunity.

The estimated cost of reconstructing the original path is:

\[
C_{\text{original}}=U(s)(n-1)h
\]

The estimated cost of using a shortcut is:

\[
C_{\text{shortcut}}=2U(s)h+F+S+I
\]

The estimated net benefit is:

\[
\boxed{
\Delta C=C_{\text{original}}-C_{\text{shortcut}}
}
\]

A positive value suggests that shortcut formation may reduce total processing cost under the assumed model.

### 5.3 Default Parameters

| Parameter | Default |
|---|---:|
| Minimum path length | 4 memory units |
| Maximum path length | 6 memory units |
| Independent document threshold | 3 |
| Cost per association transition | 1.0 |
| Shortcut formation cost | 2.5 |
| Shortcut storage cost | 0.8 |
| Associative interference cost | 0.6 |
| Minimum net benefit | 0.5 |

A shortcut is formed when the sequence satisfies the structural requirements, has sufficient independent evidence, and:

\[
\boxed{\Delta C>0.5}
\]

These values are engineering assumptions.

They have not been fitted to experimental measurements of actual retrieval latency, CPU consumption, or biological memory processes.

Future work should replace these estimates with measurements obtained from real FLIN workloads.

---

## 6. Shortcut Memory Groups

Shortcut memory groups are constructed from repeated SSRS-observed association patterns.

The current implementation requires:

1. A sequence of 4–6 active memory units.
2. Distinct memory units within the selected sequence.
3. A valid order obtained from SSRS processing.
4. Evidence from at least three distinct source documents.
5. Estimated net savings above the formation threshold.

Simultaneous feature groups are not converted into artificial ordered sequences.

Existing shortcut memories are excluded from shortcut candidates to avoid uncontrolled recursive composition.

### Formation Procedure

```text
Observed SSRS Sequence
          |
          v
Identify Repeated Pattern
          |
          v
Count Independent Sources
          |
          v
Estimate Reconstruction Cost
          |
          v
Estimate Shortcut Cost
          |
          v
Calculate Net Benefit
          |
      +---+---+
      |       |
   Positive  Insufficient
   Benefit   Benefit
      |       |
      v       v
   Create    Reuse
   Shortcut  Existing Path
      |
      v
Preserve Original Route
      |
      v
Store Shortcut and Evidence
```

Each shortcut stores:

- A unique memory identifier
- Ordered member memory identifiers
- Supporting source references
- Associated source excerpts
- Estimated cost information
- Directed shortcut connections

New independent evidence can reinforce an existing shortcut.

The original memory units and directed associations are not deleted.

A shortcut represents an association optimization.

It does not establish mathematical equivalence, causality, or logical implication between its endpoints.

---

## 7. Directed Associative Network

FLIN represents learned associations using a directed weighted graph:

\[
M=(V,E,W)
\]

where:

- \(V\) is the set of memory units.
- \(E\) is the set of directed associations.
- \(W\) contains learned association strengths.

Each directed connection has an associated weight.

The weight influences the probability that the connection will be selected during associative pulse propagation.

Connections are updated through qualified effective input experiences.

Associative pulses do not independently strengthen connections simply because they pass through them.

### Association Routing

For an activated memory unit \(v_i\), eligible outgoing connections are sampled according to their learned weights.

Conceptually:

\[
P(v_j\mid v_i)=
\frac{w_{ij}}
{\sum_{k\in N^+(v_i)}w_{ik}}
\]

where the denominator covers eligible outgoing connections.

Each pulse selects one outgoing connection.

Stronger connections are more likely to be selected, but weaker connections remain accessible when eligible.

The simulation also enforces limits on immediate backtracking and repeated visits.

This allows different association routes to emerge from the same initial input.

---

## 8. Continuous Pulse Simulation

The associative mechanism uses a configurable external pulse source.

A pulse travels through the directed memory network according to learned connection strengths.

The simulation includes:

- Pulse supply frequency
- Input duration
- Directed propagation
- Weighted route selection
- Revisit restrictions
- Reaction-frequency measurement
- Sliding observation windows
- Reaction thresholds

The response of a memory unit is estimated from the frequency of pulse arrivals during a specified observation window.

For a window of duration \(\tau\):

\[
f_i(t)=
\frac{N_i(t-\tau,t]}{\tau}
\]

where \(N_i(t-\tau,t]\) is the number of pulse arrivals at memory unit \(i\) within that window.

A unit's response can be displayed when its frequency exceeds the configured threshold.

This is a computational signal-propagation model, not a physical simulation of biological neurons.

Shortcut memories participate in the same weighted propagation mechanism as other memory units.

Their existence does not guarantee that the pulse will select the shortcut route.

---

## 9. Mathematical Knowledge Acquisition

FLIN supports automated exploration of mathematical topics and related academic literature.

### Supported Sources

| Source | Application |
|---|---|
| Wikipedia / MediaWiki | Mathematical topic discovery and references |
| arXiv | Research preprints |
| Crossref | Publication metadata and DOI lookup |
| OpenAIRE | Academic research discovery |
| DBLP | Computing and mathematical computing literature |
| Europe PMC | Biomedical and interdisciplinary research |
| OpenAlex | Optional academic literature indexing |
| Semantic Scholar | Optional academic paper discovery |
| Local SQLite catalog | Previously indexed literature metadata |

Some providers require API configuration.

Availability and rate limits depend on the source.

The system may process titles, abstracts, or available text excerpts depending on the retrieved material.

A bibliographic record is not equivalent to reading or understanding the complete paper.

### Continuous Discovery

The collection system maintains persistent discovery progress.

Previously processed topics and source records can be reused.

When the current exploration queue becomes empty, continuous discovery mode can periodically check for additional work.

Temporary inactivity does not imply that all available mathematical knowledge has been explored.

---

## 10. Installation

### Windows

Requirements:

- Python 3.10 or newer
- Python Tkinter support
- Internet access for online literature retrieval

Clone or download the repository:

https://github.com/jjy246/FLIN-Research

Run:

```text
start_windows.bat
```

The Windows launcher should start:

```text
flin_desktop.py
```

This file serves as the complete application entry point.

For manual execution:

```powershell
py -m pip install -r requirements.txt
py flin_desktop.py
```

### Ubuntu / Linux

Install system dependencies:

```bash
sudo apt update
sudo apt install python3-tk python3-venv
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Start FLIN:

```bash
python flin_desktop.py
```

Primary dependencies include:

- NumPy
- NetworkX
- Matplotlib
- Requests
- Beautiful Soup
- Scikit-learn

PyMuPDF is optional unless PDF text extraction is enabled.

A graphical desktop session is required for the Tkinter interface.

Some command-line operations can run without a graphical session.

---

## 11. Building a Memory Network

FLIN allows users to create independent mathematical memory networks.

### Step 1 — Create a Network

In the desktop interface, select:

**New Empty FLIN Network (no data copied)**

The system creates an independent persistent network.

Existing networks are not overwritten.

### Step 2 — Configure Literature Collection

Select the desired:

- Research discovery settings
- Paper collection limits
- Available academic sources
- Worker count
- PDF extraction settings
- Continuous discovery mode

### Step 3 — Start Learning

Select:

**Start Building (Literature → FLIN)**

The application begins retrieving research material and processing qualified effective inputs.

New mathematical features are converted into active memory units.

Existing memory units and directed connections are updated through additional observations.

Repeated association patterns are evaluated for shortcut formation.

### Step 4 — Inspect the Network

The desktop application provides interactive 3D visualization.

Memory units and their associations can be inspected through the network interface.

The displayed network may contain fewer nodes and edges than the complete database because visualization is resource-limited.

### Step 5 — Test Association

Use:

**Run Pulse Simulation / Response Distribution**

Input a known mathematical concept and configure the pulse parameters.

The simulator produces a distribution of activated memory units based on weighted propagation.

### Step 6 — Inspect Shortcut Decisions

Use:

**Shortcut and Cost Report**

The report provides information about formed shortcuts and estimated association costs.

Existing stored input clusters can also be evaluated through:

**Reevaluate Existing Input Costs (1,000 clusters)**

This operation allows older SSRS input records to be examined without rebuilding the original memory network.

---

## 12. Command-Line Interface

The application supports command-line operations for network inspection and maintenance.

Create an independent network:

```bash
python flin_desktop.py --flin-create-network "My Mathematics Network"
```

Inspect the active network:

```bash
python flin_desktop.py --flin-info
```

Inspect literature coverage and collection status:

```bash
python flin_desktop.py --flin-source-report
```

Inspect discovery progress:

```bash
python flin_desktop.py --flin-discovery-info
```

Evaluate previously stored effective input clusters:

```bash
python flin_desktop.py --flin-retrofit --flin-retrofit-limit 1000
```

View shortcut formation and cost statistics:

```bash
python flin_desktop.py --flin-efficiency-report
```

Run associative pulse simulation:

```bash
python flin_desktop.py --flin-simulate "partial differential equation"
```

On Windows, use `py` instead of `python` if required by the local Python installation.

---

## 13. Data Persistence

FLIN uses SQLite for persistent memory storage.

The application stores network data separately from the source retrieval process.

Memory units, directed links, evidence records, source information, and association histories can be retained across application restarts.

The existing implementation uses historical `abc_*` table names for the FLIN associative graph.

### Primary Tables

| Table | Description |
|---|---|
| `abc_units` | Associative memory units |
| `abc_edges` | Directed weighted associations |
| `abc_ssrs` | Learned SSRS routing information |
| `abc_evidence` | Source evidence associated with memories |
| `abc_input_clusters` | Effective input clusters |
| `abc_cluster_features` | Features and their observed positions |
| `flin_patterns` | Observed association patterns and cost estimates |
| `flin_pattern_evidence` | Independent source evidence for patterns |
| `flin_shortcut_members` | Ordered members of shortcut memories |
| `flin_cost_decisions` | Recorded memory formation and reuse decisions |

The shortcut mechanism extends the existing schema without deleting the original FLIN units or connections.

For compatibility, some earlier database structures remain present even though the active associative graph is stored in separate tables.

Users should back up their SQLite databases before major updates.

---

## 14. Mathematical Question Generation

FLIN includes an association-assisted mathematical question generation workflow.

The process begins with an existing mathematical memory.

An associative pulse simulation activates related memories according to the learned network.

The resulting response distribution and available source evidence provide context for question generation.

A local language model can then be used for:

- Drafting mathematical research questions
- Reviewing generated questions
- Identifying limitations
- Revising candidate questions

The current implementation supports local Ollama-based workflows.

Language models are not responsible for constructing the underlying FLIN memory associations.

Generated questions and mathematical claims still require independent verification.

---

## 15. Research Objective: Memory Network Sufficiency

An ongoing research question is determining when an associative memory network contains a sufficiently reusable collection of mathematical representations.

A growing network may eventually represent many newly encountered theories through combinations of existing memory units.

However, representational capability alone does not imply computational efficiency.

Even when a mathematical structure can be reconstructed from elementary concepts, doing so repeatedly may be expensive.

FLIN therefore investigates the relationship between:

1. Memory representation capacity
2. Association reconstruction cost
3. Shortcut formation cost
4. Storage overhead
5. Interference between associations
6. Future reuse frequency

The working hypothesis is that a network can benefit from additional composite memories even when no new primitive features are required.

A possible long-term objective is to minimize expected processing cost while maintaining adequate knowledge representation and retrieval accuracy.

Formally:

\[
M^*=
\arg\min_M
\left[
C_{\text{learning}}(M)
+
\mathbb{E}_{T\sim P(T)}
C_{\text{processing}}(T\mid M)
+
\lambda C_{\text{storage}}(M)
+
\mu C_{\text{interference}}(M)
\right]
\]

This expression describes a proposed research objective.

It is not the optimization algorithm currently implemented in FLIN.

The current implementation uses the simpler association-hop cost estimator described in Section 5.

### Network Sufficiency

A lack of newly created memory units does not establish knowledge completeness.

Potential evaluation methods include:

- Testing reconstruction of held-out mathematical concepts
- Measuring association costs on unfamiliar problems
- Comparing performance with and without shortcut memories
- Evaluating coverage across mathematical disciplines
- Measuring whether new memories improve downstream task performance

A network may be considered sufficient for a specified evaluation domain when it satisfies predefined representation, accuracy, and efficiency requirements.

This would not establish completeness over all existing or future mathematical knowledge.

---

## 16. Limitations and Future Work

The current implementation has several limitations.

**Feature extraction**

The system uses explicit mathematical and lexical extraction rules. It may fail to recognize novel mathematical notation or concepts outside the implemented extraction patterns.

**Mathematical validity**

Source-grounded associations are not independently verified mathematical proofs.

**Cost estimation**

Shortcut formation relies on heuristic estimates rather than measured long-term workload costs.

**Source coverage**

Academic provider availability, access restrictions, and partial document extraction limit the completeness of the collected information.

**Shortcut representation**

The present implementation does not recursively construct shortcuts from existing shortcuts.

**Memory consolidation**

Automatic shortcut removal, reorganization, and invalidation based on contradictory evidence remain open research tasks.

**Experimental validation**

The effect of shortcut memories on actual retrieval efficiency and mathematical problem-solving performance requires controlled evaluation.

Future development should focus on replacing heuristic cost parameters with empirical measurements and testing whether the resulting memory structures improve associative processing.

---

## 17. Project Status

The current implementation provides:

- Persistent feature-level memory formation
- Source-grounded effective input clusters
- SSRS-based association learning
- Directed weighted memory connections
- Experimental shortcut memory formation
- Cost-decision recording
- Associative pulse simulation
- Interactive network inspection
- Mathematical literature acquisition
- Association-assisted question generation

The implementation is intended as an experimental platform for studying associative memory organization and efficiency-aware knowledge representation.

It should not be interpreted as a complete mathematical reasoning system or a validated model of human cognition.

---

## Repository

**FLIN — Feature-Link Intellegence Network**

https://github.com/jjy246/FLIN-Research
