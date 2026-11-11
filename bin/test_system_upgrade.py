import os
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("system-upgrade")

# Logs every call; `brew list` answers from STUB_INSTALLED and STUB_PINNED, and
# any call containing STUB_FAIL exits 1.
STUB = """#!/bin/sh
name="$(basename "$0")"
echo "$name $*" >> "$STUB_LOG"
case " $* " in *" $STUB_FAIL "*) [ -n "$STUB_FAIL" ] && exit 1 ;; esac
if [ "$name" = brew ] && [ "$1" = list ]; then
  if [ "$2" = --pinned ]; then printf '%s\\n' $STUB_PINNED; exit 0; fi
  case " $STUB_INSTALLED " in *" $3 "*) exit 0 ;; esac
  exit 1
fi
if [ "$name" = tmutil ]; then
  echo "/Volumes/.timemachine/X/$STUB_BACKUP.backup/$STUB_BACKUP.backup"
fi
exit 0
"""


def stamp(age):
    return (datetime.now() - age).strftime("%Y-%m-%d-%H%M%S")


class SystemUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.state = root / "state"
        self.state.mkdir()
        self.log = root / "log"
        stubs = root / "stubs"
        stubs.mkdir()
        for name in ("brew", "mise", "tmutil"):
            (stubs / name).write_text(STUB)
            (stubs / name).chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "STUDIO_UPGRADE_STATE": str(self.state),
            "MISE_SYSTEM_DATA_DIR": "/sys/mise",
            "STUB_LOG": str(self.log),
            "STUB_BACKUP": stamp(timedelta(minutes=30)),
            "STUB_INSTALLED": "tmux colima",
            "STUB_PINNED": "colima",
            "STUB_FAIL": "",
        }

    def run_script(self, *args):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        changes = [c for c in calls if not c.startswith(("brew list", "tmutil"))]
        return result, changes

    def test_upgrades_brew_then_the_system_mise_tools_and_records_success(self):
        result, changes = self.run_script()
        self.assertEqual(result.returncode, 0, self.read_log())
        self.assertEqual(changes, [
            "brew update",
            "brew pin tmux",
            "brew upgrade --formula --yes",
            "mise upgrade --global --no-prune --minimum-release-age 3d -x node -x npm:agent-browser",
            "mise reshim --system",
        ])
        self.assertTrue(self.state.joinpath("last-run").read_text().strip().endswith(" ok"))
        self.assertEqual(self.state.joinpath("last-success").read_text(), self.state.joinpath("last-run").read_text())

    def test_skips_without_a_recent_backup(self):
        self.env["STUB_BACKUP"] = stamp(timedelta(hours=3))
        result, changes = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(changes, [])
        self.assertIn("skipped: no recent backup", self.state.joinpath("last-run").read_text())
        self.assertFalse(self.state.joinpath("last-success").exists())

    def test_a_failed_mise_upgrade_still_reshims_and_is_recorded(self):
        self.state.joinpath("last-success").write_text("earlier ok\n")
        self.env["STUB_FAIL"] = "--no-prune"
        result, changes = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(changes[-1], "mise reshim --system")
        self.assertIn("failed: env MISE_DATA_DIR=/sys/mise", self.state.joinpath("last-run").read_text())
        self.assertEqual(self.state.joinpath("last-success").read_text(), "earlier ok\n")

    def test_skips_while_another_run_holds_the_lock(self):
        lock = self.state / "lock"
        holder = subprocess.Popen(["flock", str(lock), "sleep", "10"])
        self.addCleanup(holder.wait)
        self.addCleanup(holder.kill)
        while not subprocess.run(["flock", "-n", str(lock), "true"]).returncode:
            subprocess.run(["sleep", "0.1"])
        result, changes = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(changes, [])
        self.assertIn("skipped: locked", self.state.joinpath("last-run").read_text())

    def test_check_prints_the_steps_and_changes_nothing(self):
        result, changes = self.run_script("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(changes, [])
        self.assertIn("+ brew upgrade --formula --yes", result.stdout)
        self.assertFalse(self.state.joinpath("last-run").exists())

    def read_log(self):
        log = self.state / "upgrade.log"
        return log.read_text() if log.exists() else ""


if __name__ == "__main__":
    unittest.main()
