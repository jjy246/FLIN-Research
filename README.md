# FLIN — Feature-Link Intellegence Network

Repository: **https://github.com/jjy246/FLIN-Research**

## What this release changes

This release is a **non-rewrite extension of the supplied `questioning(20261016-133501).py`**. Upload the downloadable `question.py` to your original repository to replace the previous main script. It retains the original literature discovery pipeline, SQLite networks, 3D desktop interface, FLIN pulse simulator, source citations, and ten-question author/reviewer workflow.

The **main FLIN workspace is presented in English**. Some inherited auxiliary dialogs, legacy diagnostics and original review prompts still contain Chinese text; this update intentionally leaves those original pathways largely intact to minimize regressions. Generated new question text is explicitly requested in English.

## Theory and implementation

The pipeline remains:

```text
Literature (Wikipedia / academic APIs)
    -> math-quality screening and source-grounded attention
    -> effective input cluster (original sentence and offsets)
    -> SSRS routing/order
    -> create or update triggerable feature memories
    -> learn directed, experience-driven links
    -> evaluate repeated association patterns
    -> optionally materialize a shortcut memory group
    -> weighted single-path pulse association
    -> math question generation / evidence review
```

### 1. First qualified experience creates a memory

A new, grounded mathematical feature with no verified equivalent in the existing network is immediately admitted as an **active, triggerable memory unit**. It does **not** wait for two or more independent sources. This preserves the project's first-input principle. Subsequent effective inputs strengthen learned associations. A new primitive is not suppressed merely because an unvalidated cost estimate claims that it can be reconstructed.

### 2. Source-grounded effective input and SSRS

The existing attention/feature filters extract literal mathematical terms from actual document sentences. `abc_extract_input_clusters()` preserves each source sentence, label, source URL and observed position. `abc_ingest_cluster()` applies the original quality and provenance checks and SSRS ordering. The original `abc_reconcile_pending()` forms directed, idempotent connections from these observed inputs.

**Important:** Source order is not mathematical implication, causality, or a theorem. A shortcut is a learned routing pattern, never a proof that its endpoints are logically equivalent.

### 3. Association-cost evaluation

Repeated SSRS input paths of **at least four** distinct, active feature memories can be considered for shortcuts. Each observed pattern has an ordered member list and evidence pointers. Documents are counted once per pattern. Default eligibility is **three independent document IDs**, positive estimated benefit greater than `0.5`, and no concurrent ties in the SSRS path.

For a path containing `n` memories supported by `s` distinct sources, the **experimental engineering cost proxy** is:

```text
expected_uses        = s * (1 + ln(1 + s))
original_path_cost   = expected_uses * (n - 1) * per_hop_cost
shortcut_total_cost  = expected_uses * 2 * per_hop_cost
                       + formation_cost + storage_cost + interference_cost
net_savings          = original_path_cost - shortcut_total_cost
```

Defaults in `question.py`:

| Parameter | Value |
|---|---:|
| Minimum member memories | 4 |
| Maximum member memories | 6 |
| Independent document threshold | 3 |
| Per-hop cost | 1.0 |
| Formation cost | 2.5 |
| Storage cost | 0.8 |
| Interference cost | 0.6 |
| Minimum net savings | 0.5 |

These constants are **heuristics, not experimentally fitted performance numbers**. In particular, `expected_uses` is a proxy inferred from observed source frequency, not a measured future query distribution. The decision is therefore reproducible, testable, and replaceable—not a claim of optimal human memory behavior.

### 4. Shortcut memory groups

If the cost test passes for observed `A -> B -> C -> D`, FLIN creates a **new triggerable shortcut memory** containing the ordered member IDs. It adds a pair of directed associations:

```text
A -> [shortcut(A,B,C,D)] -> D
```

The original route **A -> B -> C -> D** and its source evidence remain untouched. Each extra independent document can reinforce the shortcut. The shortcut's definition explicitly states that it represents an associative optimization, not a proved mathematical transformation.

Shortcuts are deliberately not recursively chunked in this prototype. More sophisticated nested composition and safe shortcut invalidation remain future research tasks.

## Run the existing application

Python **3.10+** on Ubuntu is supported by the original source. Install Tkinter through your operating system and Python packages in a virtual environment:

```bash
sudo apt install python3-tk
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 numpy networkx matplotlib scikit-learn pymupdf
python question.py
```

PyMuPDF is optional unless reading source PDFs. Some features invoke locally installed Ollama models; the core SQLite build and cost-reporting mechanism do not require Ollama.

### Start or continue your own network

In the GUI, use **Start Building (Literature → FLIN)**. The existing per-network SQLite database and research-source index continue to be used. Stop any previously running instance before launching an updated version against the same network.

The new FLIN section also provides:

- **Reevaluate Existing Input Costs (1,000 clusters)** — analyze source-grounded SSRS clusters already stored in the network, incrementally and without re-downloading papers.
- **Shortcut and Cost Report** — inspect shortcut units and experimental cost estimates.

The same functionality is available over SSH:

```bash
python question.py --flin-info
python question.py --flin-retrofit --flin-retrofit-limit 1000
python question.py --flin-efficiency-report
```

For a separate new database, you can also run:

```bash
python question.py --flin-create-network "My Mathematics Network"
```

### Offline regression tests

Place `test_question_flin.py` next to `question.py`, then run:

```bash
python test_question_flin.py
```

The tests use disposable SQLite databases, no Internet access, and no Ollama. They verify first-input activation, independent-source counting, positive-cost shortcut creation, exclusion of shorter paths, resumable retrofit, shortcut reinforcement, and original-graph nonmodification.

## Data and compatibility

The existing `abc_*` SQLite tables remain in place. New additive tables are `flin_patterns`, `flin_pattern_evidence`, `flin_shortcut_members` and `flin_cost_decisions`. The portable export format includes them. Existing `units`/`edges` legacy tables are not populated by this new FLIN learning path.

Before replacing an existing GitHub file or upgrading a database, make a normal backup of both your code and `~/.local/share/brain_project/` database files. The new database schema is additive; older program versions will not know how to use the new efficiency tables.

## Research limitations

- Actual live multi-source literature collection and local Ollama question-review performance must still be validated in the deployment environment.
- The current attention and SSRS implementations are engineering approximations of the research theory; they are not biological or mathematical proofs.
- Stronger association links reflect exposure-driven routing preference, **not** theorem correctness.
- A shortcut's existence demonstrates estimated savings **under the stated cost model**, not verified savings on real-world workloads. A next experiment should benchmark recall time and accuracy with shortcuts enabled and disabled.
- A lack of new memories or discovered papers cannot prove that all mathematics has been learned.
