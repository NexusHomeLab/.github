import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_settings_only_allow_reading_the_data_folder():
    s = json.loads((ROOT / "review/settings.json").read_text())
    assert s["permissions"]["allow"] == ["Read(./pr-data/**)"]
    deny = set(s["permissions"]["deny"])
    for rule in ("Bash", "Write", "Edit", "WebFetch", "WebSearch", "Task", "NotebookEdit",
                 "Read(//proc/**)", "Read(//home/runner/**)", "Read(//tmp/**)", "Read(./trusted/**)"):
        assert rule in deny
    assert s["permissions"]["defaultMode"] == "dontAsk"


def test_prompt_treats_pr_content_as_data():
    text = (ROOT / "review/REVIEW.md").read_text()
    assert "untrusted data" in text and "./pr-data/" in text


def test_workflow_jobs_and_permissions():
    wf = (ROOT / ".github/workflows/require-claude-review.yml").read_text()
    for needle in ("environment: claude-review\n", "environment: claude-review-post\n",
                   "--restricted", "--safe-mode", "--tools Read,Grep,Glob", "permission-contents: read",
                   "permission-pull-requests: write", "workflow_call"):
        assert needle in wf
    assert "github.event.pull_request.head.sha" not in wf.split("review:")[1].split("post:")[0]
