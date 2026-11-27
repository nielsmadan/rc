import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("studio-ship")

# Records each call; fails the call whose arguments contain $STUDIO_TEST_FAIL.
SSH = """#!/bin/sh
echo "$*" >> "$STUDIO_TEST_LOG"
case "$*" in *"$STUDIO_TEST_FAIL"*) [ -n "$STUDIO_TEST_FAIL" ] && exit 1 ;; esac
exit 0
"""


class StudioShipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ssh = self.tmp / "ssh"
        self.ssh.write_text(SSH)
        self.ssh.chmod(0o755)
        self.log = self.tmp / "log"
        self.log.write_text("")

    def run_ship(self, *args, fail=""):
        environment = dict(
            os.environ,
            STUDIO_SHIP_SSH=str(self.ssh),
            STUDIO_TEST_LOG=str(self.log),
            STUDIO_TEST_FAIL=fail,
        )
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, env=environment, timeout=10
        )

    def calls(self):
        return self.log.read_text().splitlines()

    def test_pushes_then_deploys_rc_and_ac_in_order(self):
        result = self.run_ship("rc", "ac")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            "-A studio cd ~/wrksp/rc/dev1 && git push",
            "studio zsh -lc 'studio-deploy rc'",
            "-A studio cd ~/wrksp/ac/dev1 && git push",
            "studio zsh -lc 'studio-deploy ac'",
        ])

    def test_only_pushes_a_repo_studio_deploy_does_not_know(self):
        result = self.run_ship("agents")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["-A studio cd ~/wrksp/agents/dev1 && git push"])

    def test_a_failed_push_stops_before_its_deploy(self):
        result = self.run_ship("rc", "ac", fail="rc/dev1 && git push")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.calls(), ["-A studio cd ~/wrksp/rc/dev1 && git push"])

    def test_refuses_a_repo_name_that_could_reach_the_remote_shell(self):
        result = self.run_ship("rc", "x; rm -rf ~")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid repo name", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_needs_at_least_one_repo(self):
        result = self.run_ship()
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage: studio-ship", result.stderr)


if __name__ == "__main__":
    unittest.main()
