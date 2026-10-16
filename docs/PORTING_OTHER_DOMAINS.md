# Porting FLIN to other knowledge domains (for fork authors)

**This is a design and code-navigation guide — not a claim of existing functionality.**
The official executable program has a **mathematics-specific collection and
validation policy**. For other domains, **fork and modify your own copy**. No
underlying FLIN Python code is changed by this guide.

## 1. Start by understanding the stable core

Read [FLIN Theory](FLIN_THEORY.md) and [Architecture](ARCHITECTURE.md).
You should distinguish **source-derived input features** from **directed
activation preferences**. Learn the existing behavior using the offline
synthetic demo, unit tests and a fresh mathematics SQLite network.

## 2. Decide what "knowledge" will mean in your fork

Write a short domain specification *before coding*:

- What is a legitimate source (e.g., peer-reviewed papers, archival documents,
  textbooks, sensor measurements), and what rights allow processing/sharing it?
- What counts as one **effective input cluster**? A sentence, observation,
  event, experiment, or structured record?
- What are your memory-unit types and canonicalization rules? Which expressions
  are invalid or ambiguous?
- How can a user audit a unit back to a real source and input event?
- What claims may be encoded as source-supported **candidates** rather than
  established truths? Are links factual, causal or merely associative?
- How will the fork test false positives, duplicates, bias and contradictions?

## 3. Where the mathematics restriction actually lives

In `flin_desktop.py`, inspect these **existing** definitions (names may move in
future revisions):

| Current section/function | Why a non-math fork must review it |
| --- | --- |
| `active_domain`, `set_network_domain`, `create_empty_network` | The official program returns/enforces `mathematics`; merely choosing a profile label is insufficient. |
| `MATH_ENTRY_TOPICS`, `MATH_CATEGORIES`, `mathematics_discovery_seeds`, `discover_theories` | Discovery seeds and Wikipedia category traversal are curated for mathematics. |
| `math_topic_quality`, `paper_math_quality`, `score_candidate` | Topic and paper admission assumptions are math-specific. |
| `MATH_ANCHORS`, `MATH_TOPIC_RESEARCH`, `keyphrases`, `math_concept_quality`, `score_math_unit_purity` | Concept recognition and acceptance restrict what becomes a memory unit. |
| `source_math_relations`, `math_terms_in_sentence`, `add_math_relation_memories` | Typed relation candidates rely on math vocabulary and explicit predicates. |
| `abc_extract_input_clusters`, `abc_schema` and FLIN training functions | Input clustering and persistence must agree with the domain's observation format. |
| Ollama prompting and review roles | The optional question-generation pipeline is designed for mathematical questions. |
| CLI help, GUI labels and `DOMAIN_PROFILES` | Domain labels/profiles alone must not be mistaken for full backend support. |

Some general-purpose helper functions exist in the source, but the **official
workflow does not expose a validated general-domain mode**. A fork must verify
that every upstream and downstream stage uses its intended definitions.

## 4. Fork without damaging existing research data

1. On GitHub click **Fork → Create fork**.
2. Clone your fork, make a branch, and preserve the original as a baseline.
3. Use a **new network/database** for experiments. Do not reclassify a previous
   math-only dataset as a new subject without explicit data migration.
4. Modify **your fork's** discovery, quality-gating, concept normalization,
   extraction and (if needed) model prompting for the new domain.
5. Keep provenance for every learning event; do not transform pulse associations
   into factual claims or logical implications without independent checking.
6. Decide how to encode incompatible concepts. Include tests for ambiguous
   vocabulary, invalid sources, cross-document co-occurrence and noisy input.
7. Test fresh collection, SQLite persistence, network export/import, directed
   pulses, thresholds, and the native GUI. Keep migration/version notes.
8. Document which parts of the original FLIN theory remain intact, which are
   changed, and what observations might falsify the new assumptions.
9. Publish your fork with attribution, an appropriate license, test results,
   a clear limitation statement, and a sample **lawfully redistributable** data
   snapshot when available.

## 5. Community interoperability

Publishing a SQLite file does **not** automatically make it compatible with the
official mathematics reference application. The official [network review](COMMUNITY_NETWORKS.md)
requires an importable, enabled FLIN graph with real active units and usable
directed edges, in a schema the official app can read. For incompatible forks:

- Publish the snapshot in **your own GitHub Releases** with your fork/version;
- Provide a schema migration description and separate importer when needed;
- Open a feature Issue or PR proposing a compatible interchange format rather
  than asking a maintainer to publish an unreadable SQLite in official Releases.

**The purpose of an open-source FLIN is to enable experiments, not to declare
all forks scientifically equivalent or to compromise the integrity of shared
datasets.**
