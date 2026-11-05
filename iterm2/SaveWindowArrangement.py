"""iTerm2 window-arrangement daemon.

Runs as an AutoLaunch script. Two jobs:

1. Registers the `save_window_arrangement` RPC, bound to Cmd+S in the `rc`
   dynamic profile. On an untitled window it prompts for a name, sets that as
   the window title, then saves; on a titled window it saves silently.

2. Auto-saves any "known" window — one with an iTerm2 window title set — as a
   named arrangement (name = the title) whenever it changes: tabs/splits added
   or removed, tabs renamed, window moved/resized, or agent bindings change.
   Untitled windows are ignored.
"""

import asyncio
import fcntl
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arrangement_iterm import ArrangementAgents

import iterm2

logger = logging.getLogger(__name__)


DEBOUNCE_SECONDS = 1.5
RETRY_SECONDS = 2
MAX_RETRY_SECONDS = 30

connection = None
app = None
agents = None

_debounce = {}  # window_id -> asyncio.Task
_tab_monitors = {}  # tab_id    -> asyncio.Task
_rpc_saves = {}
_save_requests = {}
_save_errors = {}


async def save_window(window, *, allow_prompt):
    name = await window.async_get_variable("titleOverride")
    if not name:
        if not allow_prompt:
            return
        alert = iterm2.TextInputAlert(
            "Save Window as Arrangement",
            "Enter a name for this arrangement:",
            "My Arrangement",
            "",
        )
        name = await alert.async_run(connection)
        if not name:
            return
        # Title doubles as the arrangement name and marks the window "known",
        # so it auto-saves from here on. async_set_variable can't write
        # titleOverride (API allows only user.* vars) — async_set_title is the
        # equivalent of the "Edit Window Title" menu item.
        await window.async_set_title(name)

    await agents.save(window, name)


async def _save_from_rpc(window):
    # Nothing is awaiting this task, so a failure would otherwise vanish.
    try:
        await save_window(window, allow_prompt=True)
    except Exception as exc:
        logger.exception("save failed for window %s", window.window_id)
        await iterm2.Alert("Arrangement was not saved", str(exc)).async_run(connection)


async def _delayed_save(window_id):
    retry = RETRY_SECONDS
    try:
        while window_id in _save_requests:
            delay = DEBOUNCE_SECONDS - (
                asyncio.get_running_loop().time() - _save_requests[window_id]
            )
            if delay > 0:
                await asyncio.sleep(delay)
                continue
            del _save_requests[window_id]
            window = next((w for w in app.windows if w.window_id == window_id), None)
            if window:
                try:
                    await save_window(window, allow_prompt=False)
                    _save_errors.pop(window_id, None)
                    retry = RETRY_SECONDS
                except Exception as exc:
                    message = str(exc)
                    if _save_errors.get(window_id) != message:
                        logger.exception("auto-save failed for window %s", window_id)
                        _save_errors[window_id] = message
                    _save_requests.setdefault(
                        window_id, asyncio.get_running_loop().time()
                    )
                    await asyncio.sleep(retry)
                    retry = min(retry * 2, MAX_RETRY_SECONDS)
    finally:
        _debounce.pop(window_id, None)
        if not any(w.window_id == window_id for w in app.windows):
            _save_errors.pop(window_id, None)


def schedule_save(window_id):
    _save_requests[window_id] = asyncio.get_running_loop().time()
    if window_id not in _debounce:
        _debounce[window_id] = asyncio.create_task(_delayed_save(window_id))


def _window_for_tab(tab_id):
    for w in app.windows:
        if any(t.tab_id == tab_id for t in w.tabs):
            return w
    return None


async def _watch_tab_title(tab_id):
    # Tab renames are not reported by LayoutChangeMonitor — watch each tab's
    # titleOverride directly.
    try:
        async with iterm2.VariableMonitor(
            connection, iterm2.VariableScopes.TAB, "titleOverride", tab_id
        ) as mon:
            while True:
                await mon.async_get()
                window = _window_for_tab(tab_id)
                if window:
                    schedule_save(window.window_id)
    except asyncio.CancelledError:
        return
    except Exception:
        # Ends the task cleanly (no unobserved-exception warning); reconcile
        # prunes the dead task and respawns a monitor on the next layout change.
        logger.exception("tab-title monitor error for tab %s", tab_id)


def reconcile_tab_monitors():
    """Spawn a title monitor for new tabs, cancel it for closed ones."""
    # Drop crashed/finished monitors first, so their tabs get re-monitored.
    for tab_id in [t for t, task in _tab_monitors.items() if task.done()]:
        del _tab_monitors[tab_id]
    current = {t.tab_id for w in app.windows for t in w.tabs}
    for tab_id in current - _tab_monitors.keys():
        _tab_monitors[tab_id] = asyncio.create_task(_watch_tab_title(tab_id))
    for tab_id in list(_tab_monitors.keys() - current):
        _tab_monitors.pop(tab_id).cancel()


# A transient iTerm2 API error must not kill a monitor loop — that would
# silently stop auto-saving with no visible signal. Log and carry on; the
# short sleep keeps a persistent failure from becoming a tight error loop.
async def _layout_loop():
    async with iterm2.LayoutChangeMonitor(connection) as mon:
        while True:
            try:
                await mon.async_get()
                reconcile_tab_monitors()
                for w in app.windows:
                    schedule_save(w.window_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("layout monitor error")
                await asyncio.sleep(1)


async def _focus_loop():
    # Catch-all: any window focus change gets saved. Also covers move/resize
    # (e.g. Hammerspoon re-homing), which LayoutChangeMonitor does not report.
    async with iterm2.FocusMonitor(connection) as mon:
        while True:
            try:
                update = await mon.async_get_next_update()
                changed = update.window_changed
                if changed is not None:
                    schedule_save(changed.window_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("focus monitor error")
                await asyncio.sleep(1)


async def main(_connection):
    global connection, app, agents
    connection = _connection
    app = await iterm2.async_get_app(connection)
    agents = ArrangementAgents(connection, app, schedule_save)

    @iterm2.RPC
    async def save_window_arrangement():
        # Hand off so the RPC returns immediately: the untitled-window path
        # awaits a text-input alert, and iTerm2 fails the call after 5s.
        window = app.current_window
        if window and window.window_id not in _rpc_saves:
            task = asyncio.create_task(_save_from_rpc(window))
            _rpc_saves[window.window_id] = task
            task.add_done_callback(lambda _: _rpc_saves.pop(window.window_id, None))

    await save_window_arrangement.async_register(connection)

    reconcile_tab_monitors()
    await asyncio.gather(_layout_loop(), _focus_loop(), agents.watch())


if __name__ == "__main__":
    lock_dir = Path.home() / ".local/state/iterm-agent-resume"
    lock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(lock_dir / "saver.lock", "w") as daemon_lock:
        try:
            fcntl.flock(daemon_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("Arrangement saver is already running.")
        iterm2.run_until_complete(main)
