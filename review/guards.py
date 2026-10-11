"""Paths only the owner may approve. A PR touching any of them never gets the bot's approval."""

from __future__ import annotations

from fnmatch import fnmatchcase

# Matched against the file name, anywhere in the repo.
NAMES = [
    "CODEOWNERS", "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude.json", ".mcp.json", ".gitleaks*",
    ".gitmodules", "Dockerfile*", "Makefile", ".npmrc", ".yarnrc*", ".pre-commit-config.yaml",
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
    "bun.lock", "bun.lockb",
    "requirements*.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock",
    "uv.lock", "poetry.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock",
    "composer.json", "composer.lock", "pom.xml", "build.gradle*", "*.csproj",
    ".terraform.lock.hcl",
]

# Directories guarded anywhere in the path (as a non-final component).
GUARDED_DIRS = {".github", ".claude", ".husky", ".devcontainer"}

# Path prefixes guarded per repo ("" guards everything).
REPO_PREFIXES = {
    "registry": ("scripts/", "schemas/", "modules/", "stacks/", "bootstrap/"),
    ".github": ("",),
}


def _normalise(path: str) -> str:
    path = path.lstrip("/")
    while path.startswith("./"):
        path = path[2:]
    return path


def _is_guarded(path: str, repo: str) -> bool:
    path = _normalise(path)
    parts = path.split("/")
    if any(p in GUARDED_DIRS for p in parts[:-1]):
        return True
    if any(fnmatchcase(parts[-1], pattern) for pattern in NAMES):
        return True
    return any(path.startswith(prefix) for prefix in REPO_PREFIXES.get(repo, ()))


def guarded_paths(paths: list[str], repo: str) -> list[str]:
    return [p for p in paths if _is_guarded(p, repo)]
