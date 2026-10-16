# Contributing to FLIN

**Thank you for helping build a transparent, critical, and reproducible FLIN community.**
The original executable project is a mathematics-specific research reference.
We welcome improvements and independent forks for other areas of knowledge.

## Ways to participate

1. **Issues:** File a bug, scientific objection, feature request, reproducible
   experiment or documentation correction using the GitHub Issue templates.
2. **Pull requests:** Propose focused source or document changes (see below).
3. **Community Showcase:** Share your own network release URL, SHA-256, and compatibility details through [Discussions / Network Showcase](https://github.com/jjy246/FLIN-Research-Desktop/discussions); no approval is needed for a community listing. Follow the [Community Hub guide](docs/COMMUNITY_HUB.md).
4. **Optional official review:** Submit `.sqlite3` via the official
   [Network Submission](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml)
   Issue, **not** by Git committing a database.
5. **Domain forks:** Fork FLIN to specialize it for a new research area. See
   [Domain porting](docs/PORTING_OTHER_DOMAINS.md). Keep the limitations and
   compatibility status visible to users.

## First-time code contributor: exact workflow

1. Sign in to GitHub; visit the project and click **Fork → Create fork**.
2. Clone *your fork*: `git clone https://github.com/YOUR_NAME/FLIN-Research-Desktop.git`.
3. Enter the folder and create a branch:
   `git switch -c fix/brief-description`.
4. Create a venv using Python 3.12, then install `requirements.txt`.
5. Make one focused change. Document whether it affects the mathematics-specific
   behavior, FLIN dynamics, DB schema, GUI, CLI, or model prompting.
6. Run `python -m unittest discover -s tests -v` and
   `python scripts/validate_repo.py`. For mathematical behavior changes, include
   a reproducible source or synthetic test and avoid claiming truth from a
   heuristic score.
7. Confirm `git status` contains no `.env`, SQLite database, copyrighted PDF,
   credentials, or model weights. Run `git diff --check`.
8. `git add <intended files>`;
   `git commit -m "Explain focused change"`;
   `git push -u origin fix/brief-description`.
9. On GitHub open a **Pull Request** from your fork branch to the official
   `main`. Fill the PR template and respond to review feedback.
10. Maintainers run CI and review. **PRs are not automatically merged**; the
    maintainer decides whether the proposed behavior belongs in the canonical
    mathematics reference or is better maintained as a separate fork/module.

## Code compatibility and scientific claims

- Do not silently change historical SQLite column names, graph IDs, source
  evidence, edge meanings, stable CLI names or portable export formats.
- Keep **literature graph** edges distinct from **FLIN directed preference**
  edges; do not relabel route strength as conceptual equivalence.
- Preserve exact source provenance, original input clusters and separation of
  *external learning* from *pulse simulation*.
- Changes to pulse selection, revisit limits, activation thresholds or gate
  feedback must be tested and described as implementation choices.
- Domain forks **may** alter mathematics-specific filters and collectors, but
  must state if SQLite imports remain compatible. A merge into the official app
  needs explicit maintainer acceptance.
- Never submit data, text, weights or generated output whose redistribution
  rights are not established. Do not collect private personal information.

## Licensing, attribution and conduct

By contributing, you agree your original submitted code and documentation may
be distributed under the repository's **Apache-2.0** license. You retain the
copyright in your contribution subject to those terms. If you do not have
rights to reuse material, do not submit it. Research datasets/SQLite networks
have separate permissions and are reviewed separately.

Respect the [Code of Conduct](CODE_OF_CONDUCT.md) and the
[Governance](GOVERNANCE.md). Criticism of FLIN's theory is welcome when it
is specific, reproducible and respectful.
