# Data safety, privacy, provenance, and publication

## Where data is stored

The storage root is chosen in this priority order:

1. Explicit environment variable `BRAIN_DATA_DIR` (absolute path recommended).
2. **Existing legacy folder** `~/.local/share/brain_project` (retained even on Windows/macOS to avoid accidental loss of prior project data).
3. New platform default:
   - Windows: `%LOCALAPPDATA%\FLIN\BrainProject`
   - macOS: `~/Library/Application Support/FLIN/BrainProject`
   - Linux: `~/.local/share/brain_project`

This root contains the network registry, individual SQLite databases, a shared literature catalog, derived positions, source excerpts, question histories and other local state. **Do not commit this folder to GitHub.**

## Backup strategy

- Before building large datasets, deleting graph nodes, changing quality filters or running migration-related CLI commands, export a **full SQLite snapshot**.
- Use `--export-network "DEST_DIR" --export-format sqlite` to create a consistent new snapshot without modifying the active DB.
- Verify backup contents and restore a **copy** into a new network to test recoverability.
- Portable JSONL.gz exports are useful for sharing or importing into other tools but do **not** necessarily include all history and question tables.
- Keep enough free disk space for the existing database + WAL + temporary export/snapshot. Do not manually copy an active WAL-mode SQLite `.sqlite3` file without its consistency guarantees; use the built-in online backup.

## Data ethics and security

- Extracted scientific content remains attributed to its original source. Publisher PDFs, paper abstracts, Wikipedia content and external provider API responses are subject to **their own** copyright and licensing terms.
- API keys must be set through environment variables; `.env.example` is a template **not an automatic secrets loader**. Do not put real keys in GitHub commits, screenshots or issues.
- The app contacts public research providers during collection and contacts the local Ollama server during question generation. It is **not** an anonymizing network client.
- The PDF fetcher checks initial and redirected URLs and applies size/page/text caps, but cannot guarantee defenses against all SSRF-like attacks, DNS rebinding, malicious PDFs or hostile imported SQLite databases. Run only on trusted networks, maintain dependencies, and do not feed sensitive organizational content into a public-source workflow.
- The app does not establish medical, financial, physical or scientific conclusions. Inspect source snippets and carry out independent verification before applying research output to real-world decisions.

## Publication checklist

Before making the GitHub repository public:

1. Confirm no `*.sqlite3`, `*.db`, `.env`, API keys, PDFs or generated research exports are staged (`git status`).
2. Review source code and check that third-party libraries are installed from trusted package indexes.
3. The repository source code is licensed under **Apache-2.0**; keep its notices when redistributing. This does not grant rights to third-party academic content or independently published SQLite network data. See [Licensing](../LICENSING.md).
4. Do not state that FLIN simulates real neurons, proves theorems, understands mathematics, or achieves artificial general intelligence. State precisely which operational rules are implemented and which are hypotheses.
5. For native binaries: sign, notarize, manually test per OS and document reproducibility before distributing to nontechnical users.
