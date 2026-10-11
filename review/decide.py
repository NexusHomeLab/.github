"""Turn Claude's verdict into one GitHub review. Plain code: Claude can't override these rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from review.model import Review  # noqa: F401  (re-exported)

SCHEMA = json.loads((Path(__file__).parent / "verdict.schema.json").read_text())
MAX_LINES = 400
MAX_FILES = 15
SECRET_PATTERNS = [
    re.compile(p)
    for p in (
        r"sk-ant-[A-Za-z0-9_-]{10,}",
        r"gh[pousr]_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"-----BEGIN [A-Z0-9 ]+-----",
        r"AKIA[0-9A-Z]{16}",
        r"(?i)aws.{0,20}?['\"=: ]+[A-Za-z0-9/+=]{40}",
        r"xox[abprs]-[A-Za-z0-9-]{10,}",
        r"AIza[0-9A-Za-z_-]{35}",
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}",
        r"\bsk-[A-Za-z0-9_-]{20,}",
        r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}",
    )
]
FOOTER = "\n\n---\n_Automated review by nexus-claude-reviewer (mode `{mode}`)._"


@dataclass
class Facts:
    head_sha: str
    guarded: list[str]
    lines_changed: int
    files_changed: int
    diff_available: bool
    skipped: list[str]
    long_lines: bool


def validate(verdict: object) -> list[str]:
    return sorted(e.message for e in Draft202012Validator(SCHEMA).iter_errors(verdict))


def find_secrets(text: str) -> list[str]:
    return [p.pattern for p in SECRET_PATTERNS if p.search(text)]


def diff_lines(diff: str) -> dict[str, set[int]]:
    """Line numbers on the new side of the diff, per file: the only lines GitHub accepts inline comments on."""
    lines: dict[str, set[int]] = {}
    path, new_line = None, 0
    for raw in diff.split("\n"):
        if raw.startswith("+++ "):
            target = raw[4:]
            path = target[2:] if target.startswith("b/") else None
        elif raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            new_line = int(match.group(1)) if match else 0
        elif path and raw.startswith("+"):
            lines.setdefault(path, set()).add(new_line)
            new_line += 1
        elif path and raw.startswith(" "):
            lines.setdefault(path, set()).add(new_line)
            new_line += 1
    return lines


def _comment(mode: str, text: str) -> Review:
    return Review("COMMENT", text + FOOTER.format(mode=mode))


def decide(verdict, facts: Facts, mode: str, review_ok: bool, current_head: str, diff: str):
    if mode == "off" or current_head != facts.head_sha:
        return None
    if verdict is None or not review_ok:
        return _comment(mode, "Claude review didn't finish (error, timeout or turn limit). Not approving.")
    if validate(verdict):
        return _comment(mode, "Claude review output was invalid. Not approving.")
    withheld = "Claude review withheld: its output looked like it contained a secret. Not approving."

    blocking = [f for f in verdict["findings"] if f["severity"] == "blocking"]
    reasons = []
    if verdict["verdict"] != "approve":
        reasons.append(f"Claude's verdict is `{verdict['verdict']}`")
    if not verdict["complete"]:
        reasons.append("Claude marked the review incomplete")
    if blocking:
        reasons.append(f"{len(blocking)} blocking finding(s)")
    if facts.guarded:
        shown = ", ".join(f"`{p}`" for p in facts.guarded[:10])
        reasons.append(f"touches guarded path(s) {shown}; needs the owner")
    if facts.lines_changed > MAX_LINES or facts.files_changed > MAX_FILES:
        reasons.append(
            f"too large to approve ({facts.lines_changed} lines, {facts.files_changed} files; "
            f"limit {MAX_LINES} lines, {MAX_FILES} files)"
        )
    if not facts.diff_available:
        reasons.append("the diff couldn't be fetched")
    if facts.skipped:
        shown = ", ".join(f"`{p}`" for p in facts.skipped[:10])
        reasons.append(f"{len(facts.skipped)} file(s) not shown to Claude (binary, too large or unavailable): {shown}")
    if facts.long_lines:
        reasons.append("a changed line is longer than 2000 characters")

    if mode == "approve" and not reasons:
        event = "APPROVE"
    elif mode == "approve" and blocking:
        event = "REQUEST_CHANGES"
    else:
        event = "COMMENT"

    on_diff = diff_lines(diff)
    comments, elsewhere = [], []
    for f in verdict["findings"]:
        text = f"**{f['severity']}**: {f['body']}"
        line = int(f["line"])
        if line in on_diff.get(f["path"], set()):
            comments.append({"path": f["path"], "line": line, "side": "RIGHT", "body": text})
        else:
            elsewhere.append(f"- `{f['path']}:{line}` {text}")

    body = ["## Claude review", "", verdict["summary"]]
    if elsewhere:
        body += ["", "### Findings outside the diff", *elsewhere]
    if mode == "approve" and reasons:
        body += ["", "**Not approving:** " + "; ".join(reasons) + "."]
    text = "\n".join(body)

    # Scan exactly what would be posted, not the raw verdict.
    if find_secrets(text) or any(find_secrets(c["body"]) for c in comments):
        return _comment(mode, withheld)
    return Review(event, text + FOOTER.format(mode=mode), comments)
