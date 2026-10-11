import json

from review.model import Review
from review.post import fold_comments_into_body, load_verdict, review_request, stale_change_requests


def test_review_request_pins_the_reviewed_commit():
    r = Review("APPROVE", "ok", [{"path": "a.py", "line": 1, "side": "RIGHT", "body": "x"}])
    assert review_request(r, "d" * 40) == {
        "commit_id": "d" * 40, "event": "APPROVE", "body": "ok",
        "comments": [{"path": "a.py", "line": 1, "side": "RIGHT", "body": "x"}],
    }


def test_load_verdict_missing_or_unparseable_is_none(tmp_path):
    assert load_verdict(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_verdict(bad) is None
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"verdict": "approve"}))
    assert load_verdict(good) == {"verdict": "approve"}


def test_submit_path_does_not_import_jsonschema():
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    code = "import sys, review.post; assert 'jsonschema' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], cwd=root, check=True)


def test_stale_change_requests_only_the_bots_changes_requested():
    reviews = [
        {"id": 1, "state": "CHANGES_REQUESTED", "user": {"login": "bot[x]"}},
        {"id": 2, "state": "APPROVED", "user": {"login": "bot[x]"}},
        {"id": 3, "state": "COMMENTED", "user": {"login": "bot[x]"}},
        {"id": 4, "state": "DISMISSED", "user": {"login": "bot[x]"}},
        {"id": 5, "state": "CHANGES_REQUESTED", "user": {"login": "human"}},
        {"id": 6, "state": "CHANGES_REQUESTED", "user": {"login": "bot[x]"}},
    ]
    assert stale_change_requests(reviews, "bot[x]") == [1, 6]


def test_fold_comments_into_body():
    r = Review("COMMENT", "body", [
        {"path": "a.py", "line": 3, "side": "RIGHT", "body": "**suggestion**: x"},
        {"path": "b.py", "line": 9, "side": "RIGHT", "body": "**blocking**: y"},
    ])
    out = fold_comments_into_body(r)
    assert out.event == "COMMENT" and out.comments == []
    assert out.body.startswith("body")
    assert "### Findings (inline comments rejected by GitHub)" in out.body
    assert "- `a.py:3` **suggestion**: x" in out.body and "- `b.py:9` **blocking**: y" in out.body
