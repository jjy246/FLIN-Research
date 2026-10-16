# Security policy

This is an experimental local-first research application. There is no formal third-party security audit and no public security response guarantee. For suspected vulnerabilities, avoid posting exploits, tokens, private academic files or databases in a public GitHub issue; contact the repository maintainer via private channel once the project has a public maintainer contact.

Threat boundaries: the program fetches literature and optional PDFs from third-party servers, imports SQLite/JSONL files, stores citation/extracted text, opens links in a browser and optionally connects to a local Ollama endpoint. URL scheme/redirect checks and import validation provide only **partial defense**. Operate on trusted systems, update dependencies, use unprivileged accounts, minimize permissions, and review public data/provider terms. Do not run arbitrary unknown networks or SQLite files as privileged users.

Report should include platform, version/commit, minimal reproduction and impact, with any credentials removed.
