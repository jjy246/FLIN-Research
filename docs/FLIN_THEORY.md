# FLIN Theory: a precise guide to the current experimental model

## 1. Goal and epistemic status

**FLIN** means **Feature-Link Intelligence Network**. Its long-term research question is whether a system can build new conceptual structure by combining existing experience-defined frames and learned pathways, rather than relying exclusively on opaque vector similarity. This is an architectural hypothesis, **not a demonstrated theory of human cognition**.

The executable prototype currently restricts automatic collection to mathematical material. It stores source-attested feature/concept units, strengthens **directed activation preferences** based on observed qualified inputs, and simulates pulses. It cannot independently establish that a mathematical relation is true, novel, or generalizable. Evidence checks and independent theorem/proof verification remain necessary.

The terminology below distinguishes (a) **design intent**, (b) **implemented algorithm**, and (c) **unresolved research questions**. Do not promote a code convention to a neurological fact.

## 2. Memory units and effective input clusters

A **memory unit** is a reusable feature/concept representation with an identifier, label, supporting explanation, source information, quality heuristic, and activation state. Its identity is based on a normalized literal label, not a learned embedding; synonym identity therefore remains an open problem.

An **effective input cluster** is a group of features extracted from an *individual, traceable input statement*. The application segments source text into sentences, identifies mathematical expressions appearing literally within those sentences, screens candidates and records their positions. The cluster carries the original statement and source provenance. It is **not** a bag of keywords pooled across unrelated documents.

In this prototype, a **first qualified, source-grounded experience** can create an immediately triggerable memory unit. Independent additional sources improve provenance/evidence counts; they are **not required** to open an arbitrary activation gate. The acceptance threshold is a **heuristic lexical-quality threshold**, not a truth score. The code intentionally preserves uncertain or rejected claims outside the set of accepted active memories.

## 3. Two network types: do not confuse them

| Graph | Main storage | Meaning |
| --- | --- | --- |
| Literature/evidence graph | `units`, `edges`, `papers`, `relation_evidence`, … | Navigation through topics, papers, quoted candidate relations and citations |
| FLIN associative graph | `abc_units`, `abc_edges`, `abc_input_clusters`, `abc_evidence`, … | Memory-unit activation and **learned directed routing preferences** |

An evidence-graph edge may encode a claim with its original sentence. A FLIN `abc_edges` row means an input-driven preference for routing activation from one memory unit to another. Neither alone is sufficient to assert a theorem, causation, entailment, or conceptual equivalence.

## 4. SSRS: attention and routing as a separate stage

The **Sensory Shaping and Routing System (SSRS)** is the conceptual intermediate stage between accepted input features and activation of memory units. In the present text-only approximation:

1. A source sentence passes an effective-input/quality screen.
2. Features are identified, with **observed positions** retained.
3. Stored SSRS priority/experience statistics affect ordering slightly.
4. Qualified features activate memory units and can contribute to learned directed links.

The system does **not** implement complete multisensory integration, biological attention, camera inputs, or a physically modeled syncytium. The SSRS name is a research abstraction; the available implementation is a deterministic ordering/priority mechanism in Python and SQLite.

The effective order is modeled approximately as

\[
\tilde t_i = p_i - 0.1\,s_i,
\]

where \(p_i\) is the observed source position and \(s_i\) is the stored priority for unit \(i\). This is an **engineering rule**, not measured brain timing. When features share exactly the same effective position, the implementation treats them as a concurrent group rather than inventing an orientation between them.

## 5. Learning directed links

If a qualified input cluster contains successive active feature groups \(G_1,G_2,\dots\), the implementation can reinforce directed transitions from members of \(G_k\) to members of \(G_{k+1}\):

\[
 u \longrightarrow v, \quad u\in G_k,\;v\in G_{k+1}.
\]

These links represent **observed input order after SSRS processing**, not an assertion that \(u\) logically implies \(v\).

For a supported link with old weight \(w\), a qualifying new observation updates

\[
 w_{\mathrm{new}} = w + \eta\,(w_{\max}-w),
\]

with the implementation default \(\eta=0.22\), \(w_{\max}=10\), and an initial weight of 1 before the first reinforcement. A unique cluster-link record prevents counting the **same input event** twice. Independent repeated experiences can increase strength; FLIN pulse simulation itself does **not** strengthen learned connections. This deliberately separates real external input from internally generated associations.

## 6. Pulse propagation: one pulse, one directed exit

During a simulation, a gate linked to an input concept emits a train of pulses at configurable rate \(f_{\mathrm{in}}\) over input duration \(T_{\mathrm{in}}\). Pulses enter active memory units; **exactly one** eligible outgoing directed edge is chosen at each step.

For unit \(i\), eligible exits \(E_i\), and positive learned weights \(w_{ij}\), the *implemented* routing rule is

\[
\Pr(i\rightarrow j \mid j\in E_i)=\frac{w_{ij}}{\sum_{k\in E_i}w_{ik}}.
\]

This is **weighted exit selection**, not a second probabilistic "transmission success" test. The weights approximate preferences/low impedance; no literal electrical impedance measurements are used. The normalization formula was an unresolved design choice in the early theory notes, and remains an **implementation hypothesis**, not an experimentally proven biological rule.

A pulse:

- follows a **directed** edge (a separate reverse edge could exist, but is not automatically assumed);
- never immediately traverses back to the unit it just came from;
- may pass through longer cycles, subject to a configurable per-unit **revisit cap**;
- does **not** lose intrinsic strength as it travels;
- stops when no eligible exit remains or the **maximum-step safeguard** is reached.

The simulation uses discrete event timestamps and a configured per-edge transit interval; it does **not** numerically solve a continuous neural-circuit differential equation. Stopping at an endpoint or safety cap is distinct from attenuation.

## 7. Flash/reaction: frequency, not accumulated amplitude

Every pulse arrival generates an event at a memory unit. Let \(\mathcal{T}_i\) be its arrival times and \(\Delta\) the sliding observation window. The raw event-frequency estimate is

\[
 r_i(t)=\frac{\#\{\tau\in\mathcal{T}_i:\ t-\Delta < \tau\le t\}}{\Delta}.
\]

An observation threshold \(\theta\) suppresses low-frequency reactions:

\[
 v_i(t)=r_i(t)\,\mathbf{1}[r_i(t)\ge\theta].
\]

Time-averaged visible reaction over the completed simulation is \(\bar v_i=\frac{1}{T}\int_0^T v_i(t)\,dt\). The displayed response distribution is normalized by \(P_i=\bar v_i/\sum_k \bar v_k\), when the denominator is positive. If no unit crosses the threshold, the visible distribution may be empty.

**Interpretation:** The visible reaction is a thresholded *frequency* of arrivals, not a stored potential. More strongly connected regions may dominate observations because they receive more pulses; the code does not overwrite weaker memories or prove that those concepts are irrelevant. Numerical integration is computed directly from event intervals so narrow flashes are not lost solely because a plot has few points.

## 8. Gate-specific feedback

Each input seed has a **gate label**. When a pulse ends, the simulator stores its gate, terminal memory unit, reason and time in a feedback event. This preserves the distinction between paths arising from different inputs even when they visit a shared node.

The **design intent** is an independent gate-indexed feedback network or tree. The current code records source-specific feedback events; it does **not** implement a complete, separately trained feedback-tree circuit with learned gate-specific control dynamics. The feedback events should therefore be interpreted as **instrumentation and research scaffolding**.

## 9. What FLIN is — and is not — learning

FLIN learns *which source-attested memory unit transitions have been jointly encountered in ordered inputs*. It does not yet prove that it understands the underlying theory, automatically transfers mathematical abstractions across disciplines, or constructs valid unseen theorems. Unlike semantic-vector/RAG retrieval, the pulse simulator never calls an LLM or cosine embedding; its inputs are already-admitted units and learned links. The **separate** question generator uses Ollama to author and critique natural-language problems from retrieved memory/source context.

A high-weight edge, frequent reaction, or model-assigned review score must not be presented as mathematical truth.

## 10. Explicit unresolved questions

- How should equivalence/synonym detection work without collapsing distinct mathematical objects?
- Is source order a sufficient proxy for a meaningful experienced association? How can false associations be measured?
- What attention/SSRS representation handles multimodal physical input as a single selected cluster?
- Should weights affect only selection, or some deeper circuit law? What observations would discriminate alternatives?
- How should longer feedback loops and independently learned gate-specific response trees work?
- How should the model measure transfer across domains, durable learning, robust novelty and genuinely valid new deductions?
- What experiments distinguish this system from ordinary co-occurrence, lexical search, graph walks and retrieval-augmented generation baselines?

**Do not call these solved features.** See [Roadmap](ROADMAP.md) for measurable evaluation proposals.
