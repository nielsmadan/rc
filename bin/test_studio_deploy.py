import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("studio-deploy")

LOGGER = """#!/bin/sh
echo "$(basename "$0") $*" >> "$STUDIO_TEST_LOG"
exit "${STUDIO_TEST_STATUS:-0}"
"""

SUDO = """#!/bin/sh
echo "sudo $*" >> "$STUDIO_TEST_LOG"
[ "$2" = -u ] || exit 0
shift 3
exec "$@"
"""

# Loaded agents, outside the console session.
LAUNCHCTL = """#!/bin/sh
echo "launchctl $*" >> "$STUDIO_TEST_LOG"
[ "$1" = managername ] && echo Background
exit 0
"""

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]

# Stands in for a checkout that changes the watchdog's program.
CHANGING_CHECKOUT = """#!/bin/sh
echo "studio-checkout $*" >> "$STUDIO_TEST_LOG"
cd "$RC_DEPLOY_ROOT/rc" && echo "# changed" >> bin/colima-watchdog &&
  git -c user.name=t -c user.email=t@example.com commit --quiet -am change
"""


class StudioDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.opt = root / "opt"
        self.log = root / "log"
        stubs = root / "stubs"
        for path, body in [
            (self.opt / "rc/bin/studio-checkout", LOGGER),
            (self.opt / "rc/install.sh", LOGGER),
            (self.opt / "ac/sync.sh", LOGGER),
            (self.opt / "ac/bin/fleet-sync", LOGGER),
            (stubs / "sudo", SUDO),
            (stubs / "launchctl", LAUNCHCTL),
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
            path.chmod(0o755)
        self.env = {
            "PATH": f"{stubs}:/usr/bin:/bin",
            "RC_DEPLOY_ROOT": str(self.opt),
            "STUDIO_TEST_LOG": str(self.log),
        }

    def run_script(self, *args):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_ac_checks_out_as_deploy_then_renders_both_profiles(self):
        result, calls = self.run_script("ac", "abc123")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            f"sudo -n -u deploy {self.opt}/rc/bin/studio-checkout ac abc123",
            "studio-checkout ac abc123",
            "sync.sh --profile studio",
            "fleet-sync ",
        ])

    def test_rc_rollback_reruns_install(self):
        result, calls = self.run_script("--rollback", "rc")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1:], ["studio-checkout --rollback rc", "install.sh "])

    def test_failed_checkout_renders_nothing(self):
        self.env["STUDIO_TEST_STATUS"] = "1"
        result, calls = self.run_script("ac")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls[-1], "studio-checkout ac")

    def test_rc_reloads_a_loaded_agent_whose_program_changed_through_the_helper(self):
        rc = self.opt / "rc"
        for name in ["launchd/com.nielsmadan.colima-watchdog.plist",
                     "launchd/com.nielsmadan.resource-log.plist", "bin/colima-watchdog"]:
            (rc / name).parent.mkdir(parents=True, exist_ok=True)
            (rc / name).write_text("v1\n")
        (rc / "bin/studio-checkout").write_text(CHANGING_CHECKOUT)
        subprocess.run(["git", "init", "--quiet", str(rc)], check=True)
        subprocess.run([*GIT, "-C", str(rc), "add", "-A"], check=True)
        subprocess.run([*GIT, "-C", str(rc), "commit", "--quiet", "-m", "v1"], check=True)
        result, calls = self.run_script("rc")
        self.assertEqual(result.returncode, 0, result.stderr)
        uid = os.getuid()
        self.assertEqual(calls[1:], [
            "studio-checkout rc",
            "install.sh ",
            f"launchctl print gui/{uid}/com.nielsmadan.colima-watchdog",
            "launchctl managername",
            "sudo -n /usr/local/libexec/studio-load-agent reload com.nielsmadan.colima-watchdog",
        ])

    def test_status_only_asks_the_checkout(self):
        result, calls = self.run_script("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1:], ["studio-checkout --status"])


if __name__ == "__main__":
    unittest.main()
