# Research providers, language models and reproducibility

## What the local models do

The optional **Ollama** subsystem drafts ten research questions, judges them, provides critiques and produces revised questions. A model does **not** embed, route, select, score or attenuate FLIN pulses.

Default model roles:

| Role | Environment setting | Default |
| --- | --- | --- |
| Main model | `BRAIN_OLLAMA_MODEL` | `qwen3:4b-instruct` |
| Fallback | `BRAIN_OLLAMA_FALLBACK` | `qwen2.5:3b` |
| Generator | `BRAIN_MODEL_GENERATOR` | Main model |
| Judge | `BRAIN_MODEL_JUDGE` | Main model |
| Critic | `BRAIN_MODEL_CRITIC` | Fallback model |
| Reviser | `BRAIN_MODEL_REVISER` | Main model |

Fetch models **manually** with `ollama pull`. Models are not bundled and names may change upstream. If your GPU cannot hold a model, Ollama may spill to RAM/CPU or fail; plan for sufficient memory. Configuration is set **before app startup** in your terminal/OS environment, e.g. on Linux/macOS:

```bash
export BRAIN_MODEL_CRITIC='qwen2.5:3b'
python flin_desktop.py
```

Windows PowerShell:

```powershell
$env:BRAIN_MODEL_CRITIC = 'qwen2.5:3b'
python flin_desktop.py
```

Advanced context/token controls include `BRAIN_NUM_CTX`, `BRAIN_MAX_NUM_CTX`, `BRAIN_MAX_NUM_PREDICT` and timeouts. Change them after measuring memory use; the application serializes calls to avoid simultaneous models on low-VRAM GPUs.

## Source providers (and what is actually read)

- **Wikipedia / MediaWiki:** verified mathematics topics, article content and extracted bibliographic footnotes.
- **Crossref:** DOI resolution and bibliographic metadata, sometimes abstracts.
- **arXiv:** arXiv IDs and preprint metadata/abstracts.
- **OpenAlex (optional):** works search and metadata; enable with `BRAIN_USE_OPENALEX=1`, and supply `OPENALEX_API_KEY` when required by the provider.
- **OpenAIRE, Europe PMC, DBLP:** additional paper discovery/metadata on supported routes.
- **Semantic Scholar (optional):** availability dependent on API policy/credentials; use `SEMANTIC_SCHOLAR_API_KEY` where applicable.
- **Offline literature catalog:** SQLite/FTS local cache, including optional imported OpenAlex JSONL/GZ snapshots.

A source with only title metadata is a **title-only** source. A provider's abstract is **abstract-only**. Text extracted from an eligible OA PDF is **partial full text** (bounded to a page/character cap), not necessarily a full article reading. The application's source-depth record should be checked before reporting coverage.

## Responsible access

- Respect provider rate limits, quotas, content licensing and API terms. Access to full text is **not** guaranteed; paywalls are not bypassed.
- Public pages can change; citations and rank counts may update between collections.
- A DOI, arXiv ID or Wikipedia footnote provides bibliographic identity, not proof that a source's mathematical claims are sound.
- The source extractor relies on textual mathematical vocabulary and observed sentence position, **not embeddings**; false positives/negatives are possible.
- Never upload API keys or author-identifying proprietary source text into a public repository.

## Example reproducibility report

Record: repository commit SHA, Python version/OS, active network ID, source provider statuses, topic/paper caps, PDF enabled/disabled, source read levels, accepted/rejected unit counts, simulation input, pulse rate, duration, threshold, window, revisit limit, random seed (when using the Python API), model names/tags, and manually verified external sources.
