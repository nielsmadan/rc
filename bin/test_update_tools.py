import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("update-tools")
TOOLS = {
    name: []
    for name in (
        "node", "python", "npm:agent-browser", "npm:agent-device",
        "aqua:hashicorp/vault", "pipx", "pipx:llm",
    )
}

MOCK = """import json, os, sys
from pathlib import Path
command = [Path(sys.argv[0]).name, *sys.argv[1:]]
with open(os.environ['UPDATE_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps({'command': command, 'cwd': os.getcwd()}) + '\\n')
if command == json.loads(os.environ.get('UPDATE_TEST_FAIL', 'null')):
    print('simulated failure', file=sys.stderr)
    sys.exit(int(os.environ.get('UPDATE_TEST_STATUS', '17')))
if command == ['mise', 'ls', '--current', '--json']:
    print(os.environ['UPDATE_TEST_TOOLS'])
"""


class UpdateToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.project = root / "project"
        self.project.mkdir()
        self.log = root / "commands.jsonl"
        self.env = {
            **os.environ,
            "PATH": str(self.bin),
            "UPDATE_TEST_LOG": str(self.log),
            "UPDATE_TEST_TOOLS": json.dumps(TOOLS),
        }
        (self.bin / "python3").symlink_to(sys.executable)
        for name in ("mise", "brew", "uv", "pipx", "agent-browser"):
            path = self.bin / name
            path.write_text(f"#!{sys.executable}\n{MOCK}")
            path.chmod(0o755)

    def run_script(self, *args):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, cwd=self.project, capture_output=True, text=True, timeout=15,
        )
        records = (
            [json.loads(line) for line in self.log.read_text().splitlines()]
            if self.log.exists() else []
        )
        return result, records

    def test_preview_runs_only_inventory_and_prints_updates(self):
        result, records = self.run_script("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [r["command"] for r in records], [["mise", "ls", "--current", "--json"]]
        )
        self.assertIn("brew upgrade --cask --greedy", result.stdout)
        self.assertIn("mise exec -- agent-browser install", result.stdout)
        self.assertIn("Preview complete; no updates were run.", result.stdout)

    def test_updates_global_tools_and_preserves_runtime_requests(self):
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r["command"] for r in records]
        self.assertIn(
            ["mise", "upgrade", "--yes", "--bump", "npm:agent-browser",
             "npm:agent-device", "pipx", "pipx:llm"], commands,
        )
        self.assertIn(["mise", "upgrade", "--yes", "node", "python"], commands)
        self.assertIn(["mise", "upgrade", "--yes", "aqua:hashicorp/vault"], commands)
        self.assertIn(["uv", "tool", "upgrade", "--all"], commands)
        self.assertIn(["mise", "exec", "--", "pipx", "upgrade-all"], commands)
        self.assertIn(["mise", "exec", "--", "agent-browser", "install"], commands)
        self.assertEqual({r["cwd"] for r in records}, {str(Path.home().resolve())})

    def test_runtime_bump_keeps_vault_pin(self):
        result, records = self.run_script("--bump-runtimes")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r["command"] for r in records]
        self.assertIn(["mise", "upgrade", "--yes", "--bump", "node", "python"], commands)
        vault_upgrades = [c for c in commands if "aqua:hashicorp/vault" in c]
        self.assertEqual(vault_upgrades, [["mise", "upgrade", "--yes", "aqua:hashicorp/vault"]])

    def test_failed_brew_refresh_skips_its_upgrades_and_continues(self):
        self.env["UPDATE_TEST_FAIL"] = json.dumps(["brew", "update"])
        result, records = self.run_script()
        self.assertEqual(result.returncode, 1)
        commands = [r["command"] for r in records]
        self.assertEqual([c for c in commands if c[0] == "brew"], [["brew", "update"]])
        self.assertIn(["uv", "tool", "upgrade", "--all"], commands)
        self.assertIn(["mise", "exec", "--", "agent-browser", "install"], commands)
        self.assertIn("Failed steps:\n  brew update", result.stderr)

    def test_failed_formula_upgrade_still_updates_casks(self):
        self.env["UPDATE_TEST_FAIL"] = json.dumps(["brew", "upgrade", "--formula"])
        result, records = self.run_script()
        self.assertEqual(result.returncode, 1)
        commands = [r["command"] for r in records]
        self.assertIn(["brew", "upgrade", "--cask", "--greedy"], commands)
        self.assertIn(["uv", "tool", "upgrade", "--all"], commands)
        self.assertIn("Failed steps:\n  brew upgrade --formula", result.stderr)

    def test_empty_inventory_does_not_upgrade_all_mise_tools(self):
        self.env["UPDATE_TEST_TOOLS"] = "{}"
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [r["command"] for r in records]
        self.assertEqual([c for c in commands if c[:2] == ["mise", "upgrade"]], [])
        self.assertIn(["pipx", "upgrade-all"], commands)
        self.assertIn(["agent-browser", "install"], commands)

    def test_interrupt_stops_remaining_updates(self):
        self.env["UPDATE_TEST_FAIL"] = json.dumps(["brew", "update"])
        self.env["UPDATE_TEST_STATUS"] = "130"
        result, records = self.run_script()
        self.assertEqual(result.returncode, 130)
        self.assertEqual(records[-1]["command"], ["brew", "update"])

    def test_runtime_only_inventory_handles_empty_cli_group(self):
        self.env["UPDATE_TEST_TOOLS"] = json.dumps({"node": []})
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        upgrades = [r["command"] for r in records if r["command"][:2] == ["mise", "upgrade"]]
        self.assertEqual(upgrades, [["mise", "upgrade", "--yes", "node"]])

    def test_failed_inventory_is_reported_and_other_managers_continue(self):
        self.env["UPDATE_TEST_FAIL"] = json.dumps(["mise", "ls", "--current", "--json"])
        result, records = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Failed steps:\n  read global mise tools", result.stderr)
        self.assertIn(["brew", "update"], [r["command"] for r in records])

    def test_missing_managers_are_skipped(self):
        for name in ("mise", "brew", "uv", "pipx", "agent-browser"):
            (self.bin / name).unlink()
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(records, [])
        self.assertIn("skip mise (not installed)", result.stdout)
        self.assertIn("skip Homebrew (not installed)", result.stdout)

    def test_unknown_option_exits_before_running_commands(self):
        result, records = self.run_script("--bogus")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(records, [])
        self.assertIn("unknown option: --bogus", result.stderr)


if __name__ == "__main__":
    unittest.main()
