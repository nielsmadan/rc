# iterm2/CloneRepoToTab.py
"""iTerm2 clone-repo-to-tab daemon.

Runs as an AutoLaunch script. Registers `clone_repo_to_tab`, bound to
Cmd+Ctrl+N in the `rc` dynamic profile. On trigger: auto-pick the target
sibling name by filling the lowest gap in the family of sibling checkouts
OPEN in this window (e.g. `foo1, foo3, foo4` -> `foo2`; contiguous ->
highest + 1), confirm via an OK/Cancel dialog, `git clone <origin>` to
that sibling of the repo root, copy any `.env` files (root and
subdirectories, mirroring their relative paths), run `lefthook install`
if the clone has a lefthook config, open a new tab next to the gap's
neighbour (right of the sibling below the gap, or left of the lowest open
sibling when filling below it) with the original tab's split structure,
every pane sitting in the clone root. If the sibling directory already
exists, the clone is skipped entirely — the tab just opens pointed at the
existing directory.

Pure helpers (path math, git wrappers, `.env` discovery) live in
`clone_repo_lib.py` so they can be unit-tested outside iTerm2.
"""

import asyncio
import os
import shlex
import sys

# AutoLaunch runs each script as a stand-alone file, so import-from-sibling
# needs the script's own dir on sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import iterm2  # noqa: E402

import clone_repo_lib as lib  # noqa: E402


connection = None
app = None


# Internal snapshot of a tab's split tree. We capture before creating the new
# tab so the original's structure can't shift under us mid-recreate.
class _SplitNode:
    __slots__ = ("vertical", "children")

    def __init__(self, vertical: bool, children: list):
        self.vertical = vertical
        self.children = children  # list[_SplitNode | _LeafNode]


class _LeafNode:
    __slots__ = ()


def _snapshot_tab(tab) -> "_SplitNode | _LeafNode":
    """Walk tab.root and return a structural snapshot (orientation + children)."""
    return _snapshot(tab.root)


def _snapshot(node):
    if isinstance(node, iterm2.Session):
        return _LeafNode()
    # iterm2.Splitter — has `.vertical` and `.children`
    return _SplitNode(node.vertical, [_snapshot(c) for c in node.children])


async def _recreate(node, target_session, profile):
    """DFS-recreate the snapshot inside the new tab.

    `target_session` is the session in the new tab that corresponds to `node`
    in the snapshot. For a splitter, we grow N-1 siblings of `target_session`
    by splitting the most-recently-created pane each time — that produces
    panes in left-to-right (or top-to-bottom) order matching node.children.
    """
    if isinstance(node, _LeafNode):
        return
    n = len(node.children)
    sessions = [target_session]
    prev = target_session
    for _ in range(n - 1):
        prev = await prev.async_split_pane(
            vertical=node.vertical,
            before=False,
            profile_customizations=profile,
        )
        sessions.append(prev)
    for child, sess in zip(node.children, sessions):
        await _recreate(child, sess, profile)


async def _alert(message: str):
    """Show an iTerm2 alert with a single OK button."""
    await iterm2.Alert("Clone repo to new tab", message).async_run(connection)


async def _confirm(message: str) -> bool:
    """Show an OK/Cancel modal; return True iff OK was clicked.

    `Alert.async_run` returns the selected button's index + 1000, so the first
    button ("OK") is 1000. OK is the default (Enter); Cancel maps to Esc.
    """
    alert = iterm2.Alert("Clone repo to new tab", message)
    alert.add_button("OK")
    alert.add_button("Cancel")
    return await alert.async_run(connection) == 1000


async def _do_clone_to_tab(window, tab, session):
    """The actual work — runs as a background task so the RPC can return fast.

    iTerm2's RPC dispatcher has a short timeout; the confirm dialog + git clone
    easily exceed it, which shows the user a "Timeout" error even though the
    function is still doing useful work. Decoupling fixes that.

    The clone runs inside the new tab's main pane (typed as a shell command)
    rather than as a subprocess in this daemon, so the new tab + splits open
    immediately and the user can watch clone progress. `mise trust` and the
    `.env` copy are chained after the clone so they only run on success.

    When the destination directory already exists, no shell command is sent:
    the tab opens pointed at the existing directory and nothing is cloned,
    trusted, or copied.
    """
    try:
        path = await session.async_get_variable("path")
        if not path:
            await _alert("Couldn't determine the current directory.")
            return

        repo_root = await asyncio.to_thread(lib.resolve_repo_root, path)
        if not repo_root:
            await _alert("Not a git repository.")
            return

        # Auto-pick the target sibling name, filling the lowest gap in the
        # family of checkouts OPEN in this window (not just the triggering tab).
        # Enumerate the window's tabs, resolve each one's repo root, then pick
        # the lowest unoccupied slot and the tab to anchor the new one against.
        # With no gap this is highest-slot + 1; a hole (e.g. foo1, foo3) fills
        # it (foo2). `side` says whether to place the new tab just right of the
        # anchor (the sibling below the gap) or left of it (filling below the
        # lowest open sibling).
        pairs = []  # [(repo_root, tab), ...] for tabs sitting in a git repo
        for t in window.tabs:
            t_path = await t.current_session.async_get_variable("path")
            if not t_path:
                continue
            t_root = await asyncio.to_thread(lib.resolve_repo_root, t_path)
            if t_root:
                pairs.append((t_root, t))

        name, anchor_root, side = lib.select_sibling_slot(
            repo_root, [rr for rr, _ in pairs]
        )
        anchor_tab = next((t for rr, t in pairs if rr == anchor_root), tab)
        dest = lib.compute_destination(repo_root, name)
        dest_exists = os.path.exists(dest)
        if dest_exists and not os.path.isdir(dest):
            await _alert(f"{name} exists at {dest} but isn't a directory.")
            return

        # Confirm via OK/Cancel, describing what will happen. An existing dir
        # is just opened (no clone needed, so no `origin` required); a fresh
        # name is cloned from `origin`.
        if dest_exists:
            origin = None
            message = f"{dest} exists.\nOpen a new tab there (no clone)?"
        else:
            origin = await asyncio.to_thread(lib.resolve_origin_url, repo_root)
            if not origin:
                await _alert("No 'origin' remote configured.")
                return
            message = f"Clone {origin}\ninto {dest}"
        if not await _confirm(message):
            return

        # Snapshot the original tab's layout BEFORE we touch anything.
        snapshot = _snapshot_tab(tab)

        # For a fresh destination, pre-create the empty dir so every pane's
        # shell can cd into it via the profile customization below. Without
        # this, the cd-on-startup would fail and shells would fall back to
        # $HOME — the `git clone . ` typed below would then clone into the
        # wrong place. An already-existing dir (e.g. a sibling checkout `dev3`
        # opened from `dev2`) is reused as-is — we skip both creation and the
        # clone, and just open a tab pointed at it.
        if not dest_exists:
            try:
                await asyncio.to_thread(os.makedirs, dest)
            except OSError as exc:
                await _alert(f"Couldn't create {dest}: {exc}")
                return

        profile = iterm2.LocalWriteOnlyProfile()
        profile.set_custom_directory(dest)
        profile.set_initial_directory_mode(
            iterm2.InitialWorkingDirectory.INITIAL_WORKING_DIRECTORY_CUSTOM
        )

        anchor_index = window.tabs.index(anchor_tab)
        new_tab_index = anchor_index + 1 if side == "right" else anchor_index
        new_tab = await window.async_create_tab(
            profile_customizations=profile,
            index=new_tab_index,
        )

        root_session = new_tab.current_session
        await _recreate(snapshot, root_session, profile)

        await new_tab.async_set_title(name)
        await new_tab.async_select()
        await root_session.async_activate()

        # Only clone into a freshly-created directory. An existing dir is
        # assumed to be a working checkout already, so we send no command —
        # the tab just opens pointed at it.
        if not dest_exists:
            # Shell command: clone in the visible pane, then `mise trust`, then
            # copy each `.env` file we found in the source repo (root and
            # subdirectories), mirroring relative paths via `mkdir -p`. Chained
            # with `&&` so clone/trust must succeed first. A trailing
            # `lefthook install` runs as its own statement, self-gated on the
            # clone having a lefthook config. Tiny sleep so the shell has
            # finished starting before we type into it.
            env_files = await asyncio.to_thread(lib.find_env_files, repo_root)
            copy_cmds = []
            for rel in env_files:
                src = os.path.join(repo_root, rel)
                subdir = os.path.dirname(rel)
                if subdir:
                    copy_cmds.append(
                        f"mkdir -p {shlex.quote(subdir)} "
                        f"&& cp {shlex.quote(src)} {shlex.quote(rel)}"
                    )
                else:
                    copy_cmds.append(f"cp {shlex.quote(src)} .")
            env_clause = (" && " + " && ".join(copy_cmds)) if copy_cmds else ""
            cmd = (
                f"git clone {shlex.quote(origin)} . "
                f"&& mise trust ."
                f"{env_clause}"
                f"{lib.lefthook_install_clause()}"
            )
            await asyncio.sleep(0.3)
            await root_session.async_send_text(cmd + "\n")
    except Exception as exc:
        print(f"clone_repo_to_tab error: {exc}")


async def main(_connection):
    global connection, app
    connection = _connection
    app = await iterm2.async_get_app(connection)

    @iterm2.RPC
    async def clone_repo_to_tab():
        # Capture the active window/tab/session now, before the user can
        # switch focus, then fire-and-forget so the RPC returns immediately.
        window = app.current_window
        if window is None:
            return
        tab = window.current_tab
        session = tab.current_session
        asyncio.create_task(_do_clone_to_tab(window, tab, session))

    await clone_repo_to_tab.async_register(connection)
    # Keep the daemon alive forever — AutoLaunch scripts are long-lived.
    await asyncio.Event().wait()


iterm2.run_until_complete(main)
