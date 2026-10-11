from review.decide import Facts, decide, diff_lines, find_secrets, validate

HEAD = "a" * 40
DIFF = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 import os
-x = 1
+x = 2
+y = 3
 print(x)
"""


def facts(**kw):
    base = dict(head_sha=HEAD, guarded=[], lines_changed=3, files_changed=1, diff_available=True)
    return Facts(**{**base, **kw})


def verdict(v="approve", findings=None, complete=True, summary="Looks correct."):
    return {"verdict": v, "summary": summary, "complete": complete, "findings": findings or []}


def finding(severity="suggestion", line=2, path="src/app.py", body="Consider a constant."):
    return {"path": path, "line": line, "severity": severity, "body": body}


def run(v=None, f=None, mode="approve", ok=True, head=HEAD, diff=DIFF):
    return decide(verdict() if v is None else v, f or facts(), mode, ok, head, diff)


def test_diff_lines_maps_new_side_lines():
    assert diff_lines(DIFF) == {"src/app.py": {1, 2, 3, 4}}


def test_diff_lines_empty():
    assert diff_lines("") == {}


def test_validate_accepts_good_and_rejects_bad():
    assert validate(verdict()) == []
    assert validate({"verdict": "lgtm"}) != []


def test_find_secrets():
    assert find_secrets("token ghp_" + "A" * 36) != []
    assert find_secrets("-----BEGIN RSA PRIVATE KEY-----") != []
    assert find_secrets("sk-ant-oat01-" + "x" * 20) != []
    assert find_secrets("no secrets here") == []


def test_approves_clean_small_review():
    r = run()
    assert r.event == "APPROVE"
    assert "Looks correct." in r.body


def test_blocking_finding_requests_changes_with_inline_comment():
    r = run(verdict("request_changes", [finding("blocking")]))
    assert r.event == "REQUEST_CHANGES"
    assert r.comments == [{"path": "src/app.py", "line": 2, "side": "RIGHT", "body": "**blocking**: Consider a constant."}]


def test_guarded_path_blocks_approval_and_says_why():
    r = run(f=facts(guarded=[".github/workflows/x.yml"]))
    assert r.event == "COMMENT"
    assert "`.github/workflows/x.yml`" in r.body and "needs the owner" in r.body


def test_size_cap_blocks_approval():
    assert run(f=facts(lines_changed=401)).event == "COMMENT"
    assert run(f=facts(files_changed=16)).event == "COMMENT"
    assert run(f=facts(lines_changed=400, files_changed=15)).event == "APPROVE"


def test_unavailable_diff_blocks_approval():
    r = run(f=facts(diff_available=False), diff="")
    assert r.event == "COMMENT" and "diff couldn't be fetched" in r.body


def test_incomplete_or_failed_review_never_approves():
    assert run(verdict(complete=False)).event == "COMMENT"
    r = run(ok=False)
    assert r.event == "COMMENT" and "didn't finish" in r.body
    assert run(v=None, ok=True).event == "APPROVE"  # sanity: default verdict approves
    r = decide(None, facts(), "approve", True, HEAD, DIFF)
    assert r.event == "COMMENT" and "didn't finish" in r.body


def test_invalid_output_comments_only():
    r = run({"verdict": "approve"})
    assert r.event == "COMMENT" and "invalid" in r.body


def test_secret_in_summary_withholds_review():
    r = run(verdict(summary="env: ghp_" + "B" * 36))
    assert r.event == "COMMENT" and "withheld" in r.body
    assert "ghp_" not in r.body and r.comments == []


def test_secret_in_a_finding_withholds_review():
    r = run(verdict("comment", [finding(body="key -----BEGIN OPENSSH PRIVATE KEY-----")]))
    assert r.event == "COMMENT" and "withheld" in r.body and r.comments == []


def test_comment_mode_never_approves_or_requests_changes():
    assert run(mode="comment").event == "COMMENT"
    assert run(verdict("request_changes", [finding("blocking")]), mode="comment").event == "COMMENT"


def test_off_mode_and_moved_head_post_nothing():
    assert run(mode="off") is None
    assert run(head="b" * 40) is None


def test_findings_outside_diff_go_to_body():
    r = run(verdict("comment", [finding(line=99), finding(path="gone.py", line=1)]))
    assert r.comments == []
    assert "`src/app.py:99`" in r.body and "`gone.py:1`" in r.body
