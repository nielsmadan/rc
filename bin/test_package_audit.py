import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("package-audit")
loader = importlib.machinery.SourceFileLoader("package_audit", str(SCRIPT))
spec = importlib.util.spec_from_loader("package_audit", loader)
audit = importlib.util.module_from_spec(spec)
loader.exec_module(audit)


def entry(sig, managed=False, detail=""):
    return {"kind": "bin", "sig": sig, "detail": detail, "managed": managed}


class MergeTests(unittest.TestCase):
    def test_reports_new_changed_and_gone_items_and_keeps_first_seen(self):
        inventory = {"items": {
            "a": {**entry("file:1:1"), "first_seen": "t0", "changed": "t0"},
            "b": {**entry("file:1:1"), "first_seen": "t0", "changed": "t0"},
            "c": {**entry("file:1:1"), "first_seen": "t0", "changed": "t0"},
        }}
        updated, changes = audit.merge(inventory, {"a": entry("file:1:1"), "b": entry("file:2:2"), "d": entry("x")}, "t1")
        self.assertEqual([(s, p) for s, p, _ in changes], [("changed", "b"), ("new", "d"), ("gone", "c")])
        self.assertEqual(updated["items"]["b"]["first_seen"], "t0")
        self.assertEqual(updated["items"]["b"]["changed"], "t1")
        self.assertEqual(updated["gone"]["c"]["gone"], "t1")
        self.assertEqual(updated["last_run"], "t1")

    def test_render_leaves_out_managed_links(self):
        updated, changes = audit.merge({"last_run": "t0", "items": {}},
                                       {"x": entry("link:/opt/rc/bin/x", managed=True), "y": entry("f", detail="eslint")},
                                       "t1")
        report = audit.render(changes, updated, "t0", show_all=False)
        self.assertEqual(report, "package-audit: 1 unmanaged items in the home; changes since t0:\n  new     y  eslint")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / ".local/bin").mkdir(parents=True)
        self.env = {**os.environ, "HOME": str(self.home), "XDG_STATE_HOME": str(self.home / "state")}

    def run_audit(self, *args):
        return subprocess.run([str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=60)

    def test_reports_an_npx_run_and_a_cargo_install_after_the_baseline(self):
        first = self.run_audit()
        self.assertIn("first run: recorded as the baseline", first.stdout)
        (self.home / ".local/bin/studio-deploy").symlink_to("/opt/rc/bin/studio-deploy")
        npx = self.home / ".npm/_npx/0dd5ae94e53e6f06"
        npx.mkdir(parents=True)
        (npx / "package.json").write_text(json.dumps({"dependencies": {"cowsay": "^1"}}))
        (self.home / ".cargo/bin").mkdir(parents=True)
        (self.home / ".cargo/bin/ripgrep-all").write_text("binary")
        second = self.run_audit()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("new     .cargo/bin/ripgrep-all", second.stdout)
        self.assertIn("new     .npm/_npx/0dd5ae94e53e6f06  cowsay", second.stdout)
        self.assertNotIn("studio-deploy", second.stdout)

    def test_all_lists_items_from_earlier_runs(self):
        (self.home / ".local/bin/handmade").write_text("#!/bin/sh\n")
        self.run_audit()
        later = self.run_audit("--all")
        self.assertIn(".local/bin/handmade", later.stdout.split("all unmanaged items (first seen):")[1])


if __name__ == "__main__":
    unittest.main()
