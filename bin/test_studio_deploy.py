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
shift 3
exec "$@"
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

    def test_status_only_asks_the_checkout(self):
        result, calls = self.run_script("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1:], ["studio-checkout --status"])


if __name__ == "__main__":
    unittest.main()
