# System architecture and dataflow

## Major components

The current source is intentionally shipped as **a single 12k+-line `flin_desktop.py` module** so the full original research implementation is preserved. This is a maintainability limitation, not an ideal target architecture. The following conceptual components are implemented within that file:

1. **Public-source discovery:** verified Wikipedia mathematics topics and categories; scholarly metadata requests to arXiv/Crossref and additional optional providers; transparent local catalog caching.
2. **Literature evidence extraction:** metadata, available abstracts, optional open-access PDF text; lexical mathematical concept/predicate quality gates; sentence-level provenance.
3. **Literature graph:** normal topic, paper, concept and claimed-relation nodes and edges; evidence and citation tables. A typed relation is a *source-backed candidate*, not an independently proven statement.
4. **FLIN learning:** input-cluster extraction with ordered feature positions; SSRS priority/reordering; source-event deduplication; one-shot memory activation after qualified evidence; directed link updates.
5. **FLIN simulation:** lexical gate lookup; serialized pulse trains; exactly one eligible weighted directed exit per step; no intrinsic amplitude decay; no immediate backtracking; event-frequency readout; gate-scoped feedback records.
6. **Question drafting:** independent local Ollama pipeline for ten draft questions followed by review, critique and revision; not part of FLIN routing.
7. **Desktop/CLI:** Tkinter settings, interactive 3D Matplotlib visualizations, network management, resumable jobs, query simulation, exports and diagnostics.

## Dataflow diagram

```text
Wikipedia categories / user research topics
            |
            v
 scholarly metadata (arXiv / Crossref / optional providers)
            |
            v
  verified title/abstract / optionally open-access PDF text
            |
            +----> LITERATURE/PROVENANCE GRAPH
            |      units / edges / papers / mentions / relation_evidence
            |
            v
 extract qualified, source-literal mathematical features + positions
            |
            v
      effective input clusters (abc_input_clusters)
            |
            v
   SSRS priority / observed group order
            |
            v
  accepted memories (abc_units / abc_evidence)
            |
            v
  directed learned associations (abc_edges / abc_cluster_links)
            |
  text query lexical lookup -> gate-specific pulse trains
            |
            v
  discrete weighted one-exit pulse propagation
            |
            +----> pulse arrivals / thresholded-frequency responses
            |
            +----> gate-labelled terminal feedback events
            |
            v
 optional question context -> local Ollama draft/review/revise
            |
            v
  human review + JSON / TXT export
```

## Storage and dataset provenance

| Table family | Purpose | Example caveat |
| --- | --- | --- |
| `theories`, `papers`, `paper_theories` | Retrieved titles, metadata and topic membership | Relevance is heuristic |
| `wikipedia_references`, `relation_evidence` | Original bibliographic footnotes and relation source sentences | Quotation is not proof |
| `units`, `edges`, `unit_terms`, `positions` | General directed **literature** graph | Not associative pulse links |
| `abc_sources`, `abc_input_clusters`, `abc_cluster_features` | Effective input events and ordered features | Lexical extraction can be incomplete |
| `abc_units`, `abc_evidence`, `abc_ssrs` | Active FLIN memories, source backing and SSRS statistics | Memory labels are not semantic embeddings |
| `abc_edges`, `abc_cluster_links` | Learned directed routing weights, per-cluster deduplication | Weight does not imply causal strength |
| `abc_runs`, `abc_pulse_events`, `abc_feedback` | Pulse simulation configuration, arrivals and terminal events | Events are simulated, not brain recordings |
| `question_sets`, `question_candidates`, `question_feedback` | Optional versioned Ollama drafts and reviews | Model opinions are not theorem validation |

### Data-compatibility requirements

Keep **SQLite field names, historical `abc_` schema prefixes and stable stored IDs** even when improving external documentation or UI labels. Rename code display text separately; changing column names or stored status strings without migrations can corrupt compatibility. Network registry references are stored outside each SQLite database. Export full SQLite snapshots before any major migration.

## Concurrency, performance and limitations

- API fetching and extraction can be parallel; SQLite writes are serialized to reduce lock contention.
- Wikipedia category exploration is depth/budget-limited; remote API quotas and content rights are respected.
- Graph visualization uses **bounded samples** (configurable via `BRAIN_OVERVIEW_NODES`) instead of trying to render millions of nodes simultaneously.
- The core is CPU/SQLite driven. A dedicated GPU is useful mainly for *optional local Ollama inference*, not required for the FLIN pulse simulation.
- Linux can optionally set CPU affinity; Windows/macOS use worker limits without this Linux-specific API.
- Portable archive export streams JSONL.gz without loading the entire graph into memory. A full SQLite snapshot includes more internal state than the portable subset.

## Future refactor boundaries

Without altering algorithms, split into `storage/`, `sources/`, `learning/`, `simulation/`, `questioning/`, and `ui/` packages with dedicated data-access boundaries and tests. Use transactions and schema migrations to preserve existing users' data. This refactor is a **roadmap item**, not claimed as shipped.
