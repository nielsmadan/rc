import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("studio-checkout")


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"},
    ).stdout.strip()


class StudioCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.opt = root / "opt"
        (self.opt / "ac").mkdir(parents=True)
        (self.opt / "rc").mkdir(parents=True)
        origins = self.origins = root / "origins"
        work = self.work = root / "work"
        git("init", "--quiet", "--bare", "--initial-branch=main", str(origins / "agentic-coding.git"))
        git("clone", "--quiet", str(origins / "agentic-coding.git"), str(work))
        git("config", "user.email", "t@example.com", cwd=work)
        git("config", "user.name", "t", cwd=work)
        self.main = []
        for n in range(2):
            (work / "file").write_text(f"{n}\n")
            git("add", "file", cwd=work)
            git("commit", "--quiet", "-m", f"main {n}", cwd=work)
            self.main.append(git("rev-parse", "HEAD", cwd=work))
        git("push", "--quiet", "origin", "main", cwd=work)
        git("checkout", "--quiet", "-b", "side", cwd=work)
        (work / "file").write_text("side\n")
        git("commit", "--quiet", "-am", "side", cwd=work)
        self.side = git("rev-parse", "HEAD", cwd=work)
        git("push", "--quiet", "origin", "side", cwd=work)
        self.env = {
            **os.environ,
            "RC_DEPLOY_ROOT": str(self.opt),
            "STUDIO_DEPLOY_ORIGIN_BASE": f"file://{origins}",
        }

    def make_rc_origin(self):
        git("init", "--quiet", "--bare", "--initial-branch=master", str(self.origins / "rc.git"))
        work = Path(self.temp.name) / "rc-work"
        git("clone", "--quiet", str(self.origins / "rc.git"), str(work))
        git("config", "user.email", "t@example.com", cwd=work)
        git("config", "user.name", "t", cwd=work)
        git("commit", "--quiet", "--allow-empty", "-m", "master", cwd=work)
        master = git("rev-parse", "HEAD", cwd=work)
        git("push", "--quiet", "origin", "master", cwd=work)
        git("checkout", "--quiet", "-b", "main", cwd=work)
        git("commit", "--quiet", "--allow-empty", "-m", "main", cwd=work)
        main = git("rev-parse", "HEAD", cwd=work)
        git("push", "--quiet", "origin", "main", cwd=work)
        return master, main

    def run_script(self, *args):
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, capture_output=True, text=True, timeout=30,
        )

    def head(self):
        return git("rev-parse", "HEAD", cwd=self.opt / "ac")

    def test_deploys_origin_main_by_default(self):
        result = self.run_script("ac")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.head(), self.main[1])
        self.assertEqual((self.opt / "ac" / "file").read_text(), "1\n")

    def test_rollback_returns_to_the_replaced_commit(self):
        self.run_script("ac", self.main[0])
        self.run_script("ac")
        result = self.run_script("--rollback", "ac")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.head(), self.main[0])

    def test_refuses_a_commit_from_another_branch(self):
        self.run_script("ac")
        result = self.run_script("ac", self.side)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"no commit '{self.side}'", result.stderr)
        self.assertEqual(self.head(), self.main[1])

    def test_refuses_a_fetched_commit_that_main_no_longer_contains(self):
        self.run_script("ac")
        git("push", "--quiet", "--force", "origin", f"{self.main[0]}:main", cwd=self.work)
        result = self.run_script("ac", self.main[1])
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not on origin/main", result.stderr)

    def test_deploys_rc_from_its_master_branch(self):
        master, main = self.make_rc_origin()
        result = self.run_script("rc")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.opt / "rc"), master)
        refused = self.run_script("rc", main)
        self.assertEqual(refused.returncode, 1)
        self.assertIn(f"no commit '{main}'", refused.stderr)

    def test_refuses_option_like_refs_and_unknown_repos(self):
        self.assertIn("invalid ref", self.run_script("ac", "--upload-pack=x").stderr)
        self.assertIn("unknown repo or tool 'notes'", self.run_script("notes", "1.2.3").stderr)

    def test_hands_tools_to_studio_tool(self):
        self.assertIn("'latest' is not an exact version", self.run_script("claude", "latest").stderr)
        self.assertIn("claude is not deployed", self.run_script("--rollback", "claude").stderr)

    def test_status_lists_the_repos_then_the_tools(self):
        self.run_script("ac")
        result = self.run_script("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "rc: not deployed", "ac: " + git("log", "-1", "--format=%h %s", cwd=self.opt / "ac"),
            *(f"{tool}: not deployed" for tool in ("loadout", "pratfall", "hooklinesinker", "claude", "codex", "pi")),
        ])

    def test_removes_untracked_files_on_deploy(self):
        self.run_script("ac", self.main[0])
        (self.opt / "ac" / "stray").write_text("x")
        self.run_script("ac")
        self.assertEqual(sorted(p.name for p in (self.opt / "ac").iterdir()), [".git", "file"])


if __name__ == "__main__":
    unittest.main()
