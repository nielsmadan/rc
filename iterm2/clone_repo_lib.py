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


def sibling_base(basename: str) -> str:
    """The family base name: `basename` with its trailing digit-run stripped
    (`"project2" -> "project"`, `"rc" -> "rc"`)."""
    m = _TRAILING_DIGITS.search(basename)
    return basename[: m.start()] if m else basename


def sibling_number(basename: str) -> int:
    """Ordering key within a family: the trailing digits as an int, or 0 when
    there are none (so bare `rc` < `rc2` < `rc3`)."""
    m = _TRAILING_DIGITS.search(basename)
    return int(m.group()) if m else 0


def is_sibling(repo_root_a: str, repo_root_b: str) -> bool:
    """True iff the two repo roots are members of the same checkout family:
    same parent directory AND same base name (trailing digits stripped)."""
    a, b = repo_root_a.rstrip("/"), repo_root_b.rstrip("/")
    if os.path.dirname(a) != os.path.dirname(b):
        return False
    return sibling_base(os.path.basename(a)) == sibling_base(os.path.basename(b))


def select_highest_sibling(current_repo_root: str, candidate_repo_roots: list) -> str:
    """Return the repo root of the highest-numbered member of
    `current_repo_root`'s family, considering it plus `candidate_repo_roots`.

    Returns `current_repo_root` when nothing in the candidates outranks it, so
    the caller falls back to the triggering checkout's own +1.
    """
    best = current_repo_root
    best_n = sibling_number(os.path.basename(current_repo_root.rstrip("/")))
    for rr in candidate_repo_roots:
        if not is_sibling(current_repo_root, rr):
            continue
        n = sibling_number(os.path.basename(rr.rstrip("/")))
        if n > best_n:
            best, best_n = rr, n
    return best


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


# Repo-root config filenames lefthook recognises (name × extension).
LEFTHOOK_CONFIG_NAMES = (
    "lefthook.yml",
    "lefthook.yaml",
    ".lefthook.yml",
    ".lefthook.yaml",
    "lefthook.toml",
    "lefthook.json",
)


def lefthook_install_clause() -> str:
    """Shell snippet that runs `lefthook install` iff a lefthook config exists.

    The clone dir doesn't exist when the command is assembled, so detection
    has to happen at runtime in the typed shell command. Built as its own
    statement (leading `; `) that self-gates on a config file being present in
    the freshly-cloned cwd — a non-lefthook repo (or a failed clone, which
    leaves an empty dir) simply skips it without leaving a non-zero exit.
    """
    test = " || ".join(f"[ -f {name} ]" for name in LEFTHOOK_CONFIG_NAMES)
    return f"; if {test}; then lefthook install; fi"
