# Maintainer checklist — launching the FLIN Community Network Hub

This guide configures GitHub's **website settings**. Adding YAML files to the repository does not automatically enable Discussions or create its categories. The public GitHub UI cannot be changed solely by publishing README files.

## 0. Prepare and upload the new repository files

If the official repository already exists, copy the files from this distribution into your checkout, without copying an old `.git` folder. From its root:

```bash
git status --short
git add README.md CONTRIBUTING.md docs/COMMUNITY_HUB.md docs/COMMUNITY_NETWORKS.md docs/EXAMPLE_NETWORK_SHOWCASE.md docs/COMMUNITY_WELCOME_POST.md docs/MAINTAINER_HUB_SETUP.md docs/OPEN_SOURCE_LAUNCH.md .github/DISCUSSION_TEMPLATE/
git diff --cached --check
git commit -m 'Launch FLIN community network sharing hub'
git push origin main
```

If you haven't created the repository yet, follow [OPEN_SOURCE_LAUNCH.md](OPEN_SOURCE_LAUNCH.md), then complete the remaining steps here. Do **not** run `gh repo create` again on an existing repository.

## 1. Enable GitHub Discussions

1. Open <https://github.com/jjy246/FLIN-Research-Desktop> while signed into the owner account.
2. Select **Settings → General → Features**.
3. Find **Discussions**; click **Set up discussions** or enable it (wording may change).
4. Paste the contents of [COMMUNITY_WELCOME_POST.md](COMMUNITY_WELCOME_POST.md) as your welcome message, or create a new announcement with that content after enabling Discussions.
5. Click **Start discussion** / save the settings.
6. Verify that the top navigation now displays a **Discussions** tab. Open <https://github.com/jjy246/FLIN-Research-Desktop/discussions>.

See [GitHub's enable Discussions documentation](https://docs.github.com/en/discussions/quickstart).

## 2. Create the six categories (manual GitHub UI action)

1. In **Discussions**, find the **Categories** header in the left sidebar, click its **edit/pencil icon**, and choose **New category**.
2. Create each category exactly as listed here. Use the described format. **Category names determine slugs** and must match the YAML filenames in `.github/DISCUSSION_TEMPLATE/`.

| Exact category title | Suggested emoji | Format | Description | Expected slug / file |
| --- | --- | --- | --- | --- |
| Network Showcase | 🧠 | Open-ended discussion | Share, download and discuss FLIN memory networks hosted by their authors. | `network-showcase.yml` |
| Research & Experiments | 🔬 | Open-ended discussion | Measurements, reproductions, experiments, limitations and negative findings. | `research-experiments.yml` |
| Ideas & Theories | 💡 | Open-ended discussion | Assumptions, questions and proposed theoretical mechanisms. | `ideas-theories.yml` |
| Domain Extensions | 🛠️ | Open-ended discussion | Forks and changes for non-mathematics knowledge domains. | `domain-extensions.yml` |
| Help & Questions | ❓ | Question and answer | Installation, import, data compatibility and usage support. | `help-questions.yml` |
| Official Announcements | 📢 | Announcement | Maintainer-only news and release notices. | no form required |

3. After creating each category, **check its actual slug in GitHub**. If a generated slug differs (for example due to an existing category with that name), rename the matching YAML file to `<actual-slug>.yml`. Merely adding YAML **does not create categories**. Existing default categories can be retained, renamed or removed to avoid duplicates.
4. Open **Discussions → New discussion**; select **Network Showcase** and check that its structured form appears. It should ask for a download URL and SHA-256. If not, inspect the category slug and `.github/DISCUSSION_TEMPLATE/network-showcase.yml`.

Docs: [category management](https://docs.github.com/en/discussions/managing-discussions-for-your-community/managing-categories-for-discussions) and [category forms](https://docs.github.com/en/discussions/managing-discussions-for-your-community/creating-discussion-category-forms).

## 3. Pin the welcome and post the first Showcase example

1. Open the welcome Discussion; in its right sidebar choose **Pin discussion** (or **Pin discussion to category**).
2. Publish a new **Network Showcase** post for your **actual** `v1.sqlite3`. Fill in real node counts, source descriptions, SHA-256, direct Release URL and FLIN compatibility; do **not** claim results that have not been measured.
3. Link the corresponding published `network-v1` Release. If it hasn't been published, first use the official [publication guide](COMMUNITY_NETWORKS.md) to upload a consistent SQLite export.
4. Check the Download button/URL in a signed-out browser window. Download the file and try importing it into a **new** FLIN network.

## 4. Moderate independently shared content

1. Users publish public SQLite download links in **Network Showcase** without prior approval; they retain control of their own storage and data licensing.
2. Keep **Issues** enabled for bug reports and official [Network Submission](https://github.com/jjy246/FLIN-Research-Desktop/issues/new?template=network_submission.yml) requests.
3. To publish a community file in **official Releases**, verify the submission URL, claimed SHA-256, source permissions, absence of sensitive data, SQLite structural health and actual import usability in an isolated test. Check compatibility with the reference app; domain-specific incompatible Forks can remain in Discussions and their authors' Releases.
4. Only repository maintainers create official Release assets. Cite the original creator, Issue and SHA-256. Always retain a link to the author's Showcase discussion.
5. For rule-breaking or suspicious submissions, use GitHub's moderation controls and [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md). A shared or approved file is **not** peer-reviewed or guaranteed safe.

## 5. Make sure newcomer routes are clear

- README links to **Discussions** for community-sharing and **Releases** for official downloads.
- CONTRIBUTING points to Network Showcase for immediate sharing and Issues for optional official review.
- Each official network Release says what version of FLIN it imports into and includes the author's attribution and data license.
- Revisit broken links and old network formats periodically.

## 6. First-launch checklist

- [ ] Source repository remains the official mathematics-specific FLIN baseline; main program unchanged.
- [ ] Commit all Hub documentation and `.github/DISCUSSION_TEMPLATE/*.yml`.
- [ ] Discussions enabled from Settings.
- [ ] All six categories exist; no duplicates cause slug conflicts.
- [ ] Network Showcase form works and asks for compatibility and provenance.
- [ ] Welcome announcement published and pinned.
- [ ] `network-v1` Release has an actual working `.sqlite3` attachment (if ready).
- [ ] Your first Showcase discussion links to the working Release and lists the correct checksum.
- [ ] Newcomer can download and **import** a trusted reference snapshot into an independent local FLIN network.
- [ ] Issue submission process still works for contributors requesting official publication.
- [ ] Public links and moderation policies are accessible without admin login.
