import json

from review.decide import Review
from review.post import load_verdict, review_request


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
