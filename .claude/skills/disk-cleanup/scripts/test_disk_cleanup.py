import datetime as dt
import subprocess
import tempfile
import unittest
from pathlib import Path

import disk_cleanup as dc

NOW = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc)
GB = 1024**3


def days_ago(n):
    return NOW - dt.timedelta(days=n)


class ArtifactReasonTest(unittest.TestCase):
    def reason(self, name, siblings):
        return dc.artifact_reason(Path("/x") / name, set(siblings) | {name})

    def test_android_native_output_beside_gradle_file(self):
        self.assertEqual(self.reason(".cxx", ["build.gradle"]), "Android native build output")

    def test_xcode_build_beside_project(self):
        self.assertEqual(self.reason("build", ["App.xcworkspace"]), "Xcode build output")

    def test_flutter_and_swiftpm(self):
        self.assertEqual(self.reason(".dart_tool", ["pubspec.yaml"]), "Flutter build output")
        self.assertEqual(self.reason(".build", ["Package.swift"]), "SwiftPM build output")

    def test_plain_build_dir_is_left_alone(self):
        self.assertIsNone(self.reason("build", ["Makefile"]))


class GradleVersionTest(unittest.TestCase):
    def test_cache_and_dist_names_map_to_one_version(self):
        self.assertEqual(
            [dc.gradle_version(n) for n in ("8.13", "gradle-8.13-all", "gradle-9.4.1-bin", "gradle-8.0-rc-1-bin")],
            ["8.13", "8.13", "9.4.1", "8.0-rc-1"])

    def test_shared_cache_dirs_are_not_versions(self):
        self.assertEqual([dc.gradle_version(n) for n in ("modules-2", "jars-9", "build-cache-1")], [None] * 3)


class ClassifyIdleCheckoutsTest(unittest.TestCase):
    def entry(self, idle_days, size):
        return {"path": Path("/w/app1"), "size": size, "last_activity": days_ago(idle_days),
                "artifacts": [(Path("/w/app1/node_modules"), "npm"), (Path("/w/app1/a/node_modules"), "npm"),
                              (Path("/w/app1/android/build"), "gradle")]}

    def test_idle_large_checkout_is_review_with_all_paths(self):
        [item] = dc.classify_idle_checkouts([self.entry(45, 2 * GB)], NOW, 30)
        self.assertEqual((item.action, item.kind, item.label), ("REVIEW", "paths", "/w/app1"))
        self.assertEqual(item.target, ("/w/app1/node_modules", "/w/app1/a/node_modules", "/w/app1/android/build"))
        self.assertEqual(item.reason, "idle 45 days: node_modules x2, build")

    def test_recent_or_small_checkouts_are_not_listed(self):
        self.assertEqual(dc.classify_idle_checkouts([self.entry(10, 2 * GB), self.entry(45, GB // 2)], NOW, 30), [])


class ClassifyPackageCachesTest(unittest.TestCase):
    def classify(self, **kw):
        args = {"caches": [], "gradle_dirs": [], "gradle_in_use": {"9.4.1"}, "pnpm_stores": []}
        return dc.classify_package_caches(**{**args, **kw})

    def test_large_tool_cache_runs_its_command(self):
        [item] = self.classify(caches=[("npm cache", 3 * GB, "r", "command", ("npm", "cache", "clean", "--force")),
                                       ("uv cache", GB // 2, "r", "command", ("uv", "cache", "prune"))])
        self.assertEqual((item.label, item.action, item.target), ("npm cache", "DELETE", ("npm", "cache", "clean", "--force")))

    def test_unused_gradle_version_groups_cache_and_dist(self):
        dirs = [(Path("/g/caches/8.13"), GB), (Path("/g/wrapper/dists/gradle-8.13-all"), GB),
                (Path("/g/caches/9.4.1"), GB)]
        [item] = self.classify(gradle_dirs=dirs)
        self.assertEqual((item.label, item.size), ("Gradle 8.13", 2 * GB))
        self.assertEqual(item.target, ("/g/caches/8.13", "/g/wrapper/dists/gradle-8.13-all"))

    def test_gradle_versions_are_kept_when_scan_found_none(self):
        self.assertEqual(self.classify(gradle_dirs=[(Path("/g/caches/8.13"), GB)], gradle_in_use=set()), [])

    def test_pnpm_prunes_current_layout_and_drops_older(self):
        root = Path("/s/.pnpm-store")
        items = self.classify(pnpm_stores=[(root, [(root / "v3", GB // 2), (root / "v11", 7 * GB)])])
        self.assertEqual([(i.kind, i.target) for i in items],
                         [("path", "/s/.pnpm-store/v3"),
                          ("command", ("pnpm", "store", "prune", "--store-dir", "/s/.pnpm-store"))])


class CheckoutScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def git_repo(self, rel):
        repo = self.ws / rel
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def test_finds_checkouts_but_not_archive_or_nested(self):
        a = self.git_repo("proj/app1")
        self.git_repo("proj/app1/vendor/sub")
        self.git_repo("_archive/old")
        self.assertEqual(dc.find_checkouts(self.ws), [a])

    def test_tracked_artifacts_are_excluded(self):
        repo = self.git_repo("proj/app1")
        for d in ("node_modules/x", ".yarn/cache", "ios/Pods/Lib"):
            (repo / d).mkdir(parents=True)
            (repo / d / "f").write_text("x")
        (repo / "ios/Podfile").write_text("")
        (repo / ".yarn/cache/z.zip").write_text("")
        subprocess.run(["git", "-C", str(repo), "add", ".yarn/cache/z.zip"], check=True)
        found = dc.untracked(repo, dc.find_checkout_artifacts(repo)[0])
        self.assertEqual(sorted(str(p.relative_to(repo)) for p, _ in found), ["ios/Pods", "node_modules"])

    def test_symlinked_artifacts_are_not_listed(self):
        repo = self.git_repo("proj/app1")
        (repo / "node_modules/x").mkdir(parents=True)
        (repo / "sub").mkdir()
        (repo / "sub/node_modules").symlink_to(repo / "node_modules")
        self.assertEqual([p for p, _ in dc.find_checkout_artifacts(repo)[0]], [repo / "node_modules"])

    def test_nested_repo_is_its_own_checkout_with_its_own_tracked_check(self):
        outer = self.git_repo("proj/app1")
        nested = self.git_repo("proj/app1/packages/lib")
        for d in (outer / "node_modules", nested / "node_modules", nested / ".yarn/cache"):
            d.mkdir(parents=True)
            (d / "f").write_text("x")
        subprocess.run(["git", "-C", str(nested), "add", ".yarn/cache/f"], check=True)
        later = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=400)
        entries = dc.collect_idle_checkouts(self.ws, later, 30)
        self.assertEqual(sorted((e["path"], [p for p, _ in e["artifacts"]]) for e in entries),
                         [(outer, [outer / "node_modules"]), (nested, [nested / "node_modules"])])


def item(action, label, kind="path", target="/t"):
    return dc.Item("c", action, label, 1, "r", kind, target)


class SelectItemsTest(unittest.TestCase):
    ITEMS = [item("DELETE", "a"), item("REVIEW", "b"), item("REVIEW", "c")]

    def test_apply_takes_deletes_and_named_reviews(self):
        chosen, unmatched = dc.select_items(self.ITEMS, True, {"c"})
        self.assertEqual(([i.label for i in chosen], unmatched), (["a", "c"], set()))

    def test_review_label_alone_takes_only_that_review(self):
        chosen, _ = dc.select_items(self.ITEMS, False, {"b"})
        self.assertEqual([i.label for i in chosen], ["b"])

    def test_unknown_or_delete_label_is_unmatched(self):
        chosen, unmatched = dc.select_items(self.ITEMS, False, {"a", "zzz"})
        self.assertEqual((chosen, unmatched), ([], {"a", "zzz"}))


class ReportAndDeleteTest(unittest.TestCase):
    def test_paths_items_print_every_path(self):
        out = dc.report([dc.Item("idle-checkouts", "REVIEW", "/w/app", 1, "idle", "paths", ("/w/app/a", "/w/app/b"))])
        self.assertIn("/w/app  -- idle\n" + " " * 17 + "/w/app/a\n" + " " * 17 + "/w/app/b", out)

    def test_delete_paths_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = [Path(tmp) / "a", Path(tmp) / "b"]
            for d in dirs:
                (d / "x").mkdir(parents=True)
            marker = Path(tmp) / "ran"
            dc.delete(item("DELETE", "p", "paths", tuple(map(str, dirs))))
            dc.delete(item("DELETE", "c", "command", ("touch", str(marker))))
            self.assertEqual(([d.exists() for d in dirs], marker.exists()), ([False, False], True))


if __name__ == "__main__":
    unittest.main()
