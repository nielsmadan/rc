"""unittest tests for clone_repo_lib.

Run: python3 iterm2/test_clone_repo_lib.py
"""

import os
import subprocess
import tempfile
import unittest

import clone_repo_lib as lib


def make_repo(parent: str, name: str, with_origin: bool = True) -> str:
    """Initialise a throwaway git repo under parent/name, returning its path."""
    path = os.path.join(parent, name)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", path], check=True)
    # Make at least one commit so HEAD exists (clone needs a branch).
    subprocess.run(
        ["git", "-C", path, "commit", "--allow-empty", "-q", "-m", "init"],
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
        check=True,
    )
    if with_origin:
        subprocess.run(
            ["git", "-C", path, "remote", "add", "origin", f"file://{path}"],
            check=True,
        )
    return path


class TestSuggestName(unittest.TestCase):
    def test_no_trailing_number_appends_2(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lib.suggest_name("rc", d), "rc2")

    def test_trailing_number_increments(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lib.suggest_name("app3", d), "app4")

    def test_multidigit_trailing_number_increments(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lib.suggest_name("app10", d), "app11")

    def test_skips_existing_sibling(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "rc2"))
            self.assertEqual(lib.suggest_name("rc", d), "rc3")

    def test_skips_multiple_existing_siblings(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "rc2"))
            os.makedirs(os.path.join(d, "rc3"))
            self.assertEqual(lib.suggest_name("rc", d), "rc4")

    def test_skips_existing_when_basename_has_number(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "app4"))
            self.assertEqual(lib.suggest_name("app3", d), "app5")


class TestResolveRepoRoot(unittest.TestCase):
    def test_root_returns_self(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(d, "r")
            self.assertEqual(lib.resolve_repo_root(repo), os.path.realpath(repo))

    def test_subdir_returns_root(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(d, "r")
            sub = os.path.join(repo, "a", "b")
            os.makedirs(sub)
            self.assertEqual(lib.resolve_repo_root(sub), os.path.realpath(repo))

    def test_non_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(lib.resolve_repo_root(d))


class TestResolveOriginUrl(unittest.TestCase):
    def test_returns_origin_url(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(d, "r", with_origin=True)
            self.assertEqual(lib.resolve_origin_url(repo), f"file://{repo}")

    def test_no_origin_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            repo = make_repo(d, "r", with_origin=False)
            self.assertIsNone(lib.resolve_origin_url(repo))

    def test_non_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(lib.resolve_origin_url(d))


class TestComputeDestination(unittest.TestCase):
    def test_sibling_of_repo_root(self):
        self.assertEqual(
            lib.compute_destination("/Users/x/wrksp/myapp", "myapp2"),
            "/Users/x/wrksp/myapp2",
        )

    def test_strips_trailing_slash(self):
        self.assertEqual(
            lib.compute_destination("/Users/x/wrksp/myapp/", "newname"),
            "/Users/x/wrksp/newname",
        )


if __name__ == "__main__":
    unittest.main()
