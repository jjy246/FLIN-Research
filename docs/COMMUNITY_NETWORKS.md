# Publishing and contributing FLIN memory networks

**You are welcome to share your own FLIN memory network and help other researchers learn from your experiments.** Suggestions, constructive critiques, reproducible bug reports, and ideas for future development are also appreciated through [GitHub Issues](https://github.com/jjy246/FLIN-Research-Desktop/issues/new/choose). We encourage contributions that improve transparency and reproducibility; a submitted network is never represented as scientifically validated solely because it is shared.

The official **mathematics-specific** application accepts experimental, source-attributed **full SQLite memory-network snapshots that it can actually import** for manual review. Domain-modified forks with incompatible schemas may publish their own release and propose an interoperability improvement. The maintainer publishes approved snapshots in the repository's [Releases](https://github.com/jjy246/FLIN-Research-Desktop/releases) rather than committing databases to Git. **This is a human review process, not automatic community write access.** Only repository contributors with write permission can publish Releases. An approved snapshot is not a mathematical or scientific certification.

## Community sharing is different from official review

Everyone can independently share a network in [Network Showcase](https://github.com/jjy246/FLIN-Research-Desktop/discussions) immediately, without permission from repository maintainers. The file stays hosted by the author (usually in their own GitHub Release), and other participants can review, discuss and download it. **Only community-created networks requested for optional official inclusion need a Network Submission Issue and the review steps below.** Incompatible domain forks may still share in Discussions, while official mathematics-reference Releases require import compatibility. Read the [full Community Network Hub guide](COMMUNITY_HUB.md).

## A. Maintainer: publish your own network

Use the app's **Export complete memory network** action or, from the repository root:

```bash
python3 flin_desktop.py --list-networks
python3 flin_desktop.py --export-network ./exports --export-format sqlite
```

This produces a new time-stamped export directory containing `association.sqlite3`. This is a consistent SQLite snapshot; do not simply copy a live database while FLIN is writing to it. Only the **currently active** network is exported. Export other independent networks separately.

On Ubuntu/Linux, find the newest exported snapshot:

```bash
SNAPSHOT="$(find ./exports -type f -name association.sqlite3 -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)"
test -f "$SNAPSHOT" || { echo 'No exported snapshot found' >&2; exit 1; }
python3 scripts/inspect_network_snapshot.py "$SNAPSHOT"
sha256sum "$SNAPSHOT"
```

Review the content and source rights **before** making the database public. Then, if `gh auth status` confirms you are signed in to the repository's owner account:

```bash
TAG="network-maintainer-$(date +%Y%m%d-%H%M%S)"
gh release create "$TAG" "$SNAPSHOT" \
  -R jjy246/FLIN-Research-Desktop \
  --title 'FLIN Memory Network — Maintainer Snapshot' \
  --notes 'Experimental source-attributed FLIN SQLite memory network. Not independently validated. Import via Manage Networks > Import SQLite.' \
  --prerelease --latest=false
```

**No ZIP is necessary.** The downloadable `association.sqlite3` is shown in that Release's **Assets** section. GitHub currently limits any individual Release asset to less than 2 GiB. Use unique tags for subsequent versions rather than overwriting earlier network snapshots. Multiple releases can contain an asset named `association.sqlite3` without a conflict.

Using the GitHub web UI instead: go to **Releases → Draft a new release**, create a unique tag, enter a descriptive title and notes, attach the exported `.sqlite3` under **Assets**, then **Publish release**. On macOS/Windows, choose the export through the file manager rather than relying on the Linux-only `find -printf` example.

## B. Other users: submit your network for review

1. Run FLIN and use **Export complete memory network** (or `--export-network ... --export-format sqlite`). Do not copy an active SQLite database while it is being written.
2. Check that the snapshot is complete. Optional read-only validator: `python scripts/inspect_network_snapshot.py /path/to/association.sqlite3`.
3. Publish **your own** SQLite snapshot to a public download location, preferably as a GitHub Release asset in a repository you own. Include a SHA-256 checksum and make sure readers can download it without access credentials. Avoid adding SQLite to Git commits.
4. Open a [Network Submission issue](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml). Supply the network name, direct download URL, SHA-256, FLIN version, sources and their redistribution rights, node/edge counts, method, and limitations.
5. Wait for maintainer feedback *on that Issue*. If revisions are requested, export and submit a new snapshot with a new checksum. The maintainer alone decides whether to publish it as an approved community snapshot in Releases.

If the repository has disabled public Issues, the maintainer must enable them under **Settings → Features → Issues** before submissions work.

## C. Maintainer: review a submission

Review **before** sharing the contributor's data:

1. Check the Issue has an attributable author, an accessible URL, a 64-character SHA-256, provenance, and an explicit redistribution grant. **Do not download or publish** material when those rights are unclear.
2. Download the file to a disposable directory (not to FLIN's live data directory). Check the size (GitHub release assets must be below 2 GiB), verify SHA-256 against the submitted value, and review whether the stated source licenses permit redistribution of all embedded content.
3. On a machine used for untrusted-file review, run `python scripts/inspect_network_snapshot.py /path/to/downloaded.sqlite3`. It performs read-only SQLite structural checks, but passing does **not** prove the file is safe, free of private material, or mathematically valid. Prefer an isolated, resource-limited environment for untrusted data.
4. Inspect sampled memory labels, source references, and edge types. Reject unexpected secrets/personal data, unverifiable origin, inappropriate copyrighted full text, malformed imports, or spam. Optionally import **into a separate FLIN test network** only after satisfactory review.
5. If accepted, create a **new unique** Release tag such as `community-githubuser-20261016`, attach that exact reviewed `.sqlite3` without modification, and include the author's GitHub handle, original Issue URL, SHA-256, FLIN version, data scope, limitations, and redistribution notice in the Release notes. Link the approved release in the Issue, then close it.
6. If declined, explain the reason in the Issue and close it, so the process remains transparent.

Never give applicants write access to the project solely for uploading databases. GitHub Releases do not provide a built-in queue of proposed attachments awaiting maintainer approval; **the Issue is the review queue**, and only the maintainer publishes after acceptance.

## D. Domain-specific forks and official compatibility

Other domains are encouraged as **source-code forks**. The official app still
has mathematics-only collection gates. A fork-built network is eligible for an
official Release **only if this app can import it and use its FLIN associative
graph**; format checks and isolated pulse tests must pass. Incompatible forks
can distribute their networks via their own GitHub Releases, clearly marking
the required fork/version, or propose a schema adapter. This policy makes the
available snapshots genuinely reusable rather than merely downloadable.

## E. Downloading and importing

Open the [Releases page](https://github.com/jjy246/FLIN-Research-Desktop/releases), select a named memory-network release and download the `.sqlite3` file from **Assets**. In the app select **Manage Networks → Import SQLite**, choose the downloaded snapshot, name it, and switch to the imported independent network. Alternatively:

```bash
python3 flin_desktop.py --import-network /path/to/association.sqlite3 --network-name "Community FLIN network"
```

This imports a new separate database; do not replace files in the live data directory. Treat imported memories, papers and associations as experimental research content, not certified knowledge.

## Legal and technical limits

* The **FLIN source code** is Apache-2.0 licensed; **SQLite network snapshots are separately licensed research data**. A review checkbox can authorize publication of a specific submitted snapshot, but cannot override third-party publisher rights or privacy rights.
* FLIN SQLite snapshots can include papers, abstracts, quotations, citations, questions, and provenance. Check all materials and permissions before publication.
* `PRAGMA quick_check` and table checks are not a security audit or validation of the FLIN theory. Review in isolation when handling untrusted user-provided databases.
* Each released snapshot is an independent downloadable asset. GitHub does not automatically update a downloader's local network when new assets are released.
