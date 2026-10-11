"""Post the Claude review. `decide` runs with a read-only token; `submit` with the App token."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from review.model import Review

API = "https://api.github.com"


def _api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"{}")


def load_verdict(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def review_request(review: Review, head_sha: str) -> dict:
    return {"commit_id": head_sha, "event": review.event, "body": review.body, "comments": review.comments}


def stale_change_requests(reviews: list[dict], bot_login: str) -> list[int]:
    """GitHub keeps CHANGES_REQUESTED until dismissed; later COMMENT reviews don't clear it."""
    return [r["id"] for r in reviews if r["state"] == "CHANGES_REQUESTED" and r["user"]["login"] == bot_login]


def fold_comments_into_body(review: Review) -> Review:
    lines = [f"- `{c['path']}:{c['line']}` {c['body']}" for c in review.comments]
    body = review.body + "\n\n### Findings (inline comments rejected by GitHub)\n" + "\n".join(lines)
    return Review(review.event, body, [])


def cmd_decide(args) -> int:
    from review.decide import Facts, decide  # lazy: pulls in jsonschema, which submit must not load

    repo, number = os.environ["REPO"], os.environ["PR_NUMBER"]
    data = Path(args.data)
    facts = Facts(**json.loads((data / "facts.json").read_text()))
    current = _api("GET", f"/repos/{repo}/pulls/{number}")["head"]["sha"]
    review = decide(
        load_verdict(Path(args.verdict)), facts, os.environ["MODE"],
        os.environ["REVIEW_OK"] == "true", current, (data / "pr.diff").read_text(),
    )
    if review is None:
        print("Nothing to post (mode off, or the PR moved on since prep).")
        return 0
    Path(args.out).write_text(json.dumps({"head_sha": facts.head_sha, **asdict(review)}))
    print(f"Decided: {review.event}")
    return 0


def cmd_submit(args) -> int:
    path = Path(args.review)
    if not path.exists():
        return 0
    saved = json.loads(path.read_text())
    head = saved.pop("head_sha")
    review = Review(**saved)
    repo, number = os.environ["REPO"], os.environ["PR_NUMBER"]
    base = f"/repos/{repo}/pulls/{number}"
    if review.event != "REQUEST_CHANGES":
        for stale in stale_change_requests(_api("GET", f"{base}/reviews?per_page=100"), os.environ["BOT_LOGIN"]):
            _api("PUT", f"{base}/reviews/{stale}/dismissals",
                 {"message": "Superseded by a newer Claude review.", "event": "DISMISS"})
    try:
        _api("POST", f"{base}/reviews", review_request(review, head))
    except urllib.error.HTTPError as err:
        if err.code != 422 or not review.comments:
            raise
        # An inline comment GitHub rejects (e.g. a line outside the diff): keep the findings in the body.
        print("Inline comments rejected; posting them in the summary.", file=sys.stderr)
        _api("POST", f"{base}/reviews", review_request(fold_comments_into_body(review), head))
    print(f"Posted {review.event}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--data", required=True)
    d.add_argument("--verdict", required=True)
    d.add_argument("--out", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--review", required=True)
    args = parser.parse_args(argv)
    return cmd_decide(args) if args.cmd == "decide" else cmd_submit(args)


if __name__ == "__main__":
    raise SystemExit(main())
