#!/usr/bin/env python3
"""Find obsolete developer caches and leftovers, and optionally delete them.

Default is a dry run that prints the plan. --apply deletes every DELETE item;
REVIEW items are only ever reported.
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
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
DERIVED_DATA = HOME / "Library/Developer/Xcode/DerivedData"
SIM_DEVICES = HOME / "Library/Developer/CoreSimulator/Devices"
DEVICE_SUPPORT_ROOT = HOME / "Library/Developer/Xcode"
CATEGORIES = ("simulators", "runtimes", "derived-data", "device-support", "rust-targets", "archive-artifacts")
REVIEW_MIN_BYTES = 5 * 1024**3


@dataclass(frozen=True)
class Item:
    category: str
    action: str
    label: str
    size: int
    reason: str
    kind: str
    target: str


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def sizes_of(paths):
    existing = [str(p) for p in paths if Path(p).exists()]
    if not existing:
        return {}
    out = subprocess.run(["du", "-sk", *existing], capture_output=True, text=True).stdout
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


def archive_artifact_reason(path, siblings):
    name = path.name
    if name == "node_modules":
        return "npm dependencies"
    if name == "Pods" and "Podfile" in siblings:
        return "CocoaPods dependencies; pod install restores them"
    if name == "build" and {"build.gradle", "build.gradle.kts"} & siblings:
        return "Gradle build output"
    if name == ".gradle":
        return "Gradle cache"
    if name == "cache" and path.parent.name == ".yarn":
        return "Yarn cache; yarn install restores it"
    if name == ".next" and "package.json" in siblings:
        return "Next.js build output"
    if name == ".venv":
        return "Python virtualenv"
    return None


def classify_archive_artifacts(entries):
    return [
        Item("archive-artifacts", "DELETE", str(e["path"]), e["size"], e["reason"], "path", str(e["path"]))
        for e in entries
    ]


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


def find_archive_artifacts(root):
    found = []
    for parent, dirs, files in os.walk(root):
        siblings = set(dirs) | set(files)
        matched = {d: reason for d in dirs if (reason := archive_artifact_reason(Path(parent) / d, siblings))}
        found += [(Path(parent) / d, reason) for d, reason in matched.items()]
        dirs[:] = [d for d in dirs if d not in matched and d != ".git"]
    return found


def collect_archive_artifacts(archive):
    found = find_archive_artifacts(archive)
    sizes = sizes_of(path for path, _ in found)
    return [{"path": path, "reason": reason, "size": sizes.get(str(path), 0)} for path, reason in found]


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
    return items


def report(items):
    lines = []
    for category in CATEGORIES:
        group = sorted((i for i in items if i.category == category), key=lambda i: (i.action, -i.size))
        if not group:
            continue
        lines.append(f"== {category} ==")
        lines += [f"{i.action:<7}{human(i.size):>8}  {i.label}  -- {i.reason}" for i in group]
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
    else:
        shutil.rmtree(item.target)


def free_space():
    return shutil.disk_usage(HOME).free


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="delete every DELETE item")
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
    if not args.apply:
        return 0

    before = free_space()
    failures = []
    for item in (i for i in items if i.action == "DELETE"):
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
