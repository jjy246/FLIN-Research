# Suggested first community Issues (maintainer copy-and-paste)

These are **proposals**, not pre-existing GitHub Issues. After publishing the
repository, the maintainer may open them via the Issue templates and label them
`good first issue`, `documentation`, `research`, `help wanted`, or `domain-fork`
as appropriate. Create labels before assigning them; GitHub does not create all
of these labels automatically.

## Issue 1 — Check the first Windows and macOS builds

**Goal:** Run the unsigned native artifact produced by GitHub Actions on one
real Windows x64, macOS Intel or macOS Apple Silicon device. Document OS,
startup result, Tk GUI behavior, ability to import a separate SQLite network
and whether Ollama is optional as expected. **Do not ask users to bypass OS
security protections or share private files.**

**Acceptance:** Reproducible environment description, screenshot with no
personal information, error logs sanitized, and a minimal recommendation.

## Issue 2 — Reproducibility benchmark for directed pulse routing

**Goal:** Propose a small, openly shareable synthetic input-cluster corpus. Run
the existing deterministic pulse experiment with multiple seeds and summarize
how learned weights and outgoing pulse distributions vary.

**Acceptance:** Source inputs, random seeds, code version, metrics, at least one
counterexample, and a clear statement that weights are not mathematical facts.

## Issue 3 — Improve the introduction for first-time users

**Goal:** Identify confusing steps in Windows/macOS/Linux installation and the
first mathematics-network experiment. Improve documents without modifying
neuroscience claims.

**Acceptance:** Steps reproduce on a clean machine, corrections have verified
CLI names/menu labels, no unsupported accuracy claims.

## Issue 4 — Proposed domain fork: historical documents

**Goal:** Draft a **fork-level** design for evidence-based history memory units.
Discuss source reliability, event timestamps, quotation attribution and what
cannot be safely inferred from document order.

**Acceptance:** Design note following [porting guide](PORTING_OTHER_DOMAINS.md),
comparison against mathematics pipeline, known false-positive examples. No
expectation the official mathematics app already supports history.

## Issue 5 — Cross-fork SQLite interoperability proposal

**Goal:** Document minimum properties a network requires for official import,
identify what domain-specific fields are needed without corrupting old SQLite
files, and propose a migration test matrix. Do **not** alter the official
application without a separate reviewed PR.

**Acceptance:** Detailed schema/compatibility proposal, data safety risks and
explicit backward-compatibility verification.

## Issue 6 — Audit math-source relevance false positives

**Goal:** Assemble a small legally shareable title-and-abstract metadata sample
containing clearly relevant and irrelevant mathematical sources. Report how
lexical quality gates perform, including failure patterns.

**Acceptance:** Independently auditable item IDs, source rights, reasons for
acceptance/rejection, and limitations; no full non-redistributable articles.

## Maintainer publishing sequence

1. Publish the README and `LICENSE` first.
2. Confirm `Issues` and optionally `Discussions` are enabled.
3. Open three starter Issues first (for instance 1, 2 and 3) to avoid burying
   early volunteers in work; create the remaining Issues only if useful.
4. Mark a task `good first issue` only if its scope and review criteria are
   actually suitable for a newcomer.
5. Reply to first contributors with concrete verification requests and link to
   [CONTRIBUTING.md](../CONTRIBUTING.md) and [GOVERNANCE.md](../GOVERNANCE.md).
