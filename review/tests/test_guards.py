from review.guards import guarded_paths


def test_workflows_and_codeowners_are_guarded():
    paths = [".github/workflows/ci.yml", ".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
    assert guarded_paths(paths, "homelab") == paths


def test_claude_config_is_guarded_anywhere():
    paths = [".claude/settings.json", "app/.claude/hooks.json", "CLAUDE.md", "app/AGENTS.md", ".mcp.json"]
    assert guarded_paths(paths, "homelab") == paths


def test_dependency_manifests_and_lockfiles_are_guarded_by_name():
    paths = ["package.json", "web/pnpm-lock.yaml", "requirements-dev.txt", "go.sum", "infra/.terraform.lock.hcl"]
    assert guarded_paths(paths, "homelab") == paths


def test_ordinary_files_are_not_guarded():
    assert guarded_paths(["src/blocker.py", "README.md", "docs/locking.md"], "homelab") == []


def test_registry_pipeline_is_guarded_but_data_is_not():
    paths = ["modules/github-repo/main.tf", "scripts/x.py", "data/github/repos/fleet.yaml"]
    assert guarded_paths(paths, "registry") == ["modules/github-repo/main.tf", "scripts/x.py"]


def test_everything_in_the_dot_github_repo_is_guarded():
    assert guarded_paths(["review/REVIEW.md", "CONTRIBUTING.md"], ".github") == ["review/REVIEW.md", "CONTRIBUTING.md"]


def test_renamed_from_guarded_path_is_guarded():
    # prep passes both the new and the previous path of a renamed file
    assert guarded_paths(["docs/x.yml", ".github/workflows/x.yml"], "homelab") == [".github/workflows/x.yml"]
