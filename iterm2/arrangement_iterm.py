import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import arrangement_agents as agents

import iterm2

logger = logging.getLogger(__name__)


def startup_settings(profile):
    return {
        "Command": profile.command or "",
        "Custom Command": profile.use_custom_command,
    }


async def set_startup(session, settings):
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_command(settings["Command"])
    profile.set_use_custom_command(settings["Custom Command"])
    await session.async_set_profile_properties(profile)


async def repair_session(session, key):
    profile = await session.async_get_profile()
    embedded = agents.command_record(profile.command or "")
    if embedded:
        agents.verify_record(embedded, key)
        embedded = agents.sign_record(
            {**embedded, "pane": agents.pane_id(session.session_id)}, key
        )
        await session.async_set_variable(agents.RESUME_VAR, json.dumps(embedded))
        await set_startup(session, embedded["original"])
    return embedded, profile


class ArrangementAgents:
    def __init__(self, connection, app, schedule, home=None, helper=None, python=None):
        self.connection = connection
        self.app = app
        self.schedule = schedule
        self.home = home or Path.home()
        self.helper = (
            helper or Path(__file__).resolve().parent.parent / "bin/iterm-agent-resume"
        )
        self.python = python or sys.executable
        self.lock = asyncio.Lock()
        self.owners = {}
        self.last_error = None
        self.state = self.home / ".local/state/iterm-agent-resume"
        self.key = agents.signing_key(self.state)
        self.snapshot = (None, {})
        self.snapshot_at = float("-inf")

    async def reconcile(self):
        async with self.lock:
            await self._reconcile(force=True)

    async def _presence(self, force):
        if not force and time.monotonic() - self.snapshot_at < 2:
            return self.snapshot
        rows = None
        parents = {}
        try:
            text, process_text = await asyncio.gather(
                agents.command_output(
                    [str(agents.presence_binary(self.home)), "sessions", "--json"]
                ),
                agents.command_output(["/bin/ps", "-axo", "pid=,ppid=,lstart="]),
            )
            rows = agents.local_bindings(agents.presence_sessions(text))
            parents = agents.process_table(process_text)
            self.last_error = None
        except (TimeoutError, OSError, TypeError, ValueError, RuntimeError) as exc:
            message = str(exc) or type(exc).__name__
            if self.last_error != message:
                print(
                    f"agent presence unavailable; retaining saved bindings: {message}"
                )
                self.last_error = message
        self.snapshot = (rows, parents)
        self.snapshot_at = time.monotonic()
        return self.snapshot

    async def _reconcile(self, windows=None, force=False):
        windows = list(self.app.windows if windows is None else windows)
        launches = {}
        for window in windows:
            for tab in list(window.tabs):
                for session in list(tab.sessions):
                    try:
                        launches[session.session_id] = agents.launch_record(
                            self.state, session.session_id
                        )
                    except (OSError, TypeError, ValueError):
                        pass
        rows, parents = await self._presence(force)
        for window in windows:
            for tab in list(window.tabs):
                for session in list(tab.sessions):
                    try:
                        await self._reconcile_session(
                            window, session, rows, parents, launches
                        )
                    except (OSError, TypeError, ValueError, iterm2.RPCException) as exc:
                        print(
                            f"agent binding unchanged for pane {session.session_id}: {exc}"
                        )

    async def _reconcile_session(self, window, session, rows, parents, launches):
        embedded, profile = await repair_session(session, self.key)
        if embedded:
            self.schedule(window.window_id)
        old = agents.object_value(await session.async_get_variable(agents.RESUME_VAR))
        if old:
            agents.verify_record(old, self.key, session.session_id)
        disabled = await session.async_get_variable(agents.DISABLED_VAR)
        launch = agents.launch_record(self.state, session.session_id)
        if disabled or (old and agents.launch_ended(self.state, old)):
            if old:
                await session.async_set_variable(agents.RESUME_VAR, "")
                self.schedule(window.window_id)
            return
        if rows is None or launch != launches.get(session.session_id):
            return
        if launch and launch.get("finished"):
            return
        row = rows.get(agents.pane_id(session.session_id))
        if not row or row.get("agent") not in ("claude", "codex"):
            return
        original = embedded["original"] if embedded else startup_settings(profile)
        record = agents.binding_record(
            row, launch, original, parents, session.session_id
        )
        if launch and record["recipe"] is None:
            return
        if (
            old
            and old["agent"] == record["agent"]
            and old["session"] == record["session"]
            and record["recipe"] is None
            and record["process"]
            and record["process"] == old["process"]
        ):
            record = {
                **record,
                "recipe": old["recipe"],
                "forceSandbox": old["forceSandbox"],
                "cwd": old["cwd"],
                "generation": old.get("generation"),
            }
        record = agents.sign_record(record, self.key)
        if agents.launch_record(self.state, session.session_id) != launch:
            return
        if record != old:
            await session.async_set_variable(agents.RESUME_VAR, json.dumps(record))
            self.schedule(window.window_id)

    async def save(self, window, name):
        async with self.lock:
            names = {
                w.window_id: await w.async_get_variable("titleOverride")
                for w in self.app.windows
            }
            if names.get(window.window_id) != name:
                raise ValueError(
                    "window name changed before save; retry with its current name"
                )
            self.owners = {
                key: value
                for key, value in self.owners.items()
                if names.get(value) == key
            }
            owner = self.owners.setdefault(name, window.window_id)
            if owner != window.window_id:
                raise ValueError(
                    f'arrangement "{name}" is already owned by another open window; rename this window to save it'
                )
            await self._reconcile(windows=[window])
            async with iterm2.Transaction(self.connection):
                if await window.async_get_variable("titleOverride") != name:
                    raise ValueError(
                        "window name changed during reconciliation; retry saving"
                    )
                sessions = [s for tab in window.tabs for s in tab.sessions]
                changed = []
                try:
                    for session in sessions:
                        raw = await session.async_get_variable(agents.RESUME_VAR)
                        if not raw or await session.async_get_variable(
                            agents.DISABLED_VAR
                        ):
                            continue
                        record = agents.verify_record(
                            agents.object_value(raw), self.key, session.session_id
                        )
                        original = startup_settings(await session.async_get_profile())
                        if agents.command_record(original["Command"]):
                            raise ValueError(
                                "pane startup repair is pending; refusing to save a nested launcher"
                            )
                        record = agents.sign_record(
                            {**record, "original": original}, self.key
                        )
                        changed.append((session, original))
                        await set_startup(
                            session,
                            {
                                "Custom Command": "Yes",
                                "Command": agents.resume_command(
                                    record, self.python, self.helper
                                ),
                            },
                        )
                    await window.async_save_window_as_arrangement(name)
                finally:
                    failures = []
                    for session, original in changed:
                        try:
                            await set_startup(session, original)
                        except Exception as exc:
                            logger.exception(
                                "startup cleanup failed for %s", session.session_id
                            )
                            failures.append(f"{session.session_id}: {exc}")
                    if failures:
                        raise RuntimeError(
                            "startup cleanup failed; next reconciliation will repair: "
                            + "; ".join(failures)
                        )

    async def watch(self):
        while True:
            try:
                await self.reconcile()
            except Exception:
                logger.exception("agent reconciliation failed")
            await asyncio.sleep(2)


async def prepare_resume(connection, record, session_id, key):
    agents.verify_record(record, key)
    app = await iterm2.async_get_app(connection)
    session = app.get_session_by_id(session_id)
    if not session:
        raise ValueError("restored pane no longer exists")
    current = agents.sign_record({**record, "pane": agents.pane_id(session_id)}, key)
    async with iterm2.Transaction(connection):
        embedded = agents.command_record(
            (await session.async_get_profile()).command or ""
        )
        if embedded:
            agents.verify_record(embedded, key)
            if embedded != record:
                raise ValueError("pane resume record changed")
            await set_startup(session, record["original"])
        else:
            live = agents.object_value(
                await session.async_get_variable(agents.RESUME_VAR)
            )
            if live != current:
                raise ValueError("pane no longer owns this resume record")
        await session.async_set_variable(agents.RESUME_VAR, json.dumps(current))
