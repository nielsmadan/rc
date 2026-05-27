# iterm2/CloneRepoToTab.py
"""iTerm2 clone-repo-to-tab daemon.

Runs as an AutoLaunch script. Registers `clone_repo_to_tab`, bound to
Cmd+Ctrl+N in the `rc` dynamic profile. On trigger: prompt for a name,
`git clone <origin>` to a sibling of the repo root, copy any `.env`
files (root and subdirectories, mirroring their relative paths), open
a new tab right of the current one with the original tab's split
structure, every pane sitting in the clone root.

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


async def _do_clone_to_tab(window, tab, session):
    """The actual work — runs as a background task so the RPC can return fast.

    iTerm2's RPC dispatcher has a short timeout; the prompt + git clone easily
    exceed it, which shows the user a "Timeout" error even though the function
    is still doing useful work. Decoupling fixes that.

    The clone runs inside the new tab's main pane (typed as a shell command)
    rather than as a subprocess in this daemon, so the new tab + splits open
    immediately and the user can watch clone progress. `mise trust` and the
    `.env` copy are chained after the clone so they only run on success.
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

        origin = await asyncio.to_thread(lib.resolve_origin_url, repo_root)
        if not origin:
            await _alert("No 'origin' remote configured.")
            return

        sibling_dir = os.path.dirname(repo_root)
        suggestion = lib.suggest_name(os.path.basename(repo_root), sibling_dir)

        prompt = iterm2.TextInputAlert(
            "Clone repo to new tab",
            f"Clone {origin}\ninto {sibling_dir}/<name>",
            "name",
            suggestion,
        )
        name = await prompt.async_run(connection)
        if not name:
            return

        dest = lib.compute_destination(repo_root, name)
        if os.path.exists(dest):
            await _alert(f"{name} already exists at {dest}.")
            return

        # Snapshot the original tab's layout BEFORE we touch anything.
        snapshot = _snapshot_tab(tab)

        # Pre-create the empty dest directory so every pane's shell can cd
        # into it via the profile customization below. Without this, the
        # cd-on-startup would fail and shells would fall back to $HOME — the
        # `git clone . ` typed below would then clone into the wrong place.
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

        new_tab_index = window.tabs.index(tab) + 1
        new_tab = await window.async_create_tab(
            profile_customizations=profile,
            index=new_tab_index,
        )

        root_session = new_tab.current_session
        await _recreate(snapshot, root_session, profile)

        await new_tab.async_set_title(name)
        await new_tab.async_select()
        await root_session.async_activate()

        # Shell command: clone in the visible pane, then `mise trust`, then
        # copy each `.env` file we found in the source repo (root and
        # subdirectories), mirroring relative paths via `mkdir -p`. Chained
        # with `&&` so clone/trust must succeed first. Tiny sleep so the
        # shell has finished starting before we type into it.
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
