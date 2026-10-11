"""Fetch a PR as flat data files for the review job.

Never checks out or runs PR content. File contents are concatenated into one text
file, so no PR-supplied .claude/, CLAUDE.md, hook or skill exists on disk.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from review.guards import guarded_paths

API = "https://api.github.com"
MAX_FILE_BYTES = 200 * 1024
MAX_FILES_WITH_CONTENT = 50


def _get(path: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": accept,
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


MAX_LINE_CHARS = 2000


def _shown(content: bytes | None) -> bool:
    """Whether build_files_txt includes this content."""
    if content is None or len(content) > MAX_FILE_BYTES or b"\x00" in content:
        return False
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def skipped_paths(files: list[dict], entries: list[tuple[str, bytes | None]]) -> list[str]:
    """Changed (not deleted) files whose content Claude was not shown."""
    removed = {f["filename"] for f in files if f["status"] == "removed"}
    skipped = [path for path, content in entries if path not in removed and not _shown(content)]
    return skipped + [f["filename"] for f in files[len(entries):] if f["status"] != "removed"]


def make_facts(pr: dict, files: list[dict], repo: str, diff_available: bool, skipped: list[str], diff: str) -> dict:
    paths = [f["filename"] for f in files] + [f["previous_filename"] for f in files if f.get("previous_filename")]
    return {
        "head_sha": pr["head"]["sha"],
        "guarded": guarded_paths(paths, repo.split("/", 1)[1]),
        "lines_changed": pr["additions"] + pr["deletions"],
        "files_changed": pr["changed_files"],
        "diff_available": diff_available,
        "skipped": skipped,
        "long_lines": any(
            len(line) > MAX_LINE_CHARS + 1 for line in diff.split("\n")
            if line.startswith("+") and not line.startswith("+++ ")
        ),
    }


def build_files_txt(entries: list[tuple[str, bytes | None]]) -> str:
    out = []
    for path, content in entries:
        if content is None:
            out.append(f"===== {path} (skipped: deleted or unavailable) =====\n\n")
        elif len(content) > MAX_FILE_BYTES:
            out.append(f"===== {path} (skipped: larger than 200 KB) =====\n\n")
        elif b"\x00" in content:
            out.append(f"===== {path} (skipped: binary) =====\n\n")
        else:
            try:
                out.append(f"===== {path} =====\n{content.decode('utf-8')}\n")
            except UnicodeDecodeError:
                out.append(f"===== {path} (skipped: binary) =====\n\n")
    return "".join(out)


def _content(repo: str, path: str, ref: str) -> bytes | None:
    try:
        meta = json.loads(_get(f"/repos/{repo}/contents/{urllib.parse.quote(path)}?ref={ref}"))
    except urllib.error.HTTPError:
        return None
    if meta.get("type") != "file" or meta.get("encoding") != "base64":
        return None
    return base64.b64decode(meta["content"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    repo, number = os.environ["REPO"], os.environ["PR_NUMBER"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pr = json.loads(_get(f"/repos/{repo}/pulls/{number}"))
    files: list[dict] = []
    for page in range(1, 31):  # GitHub caps the list at 3000 files
        batch = json.loads(_get(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}"))
        files += batch
        if len(batch) < 100:
            break
    try:
        diff = _get(f"/repos/{repo}/pulls/{number}", accept="application/vnd.github.diff").decode("utf-8", "replace")
        diff_available = True
    except urllib.error.HTTPError:  # 406/422: diff too large
        diff, diff_available = "", False

    head = pr["head"]["sha"]
    entries = [
        (f["filename"], None if f["status"] == "removed" else _content(repo, f["filename"], head))
        for f in files[:MAX_FILES_WITH_CONTENT]
    ]
    (out / "pr.json").write_text(json.dumps({
        "number": pr["number"], "title": pr["title"], "body": pr.get("body") or "",
        "author": pr["user"]["login"], "base": pr["base"]["ref"], "head_sha": head,
        "files": [f["filename"] for f in files],
    }, indent=2))
    (out / "pr.diff").write_text(diff)
    (out / "files.txt").write_text(build_files_txt(entries))
    (out / "facts.json").write_text(json.dumps(make_facts(pr, files, repo, diff_available, skipped_paths(files, entries), diff), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
