import json
from io import StringIO
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("check-runtimes")
MODULE = runpy.run_path(str(SCRIPT))
MOCK = """import json, os, sys
from pathlib import Path
command = [Path(sys.argv[0]).name, *sys.argv[1:]]
with open(os.environ['RUNTIME_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps({'command': command, 'cwd': os.getcwd()}) + '\\n')
if command == ['mise', 'ls', '--global', '--json']:
    print(os.environ['RUNTIME_TEST_INVENTORY'])
elif command[:2] == ['mise', 'latest'] and len(command) == 3:
    response = json.loads(os.environ['RUNTIME_TEST_VERSIONS']).get(command[2])
    if response is None:
        print('simulated lookup failure', file=sys.stderr)
        sys.exit(1)
    print(response)
elif command[0] == 'curl':
    response = json.loads(os.environ['RUNTIME_TEST_METADATA']).get(command[-1])
    if response is None:
        print('simulated metadata failure', file=sys.stderr)
        sys.exit(1)
    print(response)
elif command == ['deno', '--version']:
    print('deno 2.9.6 (' + os.environ.get('RUNTIME_TEST_DENO_CHANNEL', 'stable') + ', release, aarch64-apple-darwin)')
else:
    print('unexpected command: ' + repr(command), file=sys.stderr)
    sys.exit(99)
"""


def record(version, requested=None, installed=True):
    return {"version": version, "requested_version": requested or version, "installed": installed}


class CheckRuntimesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.project = root / "project"
        self.project.mkdir()
        self.log = root / "commands.jsonl"
        self.inventory = {
            "node": [record("22.1.0", "22")],
            "java": [record("zulu-17.1.0.0", "zulu-17")],
            "python": [record("3.14.5")],
            "pnpm": [record("10.0.0")],
        }
        self.versions = {
            "node@latest": "26.8.2",
            "java@zulu": "zulu-26.32.203.0", "java@zulu-25": "zulu-25.36.205.0",
            "python@latest": "3.14.7",
        }
        self.metadata = {
            "https://nodejs.org/dist/index.json": json.dumps([
                {"version": "v26.8.2", "lts": False},
                {"version": "v22.1.0", "lts": "Jod"},
                {"version": "v24.21.0", "lts": "Krypton"},
            ]),
            "https://api.adoptium.net/v3/info/available_releases": json.dumps({
                "most_recent_lts": 25, "available_lts_releases": [8, 11, 17, 21, 25],
            }),
        }
        self.env = {**os.environ, "PATH": str(self.bin), "RUNTIME_TEST_LOG": str(self.log)}
        for name in ("mise", "curl", "deno"):
            path = self.bin / name
            path.write_text(f"#!{sys.executable}\n{MOCK}")
            path.chmod(0o755)

    def run_script(self, *args, raw_inventory=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=self.project, timeout=15,
            capture_output=True, text=True,
            env={
                **self.env,
                "RUNTIME_TEST_INVENTORY": raw_inventory if raw_inventory is not None else json.dumps(self.inventory),
                "RUNTIME_TEST_VERSIONS": json.dumps(self.versions),
                "RUNTIME_TEST_METADATA": json.dumps(self.metadata),
            },
        )
        records = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, records

    def test_reports_major_updates_and_lts_using_only_metadata_queries(self):
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("26.8.2 NEW", result.stdout)
        self.assertIn("24.21.0 [LTS] NEW", result.stdout)
        self.assertIn("zulu-25.36.205.0 [LTS] NEW", result.stdout)
        self.assertIn("3 configured runtime version(s) have newer releases", result.stdout)
        self.assertEqual({r["cwd"] for r in records}, {str(Path.home().resolve())})
        self.assertEqual(
            sorted(r["command"] for r in records),
            sorted([
                ["mise", "ls", "--global", "--json"],
                *[["mise", "latest", selector] for selector in self.versions],
                *[["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "20", url]
                  for url in self.metadata],
            ]),
        )

    def test_older_lts_is_an_option_without_claiming_an_update(self):
        self.inventory = {"node": [record("26.8.2")]}
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        row = next(line for line in result.stdout.splitlines() if line.startswith("node "))
        self.assertEqual(row.split(), ["node", "26.8.2", "26.8.2", "26.8.2", "24.21.0", "[LTS]", "off", "lts"])
        self.assertIn("No newer releases available", result.stdout)

    def test_failed_stable_lookup_keeps_lts_and_other_runtime_results(self):
        del self.versions["node@latest"]
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("24.21.0 [LTS] NEW", result.stdout)
        self.assertIn("3.14.7 NEW", result.stdout)
        self.assertIn("unknown", result.stdout)
        self.assertIn("Check incomplete:", result.stderr)
        self.assertIn("node stable:", result.stderr)

    def test_failed_lts_metadata_does_not_hide_stable_release(self):
        self.metadata = {}
        result, _ = self.run_script("java")
        self.assertEqual(result.returncode, 1)
        self.assertIn("zulu-26.32.203.0 NEW", result.stdout)
        self.assertIn("unknown", result.stdout)
        self.assertIn("java LTS:", result.stderr)

    def test_explicit_runtime_selection_limits_queries(self):
        result, records = self.run_script("python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["command"] for r in records], [
            ["mise", "ls", "--global", "--json"], ["mise", "latest", "python@latest"],
        ])
        self.assertIn("3.14.7 NEW", result.stdout)

    def test_deno_lts_channel_is_shown_separately(self):
        self.inventory = {"deno": [record("2.9.6", "latest")]}
        self.inventory["deno"][0]["install_path"] = str(self.bin.parent)
        self.versions = {"deno@latest": "2.9.6"}
        self.metadata = {"https://dl.deno.land/release-lts-latest.txt": "v2.9.3\n"}
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2.9.3 [LTS]", result.stdout)
        self.assertIn("off lts", result.stdout)
        self.assertIn("No newer releases available", result.stdout)

    def test_deno_lts_build_is_identified_from_installed_channel(self):
        self.inventory = {"deno": [record("2.9.6", "latest")]}
        self.inventory["deno"][0]["install_path"] = str(self.bin.parent)
        self.versions = {"deno@latest": "2.9.6"}
        self.metadata = {"https://dl.deno.land/release-lts-latest.txt": "v2.9.3\n"}
        self.env["RUNTIME_TEST_DENO_CHANNEL"] = "lts"
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("latest lts", result.stdout)
        self.assertIn(["deno", "--version"], [r["command"] for r in records])

    def test_status_uses_release_metadata_and_numeric_version_comparisons(self):
        self.inventory["bun"] = [record("1.4.2")]
        self.inventory["ruby"] = [record("3.1.2")]
        self.inventory["rust"] = [record("1.93.1")]
        self.versions.update({"bun@latest": "1.4.2", "ruby@latest": "4.0.6", "rust@latest": "1.98.1"})
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        statuses = {
            parts[0]: parts[-1] for line in result.stdout.splitlines()
            if len(parts := re.split(r"\s{2,}", line)) == 6
        }
        self.assertEqual(statuses, {
            "Runtime": "Status", "bun": "up to date", "java": "older lts",
            "node": "older lts", "python": "patch behind", "ruby": "major behind", "rust": "minor behind",
        })

    def test_dotnet_chooses_newest_supported_lts_sdk_numerically(self):
        self.inventory = {"dotnet": [record("8.0.100")]}
        self.versions = {"dotnet@latest": "10.0.401"}
        channels = [
            {"latest-sdk": "8.0.999", "release-type": "lts", "support-phase": "maintenance", "eol-date": "2099-01-01"},
            {"latest-sdk": "12.0.100-preview.1", "release-type": "lts", "support-phase": "preview"},
            {"latest-sdk": "12.0.100-rc.1", "release-type": "lts", "support-phase": "go-live"},
            {"latest-sdk": "10.0.401", "release-type": "lts", "support-phase": "active", "eol-date": "2099-01-01"},
        ]
        self.metadata = {
            "https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json": json.dumps({"releases-index": channels}),
        }
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("10.0.401 [LTS] NEW", result.stdout)

    def test_missing_installation_is_reported(self):
        self.inventory = {"python": [record("3.14.5", installed=False)]}
        result, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not installed", result.stdout)
        self.assertIn("3.14.7", result.stdout)

    def test_prerelease_or_malformed_latest_is_a_failed_check(self):
        self.versions["python@latest"] = "3.15.0rc1"
        result, _ = self.run_script("python")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown", result.stdout)
        self.assertIn("cannot compare version", result.stderr)

    def test_empty_inventory_only_runs_inventory(self):
        self.inventory = {}
        result, records = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No global mise runtimes configured.", result.stdout)
        self.assertEqual([r["command"] for r in records], [["mise", "ls", "--global", "--json"]])

    def test_bad_inventory_fails_before_release_queries(self):
        result, records = self.run_script(raw_inventory="bad JSON")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Check failed:", result.stderr)
        self.assertEqual([r["command"] for r in records], [["mise", "ls", "--global", "--json"]])

    def test_unknown_runtime_fails_before_any_commands(self):
        result, records = self.run_script("pnpm")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown runtime(s): pnpm", result.stderr)
        self.assertEqual(records, [])

    def test_help_runs_no_commands(self):
        result, records = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("without installing updates or changing pins", " ".join(result.stdout.split()))
        self.assertEqual(records, [])


class RuntimeStatusTests(unittest.TestCase):
    def test_lts_status_tracks_lines_including_a_patch_behind(self):
        cases = [
            ("node", "24.20.0", "24.21.0", {(22,), (24,)}, None, "latest lts"),
            ("node", "22.1.0", "24.21.0", {(22,), (24,)}, None, "older lts"),
            ("node", "26.8.2", "24.21.0", {(22,), (24,)}, None, "off lts"),
            ("java", "zulu-25.30.0.0", "zulu-25.36.205.0", {(17,), (25,)}, None, "latest lts"),
            ("java", "zulu-17.68.203.0", "zulu-25.36.205.0", {(17,), (25,)}, None, "older lts"),
            ("java", "zulu-26.32.203.0", "zulu-25.36.205.0", {(17,), (25,)}, None, "off lts"),
            ("deno", "2.8.3", "2.9.3", {(2, 9)}, "lts", "older lts"),
            ("deno", "2.9.3", "2.9.3", {(2, 9)}, "stable", "off lts"),
            ("dotnet", "8.0.100", "10.0.401", {(8, 0), (10, 0)}, None, "older lts"),
        ]
        for tool, installed, lts, lines, channel, expected in cases:
            with self.subTest(tool=tool, installed=installed, channel=channel):
                self.assertEqual(MODULE["runtime_status"](tool, installed, None, lts, lines, channel), expected)

    def test_stable_status_uses_largest_changed_component(self):
        cases = [
            ("3.14.7", "3.14.7", "up to date"),
            ("3.14.8", "3.14.7", "up to date"),
            ("3.14.5", "3.14.7", "patch behind"),
            ("3.9.9", "3.14.7", "minor behind"),
            ("2.99.99", "3.14.7", "major behind"),
        ]
        for installed, latest, expected in cases:
            with self.subTest(installed=installed, latest=latest):
                self.assertEqual(MODULE["runtime_status"]("python", installed, latest, None, set()), expected)

    def test_failed_metadata_leaves_status_unknown(self):
        self.assertEqual(MODULE["runtime_status"]("node", "24.21.0", "26.8.2", None, set()), "unknown")
        self.assertEqual(MODULE["runtime_status"]("python", "3.14.7", None, None, set()), "unknown")

    def test_status_colors_and_plain_text_output(self):
        expected = {
            "latest lts": "32", "older lts": "33", "off lts": "33", "up to date": "32",
            "patch behind": "92", "minor behind": "33", "major behind": "31",
        }
        rows = [[f"tool{i}", "latest", "1.0.0", "2.0.0", "—", status] for i, status in enumerate(expected)]
        for tty, no_color in [(True, False), (False, False), (True, True)]:
            with self.subTest(tty=tty, no_color=no_color):
                output = StringIO()
                with patch.dict(os.environ), patch("sys.stdout", output), patch.object(output, "isatty", return_value=tty):
                    os.environ.pop("NO_COLOR", None)
                    if no_color:
                        os.environ["NO_COLOR"] = "1"
                    MODULE["print_table"](rows)
                lines = output.getvalue().splitlines()[1:]
                for line, (status, code) in zip(lines, expected.items()):
                    marker = f"\033[{code}m{status}\033[0m" if tty and not no_color else status
                    self.assertEqual(re.split(r"\s{2,}", line)[-1], marker)


if __name__ == "__main__":
    unittest.main()
