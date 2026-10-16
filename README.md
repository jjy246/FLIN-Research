# FLIN — Feature-Link Intelligence Network

**An open-source, experimental framework for source-grounded associative memory research.**

> **Important scope:** The executable application in this repository is the
> **mathematics-specific reference implementation**. Its automatic collection,
> relevance filters, memory-unit acceptance criteria and problem-generation
> pipeline are **designed for mathematics**, including mathematical applications
> in other fields. It is **not** an out-of-the-box knowledge-network builder for
> physics, medicine, history, or every other domain. **You are welcome to fork
> the code and adapt those stages for your own area of knowledge.**

FLIN explores whether source-grounded input clusters can create memory units and
reinforce directed pathways which later guide pulse-based associations.
Memory retrieval is not embedding-based; a **separate, optional Ollama component**
drafts and critiques mathematics research questions. These engineering choices
are **research hypotheses**, not established neuroscience or verified intelligence.

**Welcome to the FLIN community!** We invite constructive suggestions,
rigorous criticism, experiments, documentation improvements, new software
modules, forks for other knowledge domains, and contributed memory networks.
Sharing reproducible successes **and failures** helps the whole community.

## FLIN Community Network Hub — share your research 🧠

**[Explore and share community networks (GitHub Discussions)](https://github.com/jjy246/FLIN-Research-Desktop/discussions)** · **[Download official reviewed networks (Releases)](https://github.com/jjy246/FLIN-Research-Desktop/releases)**

We welcome memory networks, novel experiments, theory critiques, suggestions,
and independently developed FLIN forks for **any field of knowledge**. The
unmodified official collection pipeline is **mathematics-specific**; other
subjects require contributor adaptations and a clearly identified compatible
fork. A community post is not an endorsement or a guarantee of import
compatibility.

**Three ways to participate:**

1. **Share freely in Network Showcase.** Host your `.sqlite3` in your own
   GitHub Release, then post its download link, SHA-256 checksum, research
   method, data rights, and compatible FLIN/fork version in
   [Discussions](https://github.com/jjy246/FLIN-Research-Desktop/discussions).
   No official approval is required to discuss or showcase your work.
2. **Exchange ideas and results.** Join *Research & Experiments*, *Ideas &
   Theories*, *Domain Extensions*, or *Help & Questions*. Reproducible negative
   results and constructive criticism are welcome.
3. **Apply for optional official publication.** Use the
   [Network Submission form](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml)
   if you want maintainers to review and republish your network in the
   project's official Releases. Only networks actually usable in the official
   mathematics app qualify for those official reference-network assets.

Community-hosted `.sqlite3` snapshots and **official reviewed** snapshots are
separate collections. Neither is scientifically certified. For download,
sharing and import instructions see the **[Community Network Hub guide](docs/COMMUNITY_HUB.md)**.

## Get FLIN and choose your path

| I want to… | Start here |
| --- | --- |
| Run the current mathematics desktop application | [Installation](#install-and-run) · [Complete user manual](docs/USER_GUIDE.md) |
| Understand the proposed FLIN mechanism | [FLIN theory](docs/FLIN_THEORY.md) · [Architecture](docs/ARCHITECTURE.md) |
| Adapt the code to another knowledge domain | [Porting guide](docs/PORTING_OTHER_DOMAINS.md) · [Contributing](CONTRIBUTING.md) |
| Download and **use** a shared `.sqlite3` network | [GitHub Releases](https://github.com/jjy246/FLIN-Research-Desktop/releases) · [Import instructions](#download-and-use-a-memory-network) |
| Explore or share community-created networks | [FLIN Community Network Hub](docs/COMMUNITY_HUB.md) · [Discussions](https://github.com/jjy246/FLIN-Research-Desktop/discussions) |
| Share my own network for official review | [Network submission form](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml) · [Review guide](docs/COMMUNITY_NETWORKS.md) |
| Report bugs or propose an improvement | [Issue templates](https://github.com/jjy246/FLIN-Research-Desktop/issues/new/choose) |
| Help improve the open-source code | [Contribution guide](CONTRIBUTING.md) |
| Maintain/publish this repository | [Start-to-finish GitHub setup](docs/OPEN_SOURCE_LAUNCH.md) |

## Install and run

The full Python application is included (`flin_desktop.py`); **this is not a
README-only project**. You can run it from source or, after CI builds are
completed, download an unsigned portable desktop build from Actions/official
Releases. **This ZIP does not already contain native `.exe` or `.app` builds.**

| Platform | Source launcher | Instructions |
| --- | --- | --- |
| Windows 10/11 | `start_windows.bat` | [Windows guide](docs/INSTALL_WINDOWS.md) |
| macOS Intel / Apple Silicon | `start_macos.command` | [macOS guide](docs/INSTALL_MACOS.md) |
| Ubuntu / Linux | `./start_linux.sh` | [Linux guide](docs/INSTALL_LINUX.md) |

With Python **3.12** installed, from the repository folder on Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python flin_desktop.py
```

On Windows PowerShell, use:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe flin_desktop.py
```

Linux GUI users may also need `python3-tk` and `python3-venv`. Starting from
source requires a graphical display for the desktop GUI. API-based research
collection requires internet connectivity. Ollama and its models are optional
and only needed for local language-model question generation.

For a fully offline, **synthetic** first example:

```bash
python scripts/demo_offline.py
```

It creates temporary memory units/links, simulates pulses, and cleans up. This
demonstration is **not** evidence of mathematical knowledge or a validated
brain model.

## Build a mathematics memory network

1. Launch the app; under **Manage Networks / Create / Switch / Import**, create
   a fresh network so existing data is not changed.
2. Open **Automatic Build Network Settings**. Turn off continuous discovery for
   your first test, select a small budget such as **3 topics × 5 papers**, and
   leave full PDF fetching off at first.
3. Start collection. The application queries public research sources, stores
   provenance, extracts mathematics-focused input clusters, and learns directed
   associations from qualified external inputs.
4. Inspect input clusters and original source evidence before interpreting a
   memory unit or an edge. Missing, incorrect or weak evidence is possible.
5. Open **FLIN Directed Pulse Associations**, select an **existing memory
   label**, and simulate pulse propagation. Visualized weights are **routing
   preferences**, not proofs, entailments or semantic similarity scores.
6. Export a complete SQLite snapshot before major experiments.

[Read the detailed operating manual](docs/USER_GUIDE.md).

## Download and use a memory network

**[Browse published SQLite memory networks](https://github.com/jjy246/FLIN-Research-Desktop/releases)**

Published releases may contain a **directly downloadable `.sqlite3`
asset**, such as `v1.sqlite3` or `association.sqlite3`. If no SQLite asset is visible, no network snapshot has been published
yet. Downloads may include maintainer networks and community networks that
passed the official **manual review process**.

1. Download a `.sqlite3` file from the **Assets** section of a network release.
2. Start FLIN and open **Manage Networks / Create / Switch / Import**.
3. Click **Import SQLite**, choose your download, and give it a new local name.
4. Switch to the imported independent network, explore its memories and simulate
   associations. Your current network is **not overwritten**.

Alternatively, the app has **Browse Published Networks (GitHub Releases)**;
it can discover and download published SQLite assets. Downloads are subject
to network availability and GitHub API limits. A terminal import also works:

```bash
python flin_desktop.py --import-network /path/to/association.sqlite3 --network-name "Shared network"
```

**Only import networks you trust.** An officially reviewed snapshot has been
checked for format/provenance and usable links, **not** certified as safe,
mathematically true or scientifically valid. See
[sharing, review and release rules](docs/COMMUNITY_NETWORKS.md).

## Share your own network

**Everyone is welcome to submit a source-attributed FLIN network for review.**
Contributions need not be mathematically successful to be interesting, but an
**official downloadable SQLite release must currently be importable by this
mathematics reference application**. Other-domain forks with incompatible
schemas should publish their own releases or propose an interoperability change
via an Issue/PR; they are not silently treated as compatible.

1. Export **complete memory network → SQLite** in the app, or run:
   `python flin_desktop.py --export-network ./exports --export-format sqlite`.
2. Locate the exported `association.sqlite3` inside its new timestamped
   directory. **Never upload the live changing database.**
3. Validate your export and calculate its SHA-256 hash:
   `python scripts/inspect_network_snapshot.py PATH/association.sqlite3 --require-flin`.
4. Upload your snapshot to a location with a public download link (preferably
   a Release in your own repository). Provide source details and redistribution
   permissions.
5. [Open a Network Submission issue](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml)
   with its download URL, checksum, FLIN version, reproducible example and
   limitations. Only maintainers publish accepted copies in official Releases.

**Do not commit `.sqlite3` databases, academic PDFs, private documents or API
secrets to Git.** The `.gitignore` excludes them. The project's Apache-2.0
source-code license **does not automatically license research databases**.

## Adapt FLIN to a new knowledge domain

**Fork the repository** and customize the topic discovery, subject-specific
quality gates, input clustering and relation extraction for the target domain.
The current main program *forces mathematics* for collection and fresh network
creation; changing names or toggling a UI field is not sufficient. Keep the
learning rules and SQLite compatibility requirements explicit, and test any
changes rather than declaring conceptual truth from a link weight.

[Step-by-step domain-porting map](docs/PORTING_OTHER_DOMAINS.md) ·
[Contribution and fork guidelines](CONTRIBUTING.md).

## How the model works (short version)

1. Public literature/source records are collected with provenance.
2. A lexical, mathematics-specific quality gate extracts **effective input
   clusters** of source-observed features.
3. Repeated qualified *external input* strengthens directed memory links.
4. During recall, a pulse follows **one** allowed outgoing edge chosen by
   relative link weight, and does not immediately reverse along the last edge.
5. Pulse arrival **frequency** and a threshold determine visible responses.
6. The question generator, when enabled, uses local Ollama separately.

The literature/evidence graph (`units`, `edges`) and FLIN associative graph
(`abc_units`, `abc_edges`) are different. The current system is a software
prototype; biological claims and mathematical conclusions need independent
validation. [Full technical explanation](docs/FLIN_THEORY.md).

## Community and governance

- **Source code license:** [Apache License 2.0](LICENSE). Forks and modifications
  are permitted under its terms. [Licensing details](LICENSING.md).
- **Community networks, research exchange, ideas and questions:** [Discussions](https://github.com/jjy246/FLIN-Research-Desktop/discussions) · [Community Hub](docs/COMMUNITY_HUB.md).
- **Bug reports and tracked feature requests:** [Issues](https://github.com/jjy246/FLIN-Research-Desktop/issues/new/choose).
- **Code/doc improvements:** [Pull requests](CONTRIBUTING.md).
- **Network submissions:** [Review request form](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml).
- **Security reports:** [Security policy](SECURITY.md) — please do not post
  exploitable vulnerabilities publicly before coordinated review.
- **Rules and decision-making:** [Governance](GOVERNANCE.md) ·
  [Code of Conduct](CODE_OF_CONDUCT.md).
- **First-time maintainer launch:** [Complete checklist](docs/OPEN_SOURCE_LAUNCH.md), [starter community issues](docs/COMMUNITY_STARTER_TASKS.md), [Community Hub maintainer setup](docs/MAINTAINER_HUB_SETUP.md), and [launch announcement](docs/COMMUNITY_ANNOUNCEMENT.md).

**Open invitation:** Whether you're studying mathematics, adapting the code to
another subject, checking a research assumption, or building tools around FLIN,
please share what you discover. Forks and independently published networks are
welcome. Let's make reproducible experimental associative-memory research easier
to inspect, challenge and improve.
