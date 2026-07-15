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


class TestSiblingBase(unittest.TestCase):
    def test_strips_trailing_digits(self):
        self.assertEqual(lib.sibling_base("project2"), "project")

    def test_strips_multidigit(self):
        self.assertEqual(lib.sibling_base("app10"), "app")

    def test_no_digits_unchanged(self):
        self.assertEqual(lib.sibling_base("rc"), "rc")


class TestSiblingNumber(unittest.TestCase):
    def test_trailing_digits(self):
        self.assertEqual(lib.sibling_number("project2"), 2)

    def test_multidigit(self):
        self.assertEqual(lib.sibling_number("app10"), 10)

    def test_no_digits_is_zero(self):
        self.assertEqual(lib.sibling_number("rc"), 0)


class TestIsSibling(unittest.TestCase):
    def test_same_parent_same_base(self):
        self.assertTrue(lib.is_sibling("/w/project", "/w/project2"))
        self.assertTrue(lib.is_sibling("/w/dev2", "/w/dev3"))

    def test_different_base(self):
        self.assertFalse(lib.is_sibling("/w/project2", "/w/foo3"))

    def test_different_parent(self):
        self.assertFalse(lib.is_sibling("/w/a/project", "/w/b/project2"))

    def test_ignores_trailing_slash(self):
        self.assertTrue(lib.is_sibling("/w/project/", "/w/project2"))


class TestSelectHighestSibling(unittest.TestCase):
    def test_picks_highest_open(self):
        self.assertEqual(
            lib.select_highest_sibling(
                "/w/project1", ["/w/project1", "/w/project2"]
            ),
            "/w/project2",
        )

    def test_current_is_highest_returns_current(self):
        self.assertEqual(
            lib.select_highest_sibling(
                "/w/project2", ["/w/project1", "/w/project2"]
            ),
            "/w/project2",
        )

    def test_bare_name_with_numbered_siblings(self):
        self.assertEqual(
            lib.select_highest_sibling("/w/rc", ["/w/rc", "/w/rc2", "/w/rc3"]),
            "/w/rc3",
        )

    def test_multidigit_ordering(self):
        self.assertEqual(
            lib.select_highest_sibling("/w/app2", ["/w/app2", "/w/app10"]),
            "/w/app10",
        )

    def test_ignores_non_family_candidates(self):
        self.assertEqual(
            lib.select_highest_sibling(
                "/w/project1", ["/w/foo9", "/w/other/project5", "/w/project2"]
            ),
            "/w/project2",
        )


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


class TestLefthookInstallClause(unittest.TestCase):
    def test_runs_install_when_config_present(self):
        # Drop a config file, run the snippet in a shell, assert it fires.
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, "lefthook.yml"))
            clause = lib.lefthook_install_clause()
            # Replace the real `lefthook` with a marker so the test needs no
            # lefthook binary and stays hermetic.
            script = "true" + clause.replace("lefthook install", "echo INSTALLED")
            out = subprocess.run(
                ["sh", "-c", script], cwd=d, capture_output=True, text=True
            )
            self.assertIn("INSTALLED", out.stdout)

    def test_noop_when_no_config(self):
        with tempfile.TemporaryDirectory() as d:
            clause = lib.lefthook_install_clause()
            script = "true" + clause.replace("lefthook install", "echo INSTALLED")
            out = subprocess.run(
                ["sh", "-c", script], cwd=d, capture_output=True, text=True
            )
            self.assertNotIn("INSTALLED", out.stdout)
            self.assertEqual(out.returncode, 0)

    def test_detects_each_config_name(self):
        clause = lib.lefthook_install_clause()
        for name in lib.LEFTHOOK_CONFIG_NAMES:
            with tempfile.TemporaryDirectory() as d:
                touch(os.path.join(d, name))
                script = "true" + clause.replace("lefthook install", "echo INSTALLED")
                out = subprocess.run(
                    ["sh", "-c", script], cwd=d, capture_output=True, text=True
                )
                self.assertIn("INSTALLED", out.stdout, f"missed {name}")


if __name__ == "__main__":
    unittest.main()
