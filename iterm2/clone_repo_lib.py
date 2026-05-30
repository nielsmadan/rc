"""Pure helpers for CloneRepoToTab.py — unit-testable outside iTerm2.

No iterm2 import: this module must stay importable in a plain Python
environment so its functions can be exercised by test_clone_repo_lib.py.
"""

import os
import re
import subprocess


_TRAILING_DIGITS = re.compile(r"(\d+)$")


def next_sibling_name(basename: str) -> str:
    """Deterministic next sibling name: increment the trailing digit run,
    or append '2' if there isn't one (e.g. `dev2` -> `dev3`, `rc` -> `rc2`).

    Does NOT skip existing siblings — the caller decides what to do based on
    whether the target already exists (clone into it vs. open it).
    """
    m = _TRAILING_DIGITS.search(basename)
    if m:
        return basename[: m.start()] + str(int(m.group()) + 1)
    return basename + "2"


def resolve_repo_root(path: str) -> "str | None":
    """Return the absolute repo root for `path`, or None if `path` isn't in a repo."""
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def resolve_origin_url(repo_root: str) -> "str | None":
    """Return the URL of the `origin` remote, or None if there isn't one."""
    result = subprocess.run(
        ["git", "-C", repo_root, "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def compute_destination(repo_root: str, name: str) -> str:
    """Where the new clone goes: sibling of `repo_root` named `name`."""
    return os.path.join(os.path.dirname(repo_root.rstrip("/")), name)


_ENV_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def find_env_files(repo_root: str) -> list:
    """Return relative paths of every `.env` file under `repo_root`.

    Walks the tree, pruning common bulky/irrelevant directories. Returned
    paths are POSIX-relative to `repo_root` (e.g. `".env"`, `"server/.env"`),
    sorted for stable output.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _ENV_SKIP_DIRS]
        if ".env" in filenames:
            rel = os.path.relpath(dirpath, repo_root)
            out.append(".env" if rel == "." else os.path.join(rel, ".env"))
    return sorted(out)
