import asyncio
import copy
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import arrangement_agents as agents

PANE = "1A0478C7-1362-4522-B935-588B9A313416"
IDENTITY = "0e238fc7-96dc-4b26-9d7f-7a233e79a4f0"
GENERATION = "99808f74-2f51-484c-99ab-c819c2302b34"
STARTED = "Sun Nov 1 00:00:00 2026"
PROCESSES = {
    10: {"parent": 1, "startedAt": STARTED},
    20: {"parent": 10, "startedAt": STARTED},
    30: {"parent": 20, "startedAt": STARTED},
}


def record(**changes):
    return {
        "version": 1,
        "pane": PANE,
        "process": "30:" + STARTED,
        "agent": "claude",
        "session": IDENTITY,
        "cwd": "/tmp",
        "recipe": "claude-raw",
        "generation": None,
        "forceSandbox": False,
        "original": {"Command": "", "Custom Command": "No"},
        **changes,
    }


def row(**changes):
    return {
        "agent": "claude",
        "running": True,
        "session": {"id": IDENTITY, "cwd": "/tmp"},
        "terminal": {"terminalType": "iterm2", "sessionId": "w0t2p4:" + PANE},
        "process": {"pid": 30},
        "remoteHost": None,
        "tmux": None,
        **changes,
    }


class RecordsTests(unittest.TestCase):
    def test_signed_record_rejects_modified_directory_recipe_and_pane_replay(self):
        key = b"test key"
        signed = agents.sign_record(record(), key)
        self.assertEqual(agents.verify_record(signed, key, PANE), signed)
        for changes in ({"cwd": "/Users/someone/rc"}, {"recipe": "clor"}):
            with self.assertRaises(ValueError):
                agents.verify_record({**signed, **changes}, key)
        with self.assertRaises(ValueError):
            agents.verify_record(signed, key, IDENTITY)

    def test_v1_decoder_accepts_older_diagnostic_wording(self):
        command = agents.resume_command(record(), "/python", "/helper")
        old = command.replace("Agent resume helper unavailable", "An older diagnostic")
        self.assertEqual(agents.command_record(old), record())

    def test_command_roundtrip_preserves_shell_metacharacters_as_data(self):
        data = record(cwd="/tmp/it's $(touch nope); a\nb")
        command = agents.resume_command(data, "/some python", "/some helper")
        self.assertEqual(agents.command_record(command), data)
        self.assertEqual(agents.agent_argv(data)[-1], data["session"])

    def test_unknown_version_or_recipe_is_rejected(self):
        for data in [
            record(version=2),
            record(recipe="sh"),
            record(recipe="codex"),
            record(session="--last"),
        ]:
            with self.subTest(data=data), self.assertRaises((TypeError, ValueError)):
                agents.encode_record(data)

    def test_pane_binding_requires_one_local_agent(self):
        local = row()
        self.assertEqual(agents.local_bindings([local]), {PANE: local})
        self.assertEqual(agents.local_bindings([local, row()]), {})
        self.assertEqual(
            agents.local_bindings([row(remoteHost="mini"), row(tmux={"pane": "%1"})]),
            {},
        )

    def test_recipe_must_belong_to_process_ancestor(self):
        launch = {
            "version": 1,
            "recipe": "clor",
            "token": GENERATION,
            "priorProcesses": [],
            "pid": 10,
            "forceSandbox": True,
            "startedAt": STARTED,
            "cwd": "/tmp",
        }
        bound = agents.binding_record(
            row(), launch, record()["original"], PROCESSES, PANE
        )
        self.assertEqual((bound["recipe"], bound["forceSandbox"]), ("clor", True))
        unbound = agents.binding_record(
            row(),
            launch,
            record()["original"],
            {30: {"parent": 1, "startedAt": STARTED}},
            PANE,
        )
        self.assertEqual(unbound["recipe"], None)

    def test_presence_failure_does_not_become_empty(self):
        for data in [
            {},
            {"protocol": 1, "sessions": [None]},
            {"protocol": 1, "sessions": [], "problems": [{"kind": {"type": "state"}}]},
        ]:
            with self.subTest(data=data), self.assertRaises((TypeError, ValueError)):
                agents.presence_sessions(json.dumps(data))
        self.assertEqual(
            agents.presence_sessions(
                json.dumps(
                    {
                        "protocol": 1,
                        "sessions": [],
                        "problems": [{"kind": {"type": "sink"}}],
                    }
                )
            ),
            [],
        )

    def test_lock_is_exclusive_across_processes_and_recovers_after_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with agents.SessionLock(path, "claude", "one"):
                script = 'import fcntl,sys; f=open(sys.argv[1],"w"); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)'
                result = subprocess.run(
                    [sys.executable, "-c", script, str(next(path.iterdir()))],
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(b"BlockingIOError", result.stderr)
            with agents.SessionLock(path, "claude", "one"):
                pass

    def test_launch_checks_presence_then_runs_wrapper_in_saved_directory(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return types.SimpleNamespace(
                stdout='{"protocol":1,"sessions":[]}', returncode=7
            )

        with tempfile.TemporaryDirectory() as directory:
            result = agents.run_agent(
                agents.sign_record(
                    record(forceSandbox=True),
                    agents.signing_key(
                        Path(directory) / ".local/state/iterm-agent-resume"
                    ),
                ),
                Path(directory),
                {"PATH": "/bin", "AGENT_ITERM_LAUNCH_ACTIVE": "1"},
                runner,
            )
        self.assertEqual(result, 7)
        self.assertEqual(calls[1][0][-3:], ["claude-raw", "--resume", IDENTITY])
        self.assertEqual(calls[1][1]["cwd"], "/tmp")
        self.assertEqual(
            calls[1][1]["env"],
            {
                "PATH": "/bin",
                "AGENT_REQUIRE_SECRETS": "1",
                "AGENT_FORCE_SANDBOX": "1",
                "AGENT_REQUIRE_SANDBOX": "1",
            },
        )

    def test_running_session_blocks_launch(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return types.SimpleNamespace(
                stdout=json.dumps({"protocol": 1, "sessions": [row()]})
            )

        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "already running"),
        ):
            agents.run_agent(
                agents.sign_record(
                    record(),
                    agents.signing_key(
                        Path(directory) / ".local/state/iterm-agent-resume"
                    ),
                ),
                Path(directory),
                {},
                runner,
            )
        self.assertEqual(len(calls), 1)


class Profile:
    def __init__(self):
        self.values = {}

    def set_command(self, value):
        self.values["Command"] = value

    def set_use_custom_command(self, value):
        self.values["Custom Command"] = value


class Transaction:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        self.connection.transactions += 1

    async def __aexit__(self, *_):
        self.connection.transactions -= 1


class Session:
    def __init__(self):
        self.session_id = PANE
        self.settings = record()["original"].copy()
        self.variables = {}
        self.fail_repair = False

    async def async_get_profile(self):
        return types.SimpleNamespace(
            command=self.settings["Command"],
            use_custom_command=self.settings["Custom Command"],
        )

    async def async_set_profile_properties(self, profile):
        if self.fail_repair and agents.MARKER not in profile.values["Command"]:
            self.fail_repair = False
            raise RuntimeError("profile RPC unavailable")
        self.settings.update(profile.values)

    async def async_get_variable(self, name):
        return self.variables.get(name)

    async def async_set_variable(self, name, value):
        self.variables[name] = value


class Window:
    def __init__(self, session, connection, window_id="one"):
        self.window_id = window_id
        self.tabs = [types.SimpleNamespace(sessions=[session])]
        self.connection = connection
        self.saved = None
        self.error = None
        self.title = "test"

    async def async_get_variable(self, name):
        return self.title

    async def async_save_window_as_arrangement(self, name):
        assert self.connection.transactions == 1
        self.saved = copy.deepcopy(self.tabs[0].sessions[0].settings)
        if self.error:
            raise self.error


class SaveTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fake = types.SimpleNamespace(
            LocalWriteOnlyProfile=Profile,
            Transaction=Transaction,
            RPCException=RuntimeError,
        )
        self.modules = patch.dict(sys.modules, {"iterm2": fake})
        self.modules.start()
        sys.modules.pop("arrangement_iterm", None)
        import arrangement_iterm

        self.bridge = arrangement_iterm
        self.connection = types.SimpleNamespace(transactions=0)
        self.session = Session()
        self.window = Window(self.session, self.connection)
        self.app = types.SimpleNamespace(windows=[self.window])
        self.scheduled = []
        self.directory = tempfile.TemporaryDirectory()
        self.service = self.bridge.ArrangementAgents(
            self.connection,
            self.app,
            self.scheduled.append,
            home=Path(self.directory.name),
        )
        self.saved_record = agents.sign_record(record(), self.service.key)
        self.session.variables[agents.RESUME_VAR] = json.dumps(self.saved_record)

        async def output(argv, **kwargs):
            return (
                "1 0 Sun Nov 1 00:00:00 2026\n"
                if argv[0] == "/bin/ps"
                else '{"protocol":1,"sessions":[]}'
            )

        self.output = patch.object(agents, "command_output", output)
        self.output.start()

    def tearDown(self):
        self.directory.cleanup()
        self.output.stop()
        self.modules.stop()
        sys.modules.pop("arrangement_iterm", None)

    async def test_save_restores_live_profile_even_on_failure(self):
        self.window.error = RuntimeError("save failed")
        with self.assertRaisesRegex(RuntimeError, "save failed"):
            await self.service.save(self.window, "test")
        self.assertEqual(self.session.settings, record()["original"])
        self.assertEqual(
            agents.command_record(self.window.saved["Command"]), self.saved_record
        )
        self.assertEqual(self.connection.transactions, 0)

    async def test_cancellation_restores_profile(self):
        self.window.error = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.service.save(self.window, "test")
        self.assertEqual(self.session.settings, record()["original"])

    async def test_repeated_restore_and_save_preserves_original(self):
        await self.service.save(self.window, "test")
        self.session.settings = self.window.saved
        self.session.variables = {}
        await self.service.reconcile()
        self.assertEqual(self.session.settings, record()["original"])
        await self.service.save(self.window, "test")
        self.assertEqual(
            agents.command_record(self.window.saved["Command"]), self.saved_record
        )

    async def test_missing_presence_keeps_binding_and_repairs_interrupted_save(self):
        self.session.settings = {
            "Custom Command": "Yes",
            "Command": agents.resume_command(self.saved_record, "/python", "/helper"),
        }

        async def failed(*_):
            raise RuntimeError("offline")

        with patch.object(agents, "command_output", failed):
            await self.service.reconcile()
        self.assertEqual(self.session.settings, record()["original"])
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR]), self.saved_record
        )

    async def test_clear_is_saved_as_plain_shell(self):
        self.session.variables[agents.DISABLED_VAR] = "1"
        await self.service.save(self.window, "test")
        self.assertEqual(self.window.saved, record()["original"])
        self.assertEqual(self.session.variables[agents.RESUME_VAR], "")

    async def test_duplicate_name_cannot_overwrite_owner(self):
        await self.service.save(self.window, "test")
        second = Window(Session(), self.connection, "two")
        self.app.windows.append(second)
        with self.assertRaisesRegex(ValueError, "already owned"):
            await self.service.save(second, "test")
        self.assertEqual(second.saved, None)

    def install_launch(self, recipe="clor"):
        directory = self.service.state / "launches"
        directory.mkdir(exist_ok=True)
        path = directory / (PANE + ".json")
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "recipe": recipe,
                    "token": GENERATION,
                    "priorProcesses": [],
                    "pid": 10,
                    "startedAt": STARTED,
                    "cwd": "/tmp",
                    "forceSandbox": False,
                }
            )
        )
        path.chmod(0o600)

    async def capture(self, rows, processes=PROCESSES):
        async def snapshot(_):
            return agents.local_bindings(rows), processes

        with patch.object(self.service, "_presence", snapshot):
            await self.service.reconcile()

    async def test_unbound_capture_uses_trusted_directory_and_schedules_save(self):
        self.session.variables = {}
        self.install_launch()
        await self.capture([row(session={"id": IDENTITY, "cwd": "/untrusted/cwd"})])
        saved = json.loads(self.session.variables[agents.RESUME_VAR])
        self.assertEqual(
            (saved["session"], saved["recipe"], saved["cwd"]),
            (IDENTITY, "clor", "/tmp"),
        )
        agents.verify_record(saved, self.service.key, PANE)
        self.assertEqual(self.scheduled, ["one"])

    async def test_intentional_exit_clears_even_stale_presence_then_allows_new_capture(
        self,
    ):
        self.install_launch()
        path = self.service.state / "launches" / (PANE + ".json")
        await self.capture([row()])
        self.scheduled.clear()
        outcomes = self.service.state / "outcomes"
        outcomes.mkdir()
        outcome = outcomes / (GENERATION + ".json")
        outcome.write_text(json.dumps({"ended": True, "pane": PANE}))
        outcome.chmod(0o600)
        path.write_text(json.dumps({"version": 1, "finished": True}))
        await self.capture([row()])
        self.assertEqual(self.session.variables[agents.RESUME_VAR], "")
        self.assertEqual(self.scheduled, ["one"])
        await self.service.save(self.window, "test")
        self.assertEqual(self.window.saved, record()["original"])
        outcome.unlink()
        self.install_launch()
        await self.capture([row()])
        saved = json.loads(self.session.variables[agents.RESUME_VAR])
        self.assertEqual(saved["session"], IDENTITY)
        self.assertEqual(saved["recipe"], "clor")

    async def test_unrelated_successful_command_preserves_recovery(self):
        self.install_launch()
        path = self.service.state / "launches" / (PANE + ".json")
        path.write_text(
            json.dumps(
                {"version": 1, "token": GENERATION, "finished": True, "ended": True}
            )
        )
        await self.capture([])
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR]), self.saved_record
        )
        self.assertEqual(self.scheduled, [])

    async def test_launch_change_during_presence_does_not_rebind_old_session(self):
        self.install_launch("claude-raw")

        async def changed(_):
            self.install_launch("clor")
            return agents.local_bindings([row()]), PROCESSES

        with patch.object(self.service, "_presence", changed):
            await self.service.reconcile()
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR]), self.saved_record
        )
        self.assertEqual(self.scheduled, [])

    async def test_old_process_cannot_acquire_new_launch_recipe(self):
        self.install_launch("clor")
        path = self.service.state / "launches" / (PANE + ".json")
        launch = json.loads(path.read_text())
        path.write_text(json.dumps({**launch, "priorProcesses": ["30:" + STARTED]}))
        await self.capture([row()])
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR]), self.saved_record
        )

    async def test_stale_process_is_not_captured_into_an_empty_pane(self):
        self.session.variables = {}
        self.install_launch("clor")
        path = self.service.state / "launches" / (PANE + ".json")
        launch = json.loads(path.read_text())
        path.write_text(json.dumps({**launch, "priorProcesses": ["30:" + STARTED]}))
        await self.capture([row()])
        self.assertEqual(self.session.variables, {})
        self.assertEqual(self.scheduled, [])

    async def test_failed_auto_save_retries_without_another_event(self):
        import SaveWindowArrangement as daemon

        daemon.app = self.app
        daemon.DEBOUNCE_SECONDS = 0.001
        daemon.RETRY_SECONDS = 0.001
        calls = []

        async def save(*_, **__):
            calls.append(True)
            if len(calls) == 1:
                raise RuntimeError("temporary API failure")

        try:
            with patch.object(daemon, "save_window", save):
                daemon.schedule_save("one")
                await asyncio.wait_for(daemon._debounce["one"], 1)
            self.assertEqual(len(calls), 2)
            self.assertEqual(daemon._save_requests, {})
            self.assertEqual(daemon._save_errors, {})
        finally:
            sys.modules.pop("SaveWindowArrangement", None)

    async def test_conversation_replacement_and_unknown_new_process(self):
        self.install_launch()
        await self.capture([row()])
        replacement = "4e4a2c79-204a-4104-8561-e984e60673ed"
        await self.capture([row(session={"id": replacement, "cwd": "/tmp"})])
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR])["session"],
            replacement,
        )
        (self.service.state / "launches" / (PANE + ".json")).unlink()
        processes = {**PROCESSES, 31: {"parent": 20, "startedAt": STARTED}}
        await self.capture(
            [row(session={"id": replacement, "cwd": "/tmp"}, process={"pid": 31})],
            processes,
        )
        self.assertEqual(
            json.loads(self.session.variables[agents.RESUME_VAR])["recipe"], None
        )

    async def test_unsigned_terminal_record_is_not_promoted(self):
        self.session.variables[agents.RESUME_VAR] = json.dumps(record(recipe="clor"))
        self.install_launch()
        await self.capture([row()])
        self.assertEqual(self.scheduled, [])
        with self.assertRaisesRegex(ValueError, "unsigned"):
            await self.service.save(self.window, "test")

    async def test_failed_repair_aborts_save_without_nesting_then_recovers(self):
        self.session.settings = {
            "Command": agents.resume_command(self.saved_record, "/python", "/helper"),
            "Custom Command": "Yes",
        }
        self.session.fail_repair = True
        with self.assertRaisesRegex(ValueError, "repair is pending"):
            await self.service.save(self.window, "test")
        self.assertEqual(self.window.saved, None)
        await self.service.save(self.window, "test")
        self.assertEqual(
            agents.command_record(self.window.saved["Command"])["original"],
            record()["original"],
        )

    async def test_rename_releases_the_old_arrangement_name(self):
        await self.service.save(self.window, "test")
        self.window.title = "renamed"
        second = Window(Session(), self.connection, "two")
        self.app.windows.append(second)
        await self.service.save(second, "test")
        self.assertEqual(self.service.owners["test"], "two")

    async def test_many_events_keep_one_active_save_and_one_followup(self):
        import SaveWindowArrangement as daemon

        daemon.app = self.app
        daemon.DEBOUNCE_SECONDS = 0.001
        started = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def save(*_, **__):
            calls.append(True)
            started.set()
            await release.wait()

        try:
            with patch.object(daemon, "save_window", save):
                daemon.schedule_save("one")
                await asyncio.wait_for(started.wait(), 1)
                for _ in range(100):
                    daemon.schedule_save("one")
                self.assertEqual(len(daemon._debounce), 1)
                self.assertEqual(len(calls), 1)
                release.set()
                await asyncio.wait_for(daemon._debounce["one"], 1)
                self.assertEqual(len(calls), 2)
        finally:
            sys.modules.pop("SaveWindowArrangement", None)


if __name__ == "__main__":
    unittest.main()
