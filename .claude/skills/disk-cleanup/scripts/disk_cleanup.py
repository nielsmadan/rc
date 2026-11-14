#!/usr/bin/env python3
"""Find obsolete developer caches and leftovers, and optionally delete them.

Default is a dry run that prints the plan. --apply deletes every DELETE item;
a REVIEW item is deleted only when its label is passed to --apply-review.
"""

import argparse
import datetime as dt
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
DERIVED_DATA = HOME / "Library/Developer/Xcode/DerivedData"
SIM_DEVICES = HOME / "Library/Developer/CoreSimulator/Devices"
DEVICE_SUPPORT_ROOT = HOME / "Library/Developer/Xcode"
GRADLE_HOME = HOME / ".gradle"
YARN_V1_CACHE = HOME / "Library/Caches/Yarn"
NPM_CACHE = HOME / ".npm/_cacache"
CATEGORIES = ("simulators", "runtimes", "derived-data", "device-support", "rust-targets", "archive-artifacts",
              "idle-checkouts", "package-caches")
REVIEW_MIN_BYTES = 5 * 1024**3
IDLE_CHECKOUT_MIN_BYTES = 1024**3
CACHE_MIN_BYTES = 1024**3


@dataclass(frozen=True)
class Item:
    category: str
    action: str
    label: str
    size: int
    reason: str
    kind: str
    target: object


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def sizes_of(paths):
    existing = [str(p) for p in paths if Path(p).exists()]
    chunks = [existing[i:i + 500] for i in range(0, len(existing), 500)]
    out = "".join(subprocess.run(["du", "-sk", *c], capture_output=True, text=True).stdout for c in chunks)
    return {
        line.split("\t", 1)[1]: int(line.split("\t", 1)[0]) * 1024
        for line in out.splitlines()
        if "\t" in line
    }


def version_tuple(text):
    return tuple(int(p) for p in re.findall(r"\d+", text))


def parse_time(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def human(n):
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.1f}{unit}" if unit in ("G", "T") else f"{n:.0f}{unit}"
        n /= 1024


def checkout_exists(workspace, parent, name):
    patterns = [f"{parent}/{name}", f"*/{parent}/{name}", f"*/*/{parent}/{name}"]
    return any(any(workspace.glob(p)) for p in patterns)


def classify_devices(devices, workspace, sizes):
    def decide(d):
        name = d["name"]
        parts = name.split("/")
        if d["state"] != "Shutdown":
            return None
        if not d.get("isAvailable", True):
            return f"runtime {d['runtime'].split('.')[-1]} not installed; cannot boot"
        if re.match(r"^(pytest-\d+/|test_)", name):
            return "leaked by a test run"
        if len(parts) == 3 and not checkout_exists(workspace, parts[0], parts[1]):
            return f"splashdown checkout {parts[0]}/{parts[1]} no longer exists"
        return None

    return [
        Item("simulators", "DELETE", f"{d['name']} [{d['udid'][:8]}]",
             sizes.get(str(SIM_DEVICES / d["udid"]), 0), reason, "simctl-device", d["udid"])
        for d in devices
        if (reason := decide(d))
    ]


def classify_runtimes(images, surviving_devices, now, stale_days):
    used_idents = {d["runtime"] for d in surviving_devices}
    ready = [i for i in images if i.get("state") == "Ready" and i.get("deletable")]

    def platform(img):
        return img["runtimeIdentifier"].rsplit(".", 1)[-1].split("-")[0]

    def newest_for_ident(img):
        same = [i for i in ready if i["runtimeIdentifier"] == img["runtimeIdentifier"]]
        return max(same, key=lambda i: version_tuple(i["version"])) is img

    def superseded(img):
        v = version_tuple(img["version"])
        return any(platform(o) == platform(img) and version_tuple(o["version"])[0] == v[0]
                   and version_tuple(o["version"]) > v for o in ready)

    def stale(img):
        last = parse_time(img.get("lastUsedAt"))
        return last is None or (now - last).days >= stale_days

    def in_use(img):
        return img["runtimeIdentifier"] in used_idents and newest_for_ident(img)

    return [
        Item("runtimes", "DELETE", f"{platform(i)} {i['version']} ({i['build']})", i["sizeBytes"],
             f"no simulators use it, newer {platform(i)} {version_tuple(i['version'])[0]}.x installed, "
             f"last used {(i.get('lastUsedAt') or 'never')[:10]}",
             "simctl-runtime", i["identifier"])
        for i in ready
        if not in_use(i) and superseded(i) and stale(i)
    ]


def classify_derived_data(entries, now, stale_days):
    def decide(e):
        if e["workspace"] is None:
            return "DELETE", "no info.plist; orphaned build folder"
        if not e["workspace_exists"]:
            return "DELETE", f"project gone: {e['workspace']}"
        idle = (now - e["mtime"]).days
        if idle >= stale_days and e["size"] >= REVIEW_MIN_BYTES:
            return "REVIEW", f"live project, not built for {idle} days: {e['workspace']}"
        return None

    return [
        Item("derived-data", action, e["path"].name, e["size"], reason, "path", str(e["path"]))
        for e in entries
        if (verdict := decide(e)) and (action := verdict[0]) and (reason := verdict[1])
    ]


def classify_device_support(entries):
    def key(e):
        m = re.match(r"^(?:(\S+,\d+) )?(\d+(?:\.\d+)*)", e["path"].name)
        return (e["path"].parent.name, m.group(1) or "") if m else None, version_tuple(m.group(2)) if m else ()

    keyed = [(key(e), e) for e in entries]
    newest = {}
    for (group, ver), _ in keyed:
        if group is not None and ver > newest.get(group, ()):
            newest[group] = ver
    return [
        Item("device-support", "DELETE", f"{e['path'].parent.name}/{e['path'].name}", e["size"],
             "a newer OS version exists for this device", "path", str(e["path"]))
        for (group, ver), e in keyed
        if group is not None and ver < newest[group]
    ]


def classify_rust_targets(entries, now, stale_days):
    def decide(e):
        idle = (now - e["mtime"]).days
        if not e["has_manifest"]:
            return "DELETE", "no Cargo.toml beside it any more"
        if idle >= stale_days and e["size"] >= 1024**3:
            return "REVIEW", f"not built for {idle} days"
        return None

    return [
        Item("rust-targets", verdict[0], str(e["path"]), e["size"], verdict[1], "path", str(e["path"]))
        for e in entries
        if (verdict := decide(e))
    ]


def artifact_reason(path, siblings):
    name = path.name
    gradle_project = bool({"build.gradle", "build.gradle.kts"} & siblings)
    if name == "node_modules":
        return "npm dependencies"
    if name == "Pods" and "Podfile" in siblings:
        return "CocoaPods dependencies; pod install restores them"
    if name == "build" and gradle_project:
        return "Gradle build output"
    if name == ".cxx" and gradle_project:
        return "Android native build output"
    if name == "build" and any(s.endswith((".xcodeproj", ".xcworkspace")) for s in siblings):
        return "Xcode build output"
    if name in ("build", ".dart_tool") and "pubspec.yaml" in siblings:
        return "Flutter build output"
    if name == ".build" and "Package.swift" in siblings:
        return "SwiftPM build output"
    if name == ".gradle":
        return "Gradle cache"
    if name == "cache" and path.parent.name == ".yarn":
        return "Yarn cache; yarn install restores it"
    if name == ".next" and "package.json" in siblings:
        return "Next.js build output"
    if name == ".venv":
        return "Python virtualenv"
    return None


def matched_artifacts(parent, dirs, siblings):
    return {d: reason for d in dirs
            if not (parent / d).is_symlink() and (reason := artifact_reason(parent / d, siblings))}


def classify_archive_artifacts(entries):
    return [
        Item("archive-artifacts", "DELETE", str(e["path"]), e["size"], e["reason"], "path", str(e["path"]))
        for e in entries
    ]


def classify_idle_checkouts(entries, now, stale_days):
    def describe(e):
        counts = Counter(path.name for path, _ in e["artifacts"])
        return ", ".join(f"{name} x{n}" if n > 1 else name for name, n in counts.most_common())

    def idle(e):
        return (now - e["last_activity"]).days

    return [
        Item("idle-checkouts", "REVIEW", str(e["path"]), e["size"], f"idle {idle(e)} days: {describe(e)}", "paths",
             tuple(str(path) for path, _ in e["artifacts"]))
        for e in entries
        if idle(e) >= stale_days and e["size"] >= IDLE_CHECKOUT_MIN_BYTES
    ]


def gradle_version(name):
    version = re.sub(r"-(?:bin|all)$", "", name.removeprefix("gradle-"))
    return version if re.fullmatch(r"\d+\.\d+(?:\.\d+)?(?:-[\w.-]+)?", version) else None


def classify_package_caches(caches, gradle_dirs, gradle_in_use, pnpm_stores):
    tools = [
        Item("package-caches", "DELETE", name, size, reason, kind, target)
        for name, size, reason, kind, target in caches
        if size >= CACHE_MIN_BYTES
    ]
    by_version = {}
    for path, size in gradle_dirs:
        version = gradle_version(path.name)
        if version:
            paths, total = by_version.get(version, ((), 0))
            by_version[version] = (paths + (str(path),), total + size)
    gradle = [
        Item("package-caches", "DELETE", f"Gradle {version}", total,
             "no gradle-wrapper.properties under the workspace uses it", "paths", paths)
        for version, (paths, total) in sorted(by_version.items())
        if gradle_in_use and version not in gradle_in_use
    ]
    pnpm = []
    for root, layouts in pnpm_stores:
        current = max(layouts, key=lambda l: version_tuple(l[0].name))[0].name if layouts else None
        pnpm += [
            Item("package-caches", "DELETE", f"pnpm store {path}", size,
                 f"store layout {path.name}; the installed pnpm uses {current}, an older pinned pnpm re-downloads",
                 "path", str(path))
            for path, size in layouts if path.name != current
        ]
        pnpm += [
            Item("package-caches", "DELETE", f"pnpm store prune {root}", size,
                 "pnpm store prune; frees only packages no project links to", "command",
                 ("pnpm", "store", "prune", "--store-dir", str(root)))
            for path, size in layouts if path.name == current and size >= CACHE_MIN_BYTES
        ]
    return tools + gradle + pnpm


def collect_simulators(workspace, now, stale_days):
    raw = json.loads(run(["xcrun", "simctl", "list", "devices", "-j"]))["devices"]
    devices = [{**d, "runtime": rt} for rt, devs in raw.items() for d in devs]
    sizes = sizes_of(SIM_DEVICES / d["udid"] for d in devices)
    device_items = classify_devices(devices, workspace, sizes)
    doomed = {i.target for i in device_items}
    surviving = [d for d in devices if d["udid"] not in doomed]
    images = list(json.loads(run(["xcrun", "simctl", "runtime", "list", "-j"])).values())
    return device_items, classify_runtimes(images, surviving, now, stale_days)


def collect_derived_data():
    if not DERIVED_DATA.is_dir():
        return []
    dirs = [p for p in DERIVED_DATA.iterdir()
            if p.is_dir() and not p.name.endswith(".noindex") and p.name != "SDKExplicitPrecompiledModules"]
    sizes = sizes_of(dirs)

    def workspace_of(p):
        try:
            return plistlib.loads((p / "info.plist").read_bytes()).get("WorkspacePath")
        except (OSError, plistlib.InvalidFileException):
            return None

    return [
        {"path": p, "workspace": (ws := workspace_of(p)), "workspace_exists": bool(ws) and Path(ws).exists(),
         "size": sizes.get(str(p), 0),
         "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc)}
        for p in dirs
    ]


def collect_device_support():
    dirs = [p for root in DEVICE_SUPPORT_ROOT.glob("* DeviceSupport") for p in root.iterdir() if p.is_dir()]
    sizes = sizes_of(dirs)
    return [{"path": p, "size": sizes.get(str(p), 0)} for p in dirs]


def find_rust_targets(workspace, max_depth=4):
    skip = {".git", "node_modules", "Pods", ".venv", "venv", "build", "dist"}
    found = []
    for root, dirs, _ in os.walk(workspace):
        depth = len(Path(root).relative_to(workspace).parts)
        if "target" in dirs and (Path(root) / "target" / "CACHEDIR.TAG").exists():
            found.append(Path(root) / "target")
        dirs[:] = [] if depth >= max_depth else [d for d in dirs if d not in skip and d != "target"]
    return found


def collect_rust_targets(workspace):
    targets = find_rust_targets(workspace)
    sizes = sizes_of(targets)

    def last_build(t):
        stamps = [p.stat().st_mtime for p in (t / "debug", t / "release", t) if p.exists()]
        return dt.datetime.fromtimestamp(max(stamps), dt.timezone.utc)

    return [
        {"path": t, "size": sizes.get(str(t), 0), "has_manifest": (t.parent / "Cargo.toml").exists(),
         "mtime": last_build(t)}
        for t in targets
    ]


def walk_artifacts(root, skip=frozenset({".git"}), max_depth=None, stop_at_repos=False):
    found, repos = [], []
    for parent, dirs, files in os.walk(root):
        here = Path(parent)
        siblings = set(dirs) | set(files)
        nested = [d for d in dirs if stop_at_repos and not (here / d).is_symlink() and (here / d / ".git").exists()]
        repos += [here / d for d in nested]
        candidates = [d for d in dirs if d not in nested]
        matched = matched_artifacts(here, candidates, siblings)
        found += [(here / d, reason) for d, reason in matched.items()]
        depth = len(here.relative_to(root).parts)
        dirs[:] = [] if max_depth is not None and depth >= max_depth else [
            d for d in candidates if d not in matched and d not in skip]
    return found, repos


def find_archive_artifacts(root):
    return walk_artifacts(root)[0]


def collect_archive_artifacts(archive):
    found = find_archive_artifacts(archive)
    sizes = sizes_of(path for path, _ in found)
    return [{"path": path, "reason": reason, "size": sizes.get(str(path), 0)} for path, reason in found]


def find_checkouts(workspace, max_depth=3):
    found = []
    for root, dirs, files in os.walk(workspace):
        rel = Path(root).relative_to(workspace)
        if rel.parts and (".git" in dirs or ".git" in files):
            found.append(Path(root))
            dirs[:] = []
            continue
        top = not rel.parts
        dirs[:] = [] if len(rel.parts) >= max_depth else [
            d for d in dirs if not d.startswith(".") and d != "node_modules" and not (top and d == "_archive")]
    return found


def git_dir(checkout):
    dot_git = checkout / ".git"
    if dot_git.is_file():
        line = dot_git.read_text().strip()
        return (checkout / line.split(":", 1)[1].strip()).resolve() if line.startswith("gitdir:") else dot_git
    return dot_git


def mtime(path):
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)


def last_git_activity(checkout):
    gd = git_dir(checkout)
    stamps = [mtime(p) for p in (gd / "index", gd / "logs" / "HEAD", gd / "HEAD") if p.exists()]
    return max(stamps) if stamps else mtime(checkout)


def find_checkout_artifacts(checkout, max_depth=6):
    return walk_artifacts(checkout, skip=frozenset({".git", "target"}), max_depth=max_depth, stop_at_repos=True)


def untracked(checkout, artifacts):
    rels = [str(path.relative_to(checkout)) for path, _ in artifacts]
    if not rels:
        return []
    out = subprocess.run(["git", "-C", str(checkout), "ls-files", "-z", "--", *rels], capture_output=True, text=True)
    if out.returncode != 0:
        return []
    tracked = [t for t in out.stdout.split("\0") if t]
    return [a for a, rel in zip(artifacts, rels) if not any(t == rel or t.startswith(rel + "/") for t in tracked)]


def collect_idle_checkouts(workspace, now, stale_days):
    queue = find_checkouts(workspace)
    found = []
    while queue:
        checkout = queue.pop()
        activity = last_git_activity(checkout)
        if (now - activity).days < stale_days:
            continue
        artifacts, nested = find_checkout_artifacts(checkout)
        queue += nested
        found.append((checkout, activity, untracked(checkout, artifacts)))
    sizes = sizes_of(path for _, _, artifacts in found for path, _ in artifacts)
    return [
        {"path": c, "artifacts": artifacts,
         "size": sum(sizes.get(str(path), 0) for path, _ in artifacts),
         "last_activity": max([git_activity] + [mtime(path) for path, _ in artifacts if path.exists()])}
        for c, git_activity, artifacts in found
        if artifacts
    ]


def gradle_versions_in_use(workspace, max_depth=7):
    skip = {".git", "node_modules", "Pods", "build", "target", ".build", ".venv", "venv", "dist", ".gradle", ".cxx"}
    found = set()
    for root, dirs, files in os.walk(workspace):
        if "gradle-wrapper.properties" in files:
            text = (Path(root) / "gradle-wrapper.properties").read_text(errors="replace")
            found |= set(re.findall(r"gradle-(\d+\.\d+(?:\.\d+)?(?:-[\w.-]+?)?)-(?:bin|all)\.zip", text))
        depth = len(Path(root).relative_to(workspace).parts)
        dirs[:] = [] if depth >= max_depth else [d for d in dirs if d not in skip]
    return found


def command_output(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=HOME).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect_package_caches(workspace):
    uv_dir = command_output(["uv", "cache", "dir"])
    pnpm_path = command_output(["pnpm", "store", "path"])
    store_roots = {Path(pnpm_path).parent} if pnpm_path else set()
    store_roots |= {workspace / ".pnpm-store"}
    layouts = {root: [p for p in root.glob("v*") if p.is_dir() and re.fullmatch(r"v\d+", p.name)]
               for root in store_roots if root.is_dir()}
    gradle_dirs = [p for p in (GRADLE_HOME / "caches").glob("*") if p.is_dir() and gradle_version(p.name)]
    gradle_dirs += [p for p in (GRADLE_HOME / "wrapper/dists").glob("gradle-*") if p.is_dir()]
    tool_paths = [NPM_CACHE, YARN_V1_CACHE] + ([Path(uv_dir)] if uv_dir else [])
    sizes = sizes_of(tool_paths + gradle_dirs + [p for ps in layouts.values() for p in ps])

    def size(p):
        return sizes.get(str(p), 0)

    caches = [("npm cache", size(NPM_CACHE), "npm cache clean --force; installs re-download", "command",
               ("npm", "cache", "clean", "--force"))]
    caches += [("Yarn v1 cache", size(YARN_V1_CACHE), "Yarn 1 download cache; installs re-download", "path",
                str(YARN_V1_CACHE))] if YARN_V1_CACHE.is_dir() else []
    caches += [("uv cache", size(uv_dir), "uv cache prune; frees only unused entries", "command",
                ("uv", "cache", "prune"))] if uv_dir else []
    return {
        "caches": caches,
        "gradle_dirs": [(p, size(p)) for p in gradle_dirs],
        "gradle_in_use": gradle_versions_in_use(workspace),
        "pnpm_stores": [(root, [(p, size(p)) for p in ps]) for root, ps in sorted(layouts.items())],
    }


def scan(categories, workspace, now, stale_days):
    items = []
    if {"simulators", "runtimes"} & categories:
        devices, runtimes = collect_simulators(workspace, now, stale_days)
        items += devices if "simulators" in categories else []
        items += runtimes if "runtimes" in categories else []
    if "derived-data" in categories:
        items += classify_derived_data(collect_derived_data(), now, stale_days)
    if "device-support" in categories:
        items += classify_device_support(collect_device_support())
    if "rust-targets" in categories and workspace.is_dir():
        items += classify_rust_targets(collect_rust_targets(workspace), now, stale_days)
    if "archive-artifacts" in categories and (workspace / "_archive").is_dir():
        items += classify_archive_artifacts(collect_archive_artifacts(workspace / "_archive"))
    if "idle-checkouts" in categories and workspace.is_dir():
        items += classify_idle_checkouts(collect_idle_checkouts(workspace, now, stale_days), now, stale_days)
    if "package-caches" in categories:
        items += classify_package_caches(**collect_package_caches(workspace))
    return items


def report(items):
    lines = []
    for category in CATEGORIES:
        group = sorted((i for i in items if i.category == category), key=lambda i: (i.action, -i.size))
        if not group:
            continue
        lines.append(f"== {category} ==")
        lines += [line for i in group for line in [f"{i.action:<7}{human(i.size):>8}  {i.label}  -- {i.reason}"]
                  + ([f"{'':17}{path}" for path in i.target] if i.kind == "paths" else [])]
        lines.append("")
    delete = [i for i in items if i.action == "DELETE"]
    review = [i for i in items if i.action == "REVIEW"]
    lines.append(f"DELETE: {len(delete)} items, {human(sum(i.size for i in delete))}")
    lines.append(f"REVIEW: {len(review)} items, {human(sum(i.size for i in review))} (never deleted by --apply)")
    return "\n".join(lines)


def delete(item):
    if item.kind == "simctl-device":
        run(["xcrun", "simctl", "delete", item.target])
    elif item.kind == "simctl-runtime":
        run(["xcrun", "simctl", "runtime", "delete", item.target])
    elif item.kind == "command":
        subprocess.run(list(item.target), capture_output=True, text=True, check=True, cwd=HOME)
    elif item.kind == "paths":
        for path in item.target:
            shutil.rmtree(path)
    else:
        shutil.rmtree(item.target)


def select_items(items, apply, review_labels):
    unmatched = set(review_labels) - {i.label for i in items if i.action == "REVIEW"}
    chosen = [i for i in items
              if (apply and i.action == "DELETE") or (i.action == "REVIEW" and i.label in review_labels)]
    return chosen, unmatched


def free_space():
    return shutil.disk_usage(HOME).free


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="delete every DELETE item")
    ap.add_argument("--apply-review", action="append", default=[], metavar="LABEL",
                    help="also delete the REVIEW item with this label, as printed (repeatable)")
    ap.add_argument("--only", default=",".join(CATEGORIES), help=f"comma list from: {', '.join(CATEGORIES)}")
    ap.add_argument("--days", type=int, default=30, help="idle days before a runtime or build is stale (default 30)")
    ap.add_argument("--workspace", type=Path, default=HOME / "wrksp", help="root holding project checkouts")
    args = ap.parse_args()

    categories = set(args.only.split(","))
    unknown = categories - set(CATEGORIES)
    if unknown:
        ap.error(f"unknown category: {', '.join(sorted(unknown))}")

    items = scan(categories, args.workspace.expanduser(), dt.datetime.now(dt.timezone.utc), args.days)
    print(report(items))
    chosen, unmatched = select_items(items, args.apply, set(args.apply_review))
    if unmatched:
        print(f"no REVIEW item labelled: {', '.join(sorted(unmatched))}", file=sys.stderr)
        return 2
    if not chosen:
        return 0

    before = free_space()
    failures = []
    for item in chosen:
        try:
            delete(item)
        except (subprocess.CalledProcessError, OSError) as e:
            failures.append(f"{item.label}: {getattr(e, 'stderr', '') or e}")
    print(f"\nfree space: {human(before)} -> {human(free_space())}")
    print("runtime deletes finish in the background; their space appears later.")
    for f in failures:
        print(f"FAILED {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
