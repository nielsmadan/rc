"""iTerm2 window-arrangement daemon.

Runs as an AutoLaunch script. Two jobs:

1. Registers the `save_window_arrangement` RPC, bound to Cmd+S in the `rc`
   dynamic profile. On an untitled window it prompts for a name, sets that as
   the window title, then saves; on a titled window it saves silently.

2. Auto-saves any "known" window — one with an iTerm2 window title set — as a
   named arrangement (name = the title) whenever it changes: tabs/splits added
   or removed, tabs renamed, window moved/resized. Untitled windows are ignored.
"""

import asyncio

import iterm2

DEBOUNCE_SECONDS = 1.5

connection = None
app = None

_debounce = {}      # window_id -> asyncio.Task
_tab_monitors = {}  # tab_id    -> asyncio.Task


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

    await window.async_save_window_as_arrangement(name)


async def _delayed_save(window_id):
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
    except asyncio.CancelledError:
        return
    finally:
        # Drop our own entry so _debounce doesn't accumulate one stale task
        # per window for the daemon's lifetime. Guard against deleting a
        # newer task that schedule_save() may have just put in our place.
        if _debounce.get(window_id) is asyncio.current_task():
            del _debounce[window_id]
    window = next((w for w in app.windows if w.window_id == window_id), None)
    if window:
        try:
            await save_window(window, allow_prompt=False)
        except Exception as exc:
            print(f"auto-save failed for window {window_id}: {exc}")


def schedule_save(window_id):
    """Debounce: coalesce a burst of changes into one save."""
    task = _debounce.get(window_id)
    if task and not task.done():
        task.cancel()
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
    except Exception as exc:
        # Ends the task cleanly (no unobserved-exception warning); reconcile
        # prunes the dead task and respawns a monitor on the next layout change.
        print(f"tab-title monitor error for tab {tab_id}: {exc}")


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
            except Exception as exc:
                print(f"layout monitor error: {exc}")
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
            except Exception as exc:
                print(f"focus monitor error: {exc}")
                await asyncio.sleep(1)


async def main(_connection):
    global connection, app
    connection = _connection
    app = await iterm2.async_get_app(connection)

    @iterm2.RPC
    async def save_window_arrangement():
        window = app.current_window
        if window:
            await save_window(window, allow_prompt=True)

    await save_window_arrangement.async_register(connection)

    reconcile_tab_monitors()
    await asyncio.gather(_layout_loop(), _focus_loop())


iterm2.run_until_complete(main)
