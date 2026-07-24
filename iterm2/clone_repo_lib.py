"""Pure helpers for CloneRepoToTab.py — unit-testable outside iTerm2.

No iterm2 import: this module must stay importable in a plain Python
environment so its functions can be exercised by test_clone_repo_lib.py.
"""

import os
import re
import subprocess


_TRAILING_DIGITS = re.compile(r"(\d+)$")


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


def _sibling_slot(basename: str) -> int:
    """The family *slot* a member occupies: its trailing number, but a bare
    name (no digits, so `sibling_number` == 0) counts as slot 1 — the first
    checkout is "the first" whether it's named `foo` or `foo1`."""
    n = sibling_number(basename)
    return n if n >= 1 else 1


def select_sibling_slot(current_repo_root: str, candidate_repo_roots: list):
    """Pick the target checkout, filling the lowest gap in the open family.

    Considers `current_repo_root` plus every sibling in `candidate_repo_roots`
    (same parent dir + same base name), maps each to a *slot* (its trailing
    number; a bare name is slot 1), then targets the smallest slot >= 1 that
    is unoccupied. With no gap this is just highest-slot + 1 (the old
    behaviour); with a hole — e.g. `foo1, foo3, foo4` — it fills it (`foo2`).

    Returns `(name, anchor_repo_root, side)` where `name` is the target folder
    name (`base` + slot number), `anchor_repo_root` is the open sibling to
    position the new tab against, and `side` is "right" (place just after the
    anchor — the highest open sibling *below* the gap) or "left" (place just
    before it — used when filling below the lowest open sibling, e.g.
    `foo2, foo3` -> `foo1` left of `foo2`). Deterministic: independent of which
    sibling triggered it.
    """
    base = sibling_base(os.path.basename(current_repo_root.rstrip("/")))

    members = []  # [(slot, repo_root), ...] for the open family
    seen = set()
    for rr in [current_repo_root, *candidate_repo_roots]:
        key = rr.rstrip("/")
        if key in seen:
            continue
        if key != current_repo_root.rstrip("/") and not is_sibling(current_repo_root, rr):
            continue
        seen.add(key)
        members.append((_sibling_slot(os.path.basename(key)), rr))

    occupied = {slot for slot, _ in members}
    target = 1
    while target in occupied:
        target += 1
    name = base + str(target)

    below = [m for m in members if m[0] < target]
    if below:
        anchor = max(below, key=lambda m: m[0])[1]
        side = "right"
    else:
        anchor = min(members, key=lambda m: m[0])[1]
        side = "left"
    return name, anchor, side


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
