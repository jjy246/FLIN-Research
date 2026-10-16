# FLIN open-source launch — complete maintainer checklist

This guide assumes the repository owner is **`jjy246`**, wants to create a
brand-new public repository called **`FLIN-Research-Desktop`**, and is using
Ubuntu for the first upload. The repository itself includes unmodified FLIN
application source and scripts; no personal SQLite database is included.

## A. Download, extract, and verify *before* publishing

1. Download **`FLIN-Open-Source-GitHub.zip`** from the assistant response.
2. Extract the ZIP to a clean location that does **not** contain an older `.git`:

   ```bash
   mkdir -p "$HOME/flin-launch"
   unzip "$HOME/Downloads/FLIN-Open-Source-GitHub.zip" -d "$HOME/flin-launch"
   cd "$HOME/flin-launch/FLIN-Open-Source-GitHub"
   ```

   If your download has a different path, replace the file path explicitly.

3. Confirm the files `flin_desktop.py`, `published_networks.py`, `README.md`,
   `LICENSE`, `docs/`, `tests/`, and `.github/workflows/` are present:

   ```bash
   ls -la
   find .github -maxdepth 3 -type f | sort
   ```

4. Confirm no existing Git history is present: `test ! -e .git && echo clean`.
   **Do not run `git push --force` in an old source folder.**
5. Review the complete **Apache-2.0** [license](../LICENSE) and
   [permissions](../LICENSING.md). Publish only code you own or are entitled to
   sublicense; the maintainer must verify any reused third-party portions.
6. Scan the contents for secrets/private material, and double-check that
   no SQLite databases, PDF papers, API keys, saved questions or user data are
   included. `.gitignore` protects future accidental staging but cannot undo a
   previously committed secret.

## B. Run the offline checks locally

Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y git gh unzip python3.12 python3.12-venv python3-tk xvfb
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/demo_offline.py
```

If your Ubuntu environment does not provide `python3.12` in its configured
package repositories, install Python 3.12 using an appropriate trusted source;
**do not assume `python3` always means Python 3.12**. Tests that do not need
network access are still subject to first-time pip dependency downloads.

For an optional GUI smoke test (requires GUI dependencies):

```bash
xvfb-run -a .venv/bin/python scripts/smoke_gui.py
```

When using SSH without an X display, run headless CLI checks rather than the
Tk GUI. The workflow later runs tests on other OS platforms as well.

## C. Authenticate and create the *new* public repository

1. Confirm your intended GitHub username:

   ```bash
   gh auth login --web --git-protocol https
   gh auth setup-git
   gh api user --jq .login
   ```

   The output must identify the account which owns the intended repository.
   Never paste tokens/passwords into chat or public commits.

2. **Inside the extracted new folder**, run:

   ```bash
   git init
   git branch -M main
   git add .
   git status --short
   ```

   Inspect the staged list. You should see `.py` application/source code,
   docs, YAML workflows and the `LICENSE`, but **no `.sqlite3`, `.env`, PDFs,
   binary models or private research data**. `git status --short` is essential.

3. Configure your public Git author identity locally if Git prompts for it:

   ```bash
   git config user.name "YOUR_PUBLIC_GIT_NAME"
   git config user.email "YOUR_PUBLIC_GIT_EMAIL"
   ```

4. Commit the contents:

   ```bash
   git commit -m "Initial open-source FLIN mathematics reference implementation"
   ```

5. Create GitHub repository and push in **one** command:

   ```bash
   gh repo create jjy246/FLIN-Research-Desktop \
     --public --source=. --remote=origin --push \
     --description "FLIN: open-source experimental associative memory, mathematics reference implementation"
   ```

   **Do not create a README/license independently through the GitHub website**
   before this command: it creates an empty remote from the local sources.
   If GitHub reports that the repository already exists, visit its URL and
   reconcile it rather than overwriting with `--force`.

6. Confirm the results:

   ```bash
   git remote -v
   git status
   gh repo view jjy246/FLIN-Research-Desktop --web
   ```

   Check the website contains `flin_desktop.py`, `LICENSE`, `README.md`,
   `.github/ISSUE_TEMPLATE/`, `.github/workflows/` and the docs.

## D. Configure the community on GitHub (in the web UI)

1. Open **Settings → General → Features**, enable **Issues**. This makes
   network submission, bug report and research idea templates accessible.
2. Open **Settings → Branches** (or **Settings → Rules → Rulesets**, where
   available). Create a rule for `main`: require pull requests and selected
   CI status checks before merging. Keep maintainer access for moderation;
   do not grant strangers write access to publish networks.
3. Open **Actions**, enable workflows if GitHub requests it. Review security
   policies for external PRs before approving any external workflow changes.
4. Add repository description and topics such as `associative-memory`,
   `mathematics`, `python`, `research`, `knowledge-graph`, `sqlite`,
   `brain-inspired-computing`. Do not claim verified AGI/brain emulation.
5. Under the repo **About** / files, check that `LICENSE` is recognized as
   Apache-2.0. Look at [CONTRIBUTING](../CONTRIBUTING.md),
   [GOVERNANCE](../GOVERNANCE.md), [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md).
6. Open **Issues → New issue**; check the network submission, bug, and idea
   forms appear and link to the correct owner/repository.
7. Optionally enable **Discussions** under Settings → Features to allow
   longer research debate separated from issue tracking.

## E. Produce portable desktop apps (Windows/macOS/Linux)

1. Open **Actions → FLIN source checks** and verify all matrix jobs. If some
   platform jobs fail, investigate instead of advertising those builds as tested.
2. Open **Actions → Build unsigned native desktop packages → Run workflow**.
   Alternatively, create a code release tag as below.
3. When all four jobs finish, download artifacts from the workflow run:
   `FLIN-windows-x64`, `FLIN-macos-intel-x64`,
   `FLIN-macos-apple-silicon-arm64`, and `FLIN-linux-x64`.
4. Extract and test each on a machine of the matching OS. Confirm that the
   app starts, creates/imports a network, simulates pulses and closes cleanly.
   Verify security software and OS protections before telling users to run
   unsigned downloads. **macOS apps are unsigned / not notarized**; treat them
   as development/testing builds until correctly signed.
5. In GitHub select **Releases → Draft a new release**, create a tag such as
   `v0.1.0`, attach the successfully built archive(s), list OS/architecture,
   known limitations and test coverage, then publish. GitHub workflow artifacts
   are not automatically public release assets.
6. Do not claim there is a binary download until that specific asset is
   actually attached to a published Release.

## F. Publish *your own* memory network for direct download/use

1. In the FLIN UI choose **Export complete memory network → SQLite**, or:

   ```bash
   mkdir -p exports
   .venv/bin/python flin_desktop.py --list-networks
   .venv/bin/python flin_desktop.py --export-network ./exports --export-format sqlite
   ```

   Only the currently active network is exported. A consistent export avoids
   copying an actively-written SQLite database.

2. Find the exported file and inspect it:

   ```bash
   find exports -type f -name association.sqlite3
   .venv/bin/python scripts/inspect_network_snapshot.py \
     "PATH_FROM_FIND/association.sqlite3" --require-flin
   sha256sum "PATH_FROM_FIND/association.sqlite3"
   ```

   Replace **`PATH_FROM_FIND`** with the actual timestamped folder; do not
   paste the placeholder literally. Review embedded sources, rights, private
   data, and paper text before publishing. This code validator is a format
   check only, not an absolute safety/content audit.

3. **Test in an isolated temporary directory**, by importing a copy into a
   separate FLIN network and simulating an input label that exists in the
   downloaded snapshot. Record the reproducible label and test result.
4. Open **Releases → Draft a new release**, create a unique tag
   `network-maintainer-v1`, title it **FLIN Memory Network — Maintainer 1**,
   and attach the exported `.sqlite3` as an **Asset** (do not put it into Git).
5. Add notes listing: FLIN version, number of active units/edges, scope,
   training sources, redistribution rights, SHA-256, limitations and how to
   import it. Publish the release. GitHub has a per-asset size limit; oversized
   databases need a documented alternative or segmented distribution.
6. Download that **public** asset as a user, check its SHA-256, and try the
   in-app **Manage Networks → Import SQLite** and/or **Browse Published Networks**.
7. Confirm the public [README](../README.md) link resolves to the published
   release; the README never guarantees a snapshot already exists.

## G. Accept the first community network (manual review)

1. A contributor exports their own full SQLite snapshot and publishes a public
   link plus checksum (normally in *their own* GitHub Release).
2. They submit a **Network Submission** Issue with sources, license/rights,
   size, source author, counts, schema/application version and demonstration.
3. On a separate analysis machine or isolated workspace: download, verify
   SHA-256, run `scripts/inspect_network_snapshot.py --require-flin`, inspect
   provenance and permission to redistribute, then import and pulse-test a
   **copy**. Do not blindly run an untrusted SQLite file in your daily profile.
4. If accepted, create a new official Release tag
   `community-USERNAME-v1`. Upload exactly the reviewed `.sqlite3`. Link the
   original submission Issue and contributor in release notes, include original
   SHA-256 plus license/limitations, then comment and close the Issue.
5. If rejected/requested changes, explain the reason in the Issue.
   Contributors do **not** receive repository write access by default.
6. Other-domain forks with incompatible schemas should keep their releases on
   their own repositories until an interoperable format is implemented.

## H. After launch: updates and stewardship

| Change | Action |
| --- | --- |
| Only docs/README | `git add README.md docs/; git commit -m "Update docs"; git push origin main` |
| New code / accepted PR | Merge after tests and review; tag a new software `vX.Y.Z` when ready |
| New owner SQLite snapshot | Export a fresh SQLite; publish a **new** `network-*` Release |
| Approved community SQLite | Publish reviewed file under a **new** `community-*` tag |
| Domain adaptation | Encourage its own fork/release; maintain compatibility notes |
| Malicious/vulnerable report | Follow `SECURITY.md`, not a public Issue |

**Do not delete old releases solely to keep the Downloads page short**; tags
are part of experimental reproducibility. The maintainer may withdraw a
snapshot if it is unsafe or distribution rights are uncertain.


## Launch the community network-sharing Hub

After the repository exists, **enable Discussions and create its category names in the GitHub website**; committing Markdown/YAML alone does not turn on this feature. Follow the [complete maintainer setup](MAINTAINER_HUB_SETUP.md) to configure six categories, verify the `.github/DISCUSSION_TEMPLATE/` forms, publish and pin the welcome post, and link your first `v1.sqlite3` snapshot. Keep self-hosted community Showcases distinct from optional maintainer-reviewed official Releases.
