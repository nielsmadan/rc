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


class TestNextSiblingName(unittest.TestCase):
    def test_no_trailing_number_appends_2(self):
        self.assertEqual(lib.next_sibling_name("rc"), "rc2")

    def test_trailing_number_increments(self):
        self.assertEqual(lib.next_sibling_name("app3"), "app4")

    def test_multidigit_trailing_number_increments(self):
        self.assertEqual(lib.next_sibling_name("app10"), "app11")


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


def touch(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w"):
        pass


class TestFindEnvFiles(unittest.TestCase):
    def test_empty_repo_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lib.find_env_files(d), [])

    def test_root_env_only(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, ".env"))
            self.assertEqual(lib.find_env_files(d), [".env"])

    def test_nested_env_files_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, ".env"))
            touch(os.path.join(d, "server", ".env"))
            touch(os.path.join(d, "apps", "web", ".env"))
            self.assertEqual(
                lib.find_env_files(d),
                [".env", "apps/web/.env", "server/.env"],
            )

    def test_skips_git_dir(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, ".git", ".env"))
            touch(os.path.join(d, ".env"))
            self.assertEqual(lib.find_env_files(d), [".env"])

    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, "node_modules", "pkg", ".env"))
            touch(os.path.join(d, "server", ".env"))
            self.assertEqual(lib.find_env_files(d), ["server/.env"])

    def test_skips_virtualenvs_and_pycache(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, ".venv", ".env"))
            touch(os.path.join(d, "venv", ".env"))
            touch(os.path.join(d, "__pycache__", ".env"))
            self.assertEqual(lib.find_env_files(d), [])

    def test_does_not_match_env_prefix_files(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, ".env.local"))
            touch(os.path.join(d, ".envrc"))
            self.assertEqual(lib.find_env_files(d), [])


if __name__ == "__main__":
    unittest.main()
