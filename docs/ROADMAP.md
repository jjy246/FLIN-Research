# Research roadmap and experimental validation

These are **proposals for research**, not completed capabilities.

| Research question | Current status | Minimal falsifiable experiment |
| --- | --- | --- |
| Create source-grounded mathematical feature memories | Implemented prototype with lexical gates | Hand-annotate random article sentences and measure precision/recall of memory extraction |
| Learn directed link preferences from external input | Implemented prototype | Run repeated independent input-cluster ingestion and measure weight updates/deduplication |
| One-exit weighted pulse routing | Implemented discrete simulation | Monte Carlo output frequencies vs. exact normalized edge weights |
| Thresholded per-memory response-frequency readout | Implemented discrete-event integration | Exact-event sanity tests and threshold/window sensitivity sweeps |
| Independent gate-specific learned feedback trees | **Not implemented**, only gate-labelled feedback events exist | Prototype feedback graph in separate tables, evaluate gate cross-talk |
| Full multisensory SSRS (vision/touch/audio unified event) | **Not implemented** | Build timestamped paired sensor-cluster data; compare against independent sensory pipelines |
| Vision/image input as native memory experience | **Not implemented** | Design deterministic source-verifiable visual feature extraction and multimodal input schema |
| General language understanding without embeddings/LLMs | **Not demonstrated** | Text-input benchmarks beyond existing lexical label matching |
| Discover valid new mathematical theories/proofs | **Not demonstrated** | Blinded theorem checker + independent novelty search, count validated nontrivial novel results |
| Cross-domain analogy/transfer | **Research goal**, not demonstrated | Hold out one domain; evaluate transfer to mathematically mapped target domain vs lexical retrieval baselines |
| Compare against graph walks/RAG/embedding retrieval | **Not yet benchmarked** | Fixed dataset, compute/time budget and preregistered objective metrics |
| Modularize the 12k+ line monolith | **Planned** | Extract pure storage/learning/simulation modules with migration-safe regression suite |
| Windows and macOS GUI verification | CI/build workflows prepared; physical GUI manual verification pending | Install/test on Win11 x64, Intel macOS, Apple Silicon macOS; record outcomes |
| macOS signing/notarization and Windows signing | **Not configured** | Maintainer-controlled signed release, clean system launch test |

Suggested measurement fields: data source IDs and read depth, unit-label precision/recall, rejected unit counts, edge ordering consistency, probability calibration, pulse-response reproducibility, memory/storage and throughput, and downstream correctness of research questions independently assessed by domain specialists.
