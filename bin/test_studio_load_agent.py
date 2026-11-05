import getpass
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("studio-load-agent")
LABEL = "com.nielsmadan.colima-watchdog"

LAUNCHCTL = """#!/bin/sh
echo "launchctl $*" >> "$STUB_LOG"
if [ "$1" = print ]; then [ -n "$STUB_LOADED" ]; exit; fi
exit "${STUB_STATUS:-0}"
"""


class StudioLoadAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.plists = root / "launchd"
        self.plists.mkdir(mode=0o755)
        self.plist = self.plists / f"{LABEL}.plist"
        self.plist.write_text("<plist/>\n")
        self.plist.chmod(0o644)
        self.log = root / "log"
        launchctl = root / "launchctl"
        launchctl.write_text(LAUNCHCTL)
        launchctl.chmod(0o755)
        self.uid = str(os.getuid())
        self.helper = root / "studio-load-agent"
        self.write_helper(trusted=f"root {getpass.getuser()}", launchctl=launchctl)
        self.env = {"PATH": "/usr/bin:/bin", "SUDO_UID": self.uid, "STUB_LOG": str(self.log)}

    def write_helper(self, trusted, launchctl):
        text = SCRIPT.read_text()
        for old, new in [
            ("PLIST_DIR=/opt/rc/launchd", f"PLIST_DIR={self.plists}"),
            ('TRUSTED_OWNERS="root deploy"', f'TRUSTED_OWNERS="{trusted}"'),
            ("LAUNCHCTL=/bin/launchctl", f"LAUNCHCTL={launchctl}"),
            ("REQUIRED_EUID=0", f"REQUIRED_EUID={os.getuid()}"),
        ]:
            self.assertEqual(text.count(old), 1, old)
            text = text.replace(old, new)
        self.helper.write_text(text)
        self.helper.chmod(0o755)

    def run_helper(self, *args):
        result = subprocess.run(
            ["/bin/bash", str(self.helper), *args],
            env=self.env, capture_output=True, text=True, timeout=15,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_load_bootstraps_the_fixed_plist_into_the_callers_gui_domain(self):
        result, calls = self.run_helper("load", LABEL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            f"launchctl print gui/{self.uid}/{LABEL}",
            f"launchctl bootstrap gui/{self.uid} {self.plist}",
        ])

    def test_load_leaves_a_loaded_agent_alone(self):
        self.env["STUB_LOADED"] = "1"
        result, calls = self.run_helper("load", LABEL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already loaded", result.stdout)
        self.assertEqual(calls, [f"launchctl print gui/{self.uid}/{LABEL}"])

    def test_reload_boots_out_then_bootstraps(self):
        self.env["STUB_LOADED"] = "1"
        result, calls = self.run_helper("reload", LABEL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            f"launchctl print gui/{self.uid}/{LABEL}",
            f"launchctl bootout gui/{self.uid}/{LABEL}",
            f"launchctl bootstrap gui/{self.uid} {self.plist}",
        ])

    def test_a_failed_bootstrap_exits_1(self):
        self.env["STUB_STATUS"] = "5"
        result, _ = self.run_helper("load", LABEL)
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not bootstrap", result.stderr)

    def assert_refused(self, args, status, message):
        result, calls = self.run_helper(*args)
        self.assertEqual(result.returncode, status, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertEqual(calls, [])

    def test_refuses_a_label_outside_the_list(self):
        self.assert_refused(["load", "com.example.evil"], 2, "usage:")

    def test_refuses_a_path_given_as_the_label(self):
        self.assert_refused(["load", str(self.plist)], 2, "usage:")

    def test_refuses_an_unknown_action(self):
        self.assert_refused(["bootstrap", LABEL], 2, "usage:")

    def test_refuses_a_missing_sudo_uid(self):
        del self.env["SUDO_UID"]
        self.assert_refused(["load", LABEL], 1, "SUDO_UID is not a uid")

    def test_refuses_a_sudo_uid_that_is_not_a_number(self):
        self.env["SUDO_UID"] = "501; id"
        self.assert_refused(["load", LABEL], 1, "SUDO_UID is not a uid")

    def test_refuses_root(self):
        self.env["SUDO_UID"] = "0"
        self.assert_refused(["load", LABEL], 1, "root has no agents")

    def test_refuses_a_uid_with_no_user(self):
        self.env["SUDO_UID"] = "4242424"
        self.assert_refused(["load", LABEL], 1, "no user with uid 4242424")

    def test_refuses_a_plist_others_can_write(self):
        self.plist.chmod(0o646)
        self.assert_refused(["load", LABEL], 1, "writable by group or others (646)")

    def test_refuses_a_plist_dir_the_group_can_write(self):
        self.plists.chmod(0o775)
        self.assert_refused(["load", LABEL], 1, "writable by group or others (775)")

    def test_refuses_a_symlinked_plist(self):
        real = self.plists / "real.plist"
        self.plist.rename(real)
        self.plist.symlink_to(real)
        self.assert_refused(["load", LABEL], 1, "is a symlink")

    def test_refuses_a_plist_owned_by_someone_untrusted(self):
        self.write_helper(trusted="root deploy", launchctl=self.helper.parent / "launchctl")
        self.assert_refused(["load", LABEL], 1, f"belongs to {getpass.getuser()}")

    def test_refuses_to_run_without_root(self):
        text = self.helper.read_text().replace(f"REQUIRED_EUID={os.getuid()}", "REQUIRED_EUID=0")
        self.helper.write_text(text)
        self.assert_refused(["load", LABEL], 1, "run it through sudo")


if __name__ == "__main__":
    unittest.main()
