"""Pure helpers for CloneRepoToTab.py — unit-testable outside iTerm2.

No iterm2 import: this module must stay importable in a plain Python
environment so its functions can be exercised by test_clone_repo_lib.py.
"""

import os
import re
import subprocess


_TRAILING_DIGITS = re.compile(r"(\d+)$")


def _increment(name: str) -> str:
    """Increment the trailing digit run; append '2' if there isn't one."""
    m = _TRAILING_DIGITS.search(name)
    if m:
        return name[: m.start()] + str(int(m.group()) + 1)
    return name + "2"


def suggest_name(basename: str, sibling_dir: str) -> str:
    """Default name for the prompt: increment basename, skip existing siblings.

    `basename` is the repo root's folder name. `sibling_dir` is the directory
    in which the new clone will live (i.e. dirname(repo_root)).
    """
    candidate = _increment(basename)
    while os.path.exists(os.path.join(sibling_dir, candidate)):
        candidate = _increment(candidate)
    return candidate


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
