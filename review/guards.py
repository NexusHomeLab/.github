"""Paths only the owner may approve. A PR touching any of them never gets the bot's approval."""

from __future__ import annotations

from fnmatch import fnmatchcase

# Matched against the file name, anywhere in the repo.
NAMES = [
    "CODEOWNERS", "CLAUDE.md", "AGENTS.md", ".mcp.json", ".gitleaks*",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb",
    "requirements*.txt", "pyproject.toml", "uv.lock", "poetry.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock",
    ".terraform.lock.hcl",
]

# Path prefixes guarded per repo ("" guards everything).
REPO_PREFIXES = {
    "registry": ("scripts/", "schemas/", "modules/", "stacks/", "bootstrap/"),
    ".github": ("",),
}


def _is_guarded(path: str, repo: str) -> bool:
    parts = path.split("/")
    if path.startswith(".github/") or ".claude" in parts[:-1]:
        return True
    if any(fnmatchcase(parts[-1], pattern) for pattern in NAMES):
        return True
    return any(path.startswith(prefix) for prefix in REPO_PREFIXES.get(repo, ()))


def guarded_paths(paths: list[str], repo: str) -> list[str]:
    return [p for p in paths if _is_guarded(p, repo)]
