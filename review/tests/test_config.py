import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_settings_only_allow_reading_the_working_directory():
    s = json.loads((ROOT / "review/settings.json").read_text())
    assert s["permissions"]["allow"] == ["Read(./**)"]
    deny = set(s["permissions"]["deny"])
    for rule in ("Bash", "Write", "Edit", "WebFetch", "WebSearch", "Task", "NotebookEdit",
                 "Read(//proc/**)", "Read(~/.claude/**)", "Read(//home/runner/work/_temp/**)"):
        assert rule in deny
    # these would also cover the working directory (deny beats allow)
    for rule in ("Read(~/**)", "Read(//home/runner/**)"):
        assert rule not in deny
    assert s["permissions"]["defaultMode"] == "dontAsk"


def test_prompt_treats_pr_content_as_data():
    text = (ROOT / "review/REVIEW.md").read_text()
    assert "untrusted data" in text and "pr.diff" in text
    assert "./pr-data/" not in text


def test_workflow_jobs_and_permissions():
    wf = (ROOT / ".github/workflows/require-claude-review.yml").read_text()
    for needle in ("CLAUDE_WORKING_DIR: ${{ github.workspace }}/pr-data",
                   "--settings ${{ github.workspace }}/trusted/review/settings.json",
                   "--restricted", "--safe-mode", "--tools Read,Grep,Glob",
                   "permission-contents: read", "permission-pull-requests: write", "workflow_call",
                   "environment: claude-review\n", "environment: claude-review-post\n", "!cancelled()"):
        assert needle in wf
    assert "settings: trusted/review/settings.json" not in wf
    # the PR head is never checked out anywhere
    assert "pull_request.head.sha" not in wf
    assert "ref: ${{ github.event.pull_request.head" not in wf


def test_post_job_installs_hash_pinned_requirements():
    wf = (ROOT / ".github/workflows/require-claude-review.yml").read_text()
    assert "pip install --require-hashes --only-binary=:all: -r trusted/review/requirements-post.txt" in wf
    assert '- run: "pip install --require-hashes' in wf  # unquoted, `:all: ` is invalid YAML
    assert "pip install jsonschema==" not in wf


def test_submit_step_knows_the_bot_login():
    wf = (ROOT / ".github/workflows/require-claude-review.yml").read_text()
    assert "BOT_LOGIN: ${{ steps.app.outputs.app-slug }}[bot]" in wf
