# Machine triage — "this Mac feels slow"

Nothing in this file is configured by this repo. It's the checklist from diagnosing
this machine (10-core, 64 GB), recorded because re-deriving it cost a session.

## Read memory pressure before hunting a runaway process

A load average in the hundreds on a 10-core box is **not** hundreds of runnable
CPU-bound tasks. Threads blocked on page faults count toward load, so a huge number
tracks **memory-compressor thrash** far more often than CPU saturation.

The case that produced this note: load average ~400 (healthy is <10), ~2.2 GB free of
64 GB, ~24 GB parked in the macOS memory compressor, 0% idle with 73% of CPU time in
the kernel — and swap still at 0. Pure compression rather than disk swap, which is
why the machine was usable at all.

So: check free RAM and compressor size first (`top -l 1 -s 0 | head`, or Activity
Monitor's Memory tab), and only then look for a process pegging a core.

## Orphaned iOS Simulators are a prime suspect

A booted simulator survives indefinitely — it is not torn down when the test run that
spawned it ends, and it outlives the terminal it came from. Each booted device hosts
roughly 200 child processes (SpringBoard, Siri, Health, News, poster extensions), so a
single orphan can dominate both the process count and the memory pressure.

The one found here was named after a test (`test_ensure_fresh_recreates_…`) and had
been up for the machine's entire 2.5-day uptime, hosting 204 children.

The giveaway is one PID with an enormous child count. Clear it with:

```sh
xcrun simctl list devices booted     # what's actually running
xcrun simctl shutdown all            # safe; reclaims the memory immediately
```

## Known heavy residents (the floor, not the bug)

`watchman` is a persistent multi-GB resident on this machine (3.4-3.9 GB observed
across sessions), alongside `com.apple.Virtualization.VirtualMachine` and the usual
Electron stack (iTerm2, Telegram, Superhuman helpers, Teams, Chromium, WhatsApp).
Know that baseline before concluding some new process is the culprit.
