---
name: disk-cleanup
description: Scan this Mac for obsolete developer leftovers and reclaim disk space — iOS simulators that cannot boot or whose checkout is gone, superseded simulator runtimes, Xcode DerivedData for deleted projects, outdated iOS DeviceSupport, stale Rust target dirs, and regenerable dependencies and build output in archived projects. Use when the user says "disk is full", "free up disk space", "reclaim space", "clean up caches", "clean up leftovers", "obsolete simulators", "DerivedData is huge", or a tool fails for lack of free space. Do NOT use for memory or CPU pressure (see docs/machine-triage.md).
---

# Disk Cleanup

One script scans every category earlier cleanups covered and sorts each finding into
**DELETE** (provably obsolete or regenerable) or **REVIEW** (live but idle; the user decides).

## Instructions

### Step 1: Dry run

```bash
python3 .claude/skills/disk-cleanup/scripts/disk_cleanup.py
```

It takes about 40s, mostly `du` and the `~/wrksp` walk. Narrow it with
`--only simulators,runtimes,derived-data,device-support,rust-targets,archive-artifacts`; `--days N` sets the
staleness threshold (default 30). Also run `df -h ~ | tail -1` to record free space beforehand.

The rules behind each verdict:

| Category | DELETE when | Never touched |
|---|---|---|
| simulators | runtime not installed (cannot boot); name starts `pytest-N/` or `test_` (splashdown test leak); splashdown name `parent/dir/variant` whose checkout is not found under `~/wrksp` up to two levels deep | booted devices; hand-named devices on installed runtimes |
| runtimes | no surviving simulator uses it, a newer runtime of the same major version is installed, and it is unused for `--days` | the newest runtime of each major, e.g. iOS 18.5 kept as the old-OS test target |
| derived-data | `info.plist` missing, or its `WorkspacePath` no longer exists | Xcode's shared `*.noindex` and `SDKExplicitPrecompiledModules`; live projects only reach REVIEW (idle and over 5 GB) |
| device-support | an older OS folder for a device model that has a newer one | the newest folder per model |
| rust-targets | `target/` with no `Cargo.toml` beside it | live checkouts only reach REVIEW (idle and over 1 GB) |
| archive-artifacts | under `~/wrksp/_archive`: `node_modules`, `Pods` beside a `Podfile`, `build` beside a `build.gradle(.kts)`, `.gradle`, `.yarn/cache`, `.next`, `.venv` | anything outside `_archive`; other `build` dirs (PHP `vendor/**/build` holds code, PlatformIO `.pio/build`); `.git` |

### Step 2: Sanity-check the DELETE list

Read every DELETE line before applying. If a reason looks wrong for this machine, such as a
checkout that lives outside `~/wrksp`, rerun with `--workspace PATH` or `--only` to exclude that
category. Never delete an item by hand that the script did not list.

### Step 3: Apply

When the user asked for a cleanup, applying the DELETE list is authorized:

```bash
python3 .claude/skills/disk-cleanup/scripts/disk_cleanup.py --apply
```

It prints free space before and after, and lists any failure on stderr with a non-zero exit.
`--apply` never deletes REVIEW items. List those with sizes and ask; delete only the ones the
user names, with `rm -rf` on the printed path.

### Step 4: Report

Give free space before and after, and a per-category count and size of what was deleted.
Then give the REVIEW list as a question. Runtime deletes finish in the background (`simctl
runtime list` shows `Deleting`), sometimes not until a reboot, so report their size as still
pending.

## Examples

### Example: "the disk is almost full, clean up the leftovers"

1. Dry run: 12 simulators on missing runtimes (31 GB), iOS 26.3.1/26.4/26.4.1 runtimes (25 GB),
   2 DeviceSupport folders (11 GB), 1 REVIEW DerivedData of 6 GB.
2. All DELETE reasons check out, so run `--apply`. Free space goes 155 → 197 GiB, with runtimes still pending.
3. Report, and ask whether the idle FlowLab DerivedData (6.3 GB, 33 days) can go.

### Example: "just look, don't delete anything"

Run the dry run only and present its output grouped by category with the totals.

## Troubleshooting

### `xcrun: error` or `simctl` hangs

Xcode's command-line tools are missing or `xcode-select` points at an uninstalled Xcode. Run
with `--only derived-data,device-support,rust-targets` and tell the user.

### A runtime stays in `Deleting`

CoreSimulator finishes the delete lazily. It is not a failure; it completes after
`killall -9 com.apple.CoreSimulator.CoreSimulatorService` or a reboot.

### A splashdown simulator was flagged but the checkout exists

The checkout sits more than two levels under `~/wrksp`, or outside it. Do not apply that
item. Pass the right `--workspace`, or apply with `--only` excluding `simulators` and delete the
correct ones by UDID.
