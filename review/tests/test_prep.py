from review.prep import MAX_FILE_BYTES, build_files_txt, make_facts

PR = {"head": {"sha": "c" * 40}, "additions": 10, "deletions": 2, "changed_files": 2}
FILES = [
    {"filename": "src/a.py", "status": "modified"},
    {"filename": "docs/x.yml", "status": "renamed", "previous_filename": ".github/workflows/x.yml"},
]


def test_make_facts():
    assert make_facts(PR, FILES, "NexusHomeLab/homelab", True) == {
        "head_sha": "c" * 40,
        "guarded": [".github/workflows/x.yml"],
        "lines_changed": 12,
        "files_changed": 2,
        "diff_available": True,
    }


def test_make_facts_without_diff():
    assert make_facts(PR, FILES, "NexusHomeLab/homelab", False)["diff_available"] is False


def test_files_txt_has_headers_and_text():
    out = build_files_txt([("src/a.py", b"print(1)\n")])
    assert out == "===== src/a.py =====\nprint(1)\n\n"


def test_files_txt_skips_binary_and_large():
    out = build_files_txt([("img.png", b"\x89PNG\x00\xff"), ("big.txt", b"x" * (MAX_FILE_BYTES + 1)), ("gone.py", None)])
    assert "===== img.png (skipped: binary) =====" in out
    assert "===== big.txt (skipped: larger than 200 KB) =====" in out
    assert "===== gone.py (skipped: deleted or unavailable) =====" in out
    assert "PNG" not in out and "xxxx" not in out
