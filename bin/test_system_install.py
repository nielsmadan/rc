import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("system-install")

# Logs every call; runs only `tee` (the profile write), unless STUB_TEE_FAILS is set.
SUDO = """#!/bin/sh
echo "sudo $*" >> "$STUB_LOG"
if [ "$1" = tee ] && [ -z "$STUB_TEE_FAILS" ]; then exec "$@"; fi
exit 1
"""


def brew_is_ours():
    brew = shutil.which("brew") or "/opt/homebrew/bin/brew"
    if not os.access(brew, os.X_OK):
        return False
    prefix = subprocess.run([brew, "--prefix"], capture_output=True, text=True).stdout.strip()
    return bool(prefix) and os.stat(prefix).st_uid == os.getuid()


@unittest.skipUnless(brew_is_ours(), "needs a Homebrew this user owns")
class SystemInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.opt = root / "opt"
        self.opt.mkdir()
        self.profile = root / "rc-profile"
        self.log = root / "log"
        self.mise = root / "mise"
        stubs = root / "stubs"
        stubs.mkdir()
        (stubs / "sudo").write_text(SUDO)
        (stubs / "sudo").chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "HOME": str(self.home),
            "RC_DEPLOY_ROOT": str(self.opt),
            "RC_PROFILE_FILE": str(self.profile),
            "MISE_SYSTEM_DATA_DIR": str(self.mise),
            "STUB_LOG": str(self.log),
            "HOMEBREW_NO_AUTO_UPDATE": "1",
        }

    def run_script(self, *args):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, capture_output=True, text=True, timeout=120,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_check_links_a_missing_zshrc_and_passes_the_profile_to_brew(self):
        result, _ = self.run_script("--check", "--profile", "studio")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"+ ln -s {self.opt}/rc/zsh/admin.zshrc {self.home}/.zshrc", result.stdout)
        self.assertIn("+ env HOMEBREW_RC_PROFILE=studio brew bundle install", result.stdout)

    def test_check_keeps_an_existing_zshrc(self):
        (self.home / ".zshrc").write_text("# admin's own\n")
        result, _ = self.run_script("--check", "--profile", "studio")
        self.assertIn(f"skip {self.home}/.zshrc (exists; move it aside", result.stdout)

    def test_check_skips_a_zshrc_already_linked(self):
        (self.home / ".zshrc").symlink_to(self.opt / "rc/zsh/admin.zshrc")
        result, _ = self.run_script("--check", "--profile", "studio")
        self.assertIn(f"skip {self.home}/.zshrc (already linked)", result.stdout)

    def test_check_gives_admin_the_system_mise_dir_and_installs_without_sudo(self):
        result, _ = self.run_script("--check", "--profile", "studio")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"+ sudo chown -R {os.environ['USER']}:staff {self.mise}", result.stdout)
        self.assertIn(
            f"+ env MISE_CARGO_HOME={self.mise}/cargo MISE_SYSTEM_PACKAGES_SUDO=false mise install --system",
            result.stdout,
        )

    def test_check_skips_a_system_mise_dir_admin_owns(self):
        (self.mise / "installs").mkdir(parents=True)
        result, _ = self.run_script("--check", "--profile", "studio")
        self.assertIn(f"skip {self.mise} (owned by {os.environ['USER']})", result.stdout)

    def test_a_failed_profile_write_stops_before_anything_else(self):
        self.env["STUB_TEE_FAILS"] = "1"
        result, calls = self.run_script("--profile", "studio")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"could not write studio to {self.profile}", result.stderr)
        self.assertEqual(calls, [f"sudo tee {self.profile}"])

    def test_a_failed_step_stops_the_steps_after_it(self):
        result, calls = self.run_script("--profile", "studio")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.profile.read_text(), "studio\n")
        self.assertIn("system-install: stopped before the", result.stderr)
        self.assertEqual(len(calls), 2, calls)


if __name__ == "__main__":
    unittest.main()
