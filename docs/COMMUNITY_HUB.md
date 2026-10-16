# FLIN Community Network Hub

**Build. Share. Reproduce. Question. Improve.**

This is the community's meeting place for experimental associative memory networks built with FLIN or clearly attributed FLIN-derived forks. The [Discussions board](https://github.com/jjy246/FLIN-Research-Desktop/discussions) is a public catalogue of **community-shared work**, not an assertion that a network is correct or compatible. The [official Releases](https://github.com/jjy246/FLIN-Research-Desktop/releases) contain maintainer-published application versions and reviewed network snapshots.

> **Important scope:** The *unmodified official FLIN application* is a **mathematics-specific reference implementation**. Cross-disciplinary networks are welcome **when authors identify the modified fork required to use them**. A history or biology network cannot automatically be imported into the official program unless its actual schema and behavior are compatible.

## Choose a community space

| Goal | Where to go |
| --- | --- |
| Browse or share a reusable memory network | [Network Showcase](https://github.com/jjy246/FLIN-Research-Desktop/discussions) (select **Network Showcase**) |
| Publish an experiment, results or failed reproduction | Research & Experiments |
| Suggest or challenge an underlying theoretical assumption | Ideas & Theories |
| Show another-domain source fork or a stand-alone extension | Domain Extensions |
| Ask for help with import, simulation or compatibility | Help & Questions |
| Find official news | Official Announcements |
| Ask the maintainers to **review and republish a network** | [Network Submission Issue](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml) |
| Download a **maintainer-reviewed** snapshot | [Official GitHub Releases](https://github.com/jjy246/FLIN-Research-Desktop/releases) |

Everyone can discuss and share their own hosted releases. **Maintainer approval is NOT needed to share a network in Network Showcase.** It IS required for a copy to appear in the project's official Releases. Discussion participants do not receive write access to official Releases.

## For contributors: publish your network in the Hub

1. **Export a consistent snapshot** using **Export complete memory network → SQLite**, or:

   ```bash
   python3 flin_desktop.py --export-network ./exports --export-format sqlite
   ```

   The export creates a timestamped folder containing `association.sqlite3`. Avoid copying a database while FLIN is writing. Exports contain the **currently active** network; repeat for other networks.

2. **Inspect the snapshot** (do not publish private records or rights-restricted content):

   ```bash
   python3 scripts/inspect_network_snapshot.py /path/to/association.sqlite3 --require-flin
   sha256sum /path/to/association.sqlite3  # Linux; on macOS: shasum -a 256
   ```

   `--require-flin` is appropriate for a network claimed to work in official FLIN. A domain fork using a different schema must disclose incompatibility, and may not pass this reference-specific check. The inspector is only a *structural*, read-only check, **not** a security or scientific validation. On Windows PowerShell use `Get-FileHash -Algorithm SHA256 'C:\path\to\association.sqlite3'`.

3. **Host a public download.** The preferred option is a Release in a repository you own. In that repository, open **Releases → Draft a new release**; use a tag such as `network-v1` and attach your exported `.sqlite3` under **Assets**. Provide an explicit data license, version compatibility and source information. No write access to the official FLIN repo is needed. For very small files, you may instead attach a `.zip` to a Discussion (GitHub's supported attachment limit is **25 MB** for nonmedia files); for larger networks, use a Release. Each GitHub Release asset must be **under 2 GiB**. Please do not commit generated SQLite into Git history.

4. Open [Discussions → New discussion](https://github.com/jjy246/FLIN-Research-Desktop/discussions/new/choose) and select **Network Showcase**. Fill out the form: name, domain, author, download URL, SHA-256, FLIN or fork version, compatibility, graph statistics, evidence sources, procedure, limitations, and redistribution terms. If the submission form is not yet available, use the [manual showcase template](EXAMPLE_NETWORK_SHOWCASE.md).

5. Reply to questions, publish corrected snapshots under **new version tags**, and link newer versions from your original discussion. Do not silently replace an asset without updating its checksum.

6. **Optional official review:** if and only if you want it included in *official* Releases, open a [Network Submission Issue](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml), link to your showcase and public asset, and follow the [review policy](COMMUNITY_NETWORKS.md). Incompatible domain forks can still stay in the community Showcase even when not eligible for the official math app's network Releases.

## For downloaders: actually use shared networks

1. Read the discussion before downloading. Verify the author's download URL, target FLIN/fork version, stated data rights, and SHA-256; be careful with unknown hosts and executable attachments.
2. Download the `.sqlite3` from the author's GitHub Release **Assets** (or an official reviewed release). Optionally compare the computed checksum:

   ```bash
   sha256sum /path/to/downloaded.sqlite3
   ```

3. If the author says **compatible with the official mathematics reference application**, start FLIN, open **Manage Networks → Import SQLite**, select the downloaded file, assign a unique local name, and activate the imported network. Or run:

   ```bash
   python3 flin_desktop.py --import-network /path/to/downloaded.sqlite3 --network-name 'Community network'
   ```

4. If it requires a domain fork, install the **named fork and version** instead. Do not assume all forks share one schema.
5. Inspect the network's memory units, original sources and pulse behavior. Keep it separate from existing local networks. Treat all associations as experimental, not verified knowledge.

**Do not import untrusted databases on a machine containing sensitive data.** Test unfamiliar files in an isolated, resource-limited environment. The app's import and the snapshot inspector are not comprehensive malware, privacy or data-rights audits.

## What makes a useful post?

A good community network post includes a reproducible method, specific source provenance, the actual download URL, a checksum, a declared license for the **data** (separate from FLIN's Apache-2.0 code license), basic counts, a meaningful experiment, and an explicit compatibility statement. Report unexpected or negative results too. If a file is large, share a sample and the complete hosted Release, not a database committed to the core Git repository.

## Ground rules

- Respect [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md), scholarly attribution, privacy and redistribution restrictions.
- No credentials, medical records, private documents or unauthorized copyrighted full texts in shared snapshots.
- No implied peer review: “community shared” and “maintainer reviewed for publication” are different statuses, neither of which certifies factual or scientific validity.
- Commercial or academic third-party data licenses still apply. FLIN's source code license does **not** automatically cover any submitted network.
- Constructive criticism of FLIN's theory is welcome. Separate measured behavior from conjecture.
