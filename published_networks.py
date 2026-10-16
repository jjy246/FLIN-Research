"""Discover and download reviewed FLIN SQLite snapshots from GitHub Releases.

Only published release assets in the project's own repository are listed. This
module does not grant contributors release permissions or certify their data.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from pathlib import Path

import requests

REPOSITORY = "jjy246/FLIN-Research-Desktop"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
MAX_SNAPSHOT_BYTES = 2 * 1024 ** 3 - 1  # GitHub's per-release-asset limit.
USER_AGENT = "FLIN-Research-Desktop/17 (+https://github.com/jjy246/FLIN-Research-Desktop)"
# Known GitHub-controlled download/CDN hosts (never follow arbitrary redirects).
DOWNLOAD_HOSTS = frozenset({"github.com", "release-assets.githubusercontent.com",
                            "objects.githubusercontent.com", "objects-origin.githubusercontent.com"})
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}


class PublishedNetworkCancelled(Exception):
    """A user cancelled network discovery or download."""


def list_published_networks(session=None, *, max_pages=3, stop_event=None):
    """Return usable SQLite assets from published GitHub Releases only.

    Each item includes release name/tag, size, SHA256 if supplied by GitHub,
    and a verified release download URL. No GitHub login is needed for public
    releases. No data is written to disk while listing.
    """
    http = session or requests
    results = []
    for page in range(1, max(1, max_pages) + 1):
        if stop_event is not None and stop_event.is_set():
            raise PublishedNetworkCancelled("Network listing cancelled.")
        response = http.get(API_URL, params={"per_page": 100, "page": page},
                            headers=HEADERS, timeout=(8, 25))
        response.raise_for_status()
        releases = response.json()
        if not isinstance(releases, list):
            raise ValueError("GitHub returned an unexpected releases response.")
        for release in releases:
            if not isinstance(release, dict) or release.get("draft"):
                continue
            tag = str(release.get("tag_name") or "")
            for asset in release.get("assets") or []:
                if not isinstance(asset, dict):
                    continue
                name = str(asset.get("name") or "")
                if not name.lower().endswith(".sqlite3") or asset.get("state") not in (None, "uploaded"):
                    continue
                try:
                    size = int(asset.get("size") or 0)
                    asset_id = int(asset["id"])
                except (TypeError, ValueError, KeyError):
                    continue
                if not 16 <= size <= MAX_SNAPSHOT_BYTES or asset_id <= 0:
                    continue
                url = str(asset.get("browser_download_url") or "")
                parts = urllib.parse.urlsplit(url)
                if (parts.scheme != "https" or parts.netloc != "github.com" or
                    not parts.path.startswith(f"/{REPOSITORY}/releases/download/")):
                    continue
                digest = str(asset.get("digest") or "").lower()
                if digest and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                    # Older GitHub responses can omit a digest; if supplied,
                    # require the documented SHA-256 form before proceeding.
                    continue
                results.append({
                    "id": asset_id,
                    "title": str(release.get("name") or tag or "FLIN network")[:180],
                    "tag": tag,
                    "filename": name,
                    "size": size,
                    "url": url,
                    "digest": digest,
                    "published_at": str(release.get("published_at") or ""),
                    "release_url": str(release.get("html_url") or RELEASES_URL),
                    "author": str((release.get("author") or {}).get("login") or ""),
                })
        if len(releases) < 100:
            break
    return results


def download_published_network(asset, destination, *, session=None, stop_event=None,
                               progress=None):
    """Stream an asset to a temporary path and verify its size and SHA-256.

    The caller must use an *isolated*, new temporary path and later invoke the
    app's normal schema-checked import. A partial download is always removed.
    """
    url = str(asset["url"])
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or
            not parsed.path.startswith(f"/{REPOSITORY}/releases/download/")):
        raise ValueError("This asset is not a release download from the official FLIN repository.")
    expected_size = int(asset["size"])
    if not 16 <= expected_size <= MAX_SNAPSHOT_BYTES:
        raise ValueError("Invalid or oversized network asset.")
    digest = str(asset.get("digest") or "").lower()
    if digest and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Malformed asset digest.")
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing file.")
    http = session or requests
    written = 0
    sha = hashlib.sha256()
    try:
        # Follow only HTTPS redirects within GitHub's release-asset hosts.
        # Checking response.url after automatic redirects is too late to
        # prevent a request to an unexpected destination.
        for _ in range(7):
            if stop_event is not None and stop_event.is_set():
                raise PublishedNetworkCancelled("Network download cancelled.")
            with http.get(url, headers={"User-Agent": USER_AGENT},
                          timeout=(8, 40), stream=True, allow_redirects=False) as response:
                status = response.status_code
                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    url = urllib.parse.urljoin(url, location)
                    redirect = urllib.parse.urlsplit(url)
                    if redirect.scheme != "https" or redirect.netloc not in DOWNLOAD_HOSTS:
                        raise ValueError("GitHub asset download redirected outside trusted HTTPS hosts.")
                    continue
                response.raise_for_status()
                with destination.open("xb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if stop_event is not None and stop_event.is_set():
                            raise PublishedNetworkCancelled("Network download cancelled.")
                        if not chunk:
                            continue
                        written += len(chunk)
                        if written > expected_size or written > MAX_SNAPSHOT_BYTES:
                            raise ValueError("Download exceeded the size declared by GitHub.")
                        sha.update(chunk)
                        output.write(chunk)
                        if progress:
                            progress(written, expected_size)
                break
        else:
            raise ValueError("Too many redirects while downloading GitHub Release asset.")
        if written != expected_size:
            raise ValueError(f"Incomplete download: {written:,}/{expected_size:,} bytes.")
        if digest and sha.hexdigest() != digest.split(":", 1)[1]:
            raise ValueError("Downloaded file failed GitHub SHA-256 verification.")
        with destination.open("rb") as src:
            if src.read(16) != b"SQLite format 3\x00":
                raise ValueError("Downloaded asset is not a SQLite database.")
        return {"bytes": written, "sha256": sha.hexdigest()}
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
