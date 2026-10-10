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

## Orphaned vitest workers are the other prime suspect

When a vitest run's main process dies before its workers — the runner is killed, or a
`pnpm -r test` fails fast in one package and tears down another package's run mid-flight —
the `node (vitest N)` workers re-parent to launchd (PPID 1) and keep running. Each holds
0.3-2.5 GB; a 9-worker batch is ~12 GB. An agent that re-runs a full suite after every fix
leaves a new batch each time, and the resulting thrash makes tests time out, which triggers
the next re-run.

Case from 2026-09-29: a Claude `longshot` session in `dreamhack/core3` running
`pnpm check-all && pnpm test && … test:postgres` in a loop. Free RAM was 166 MB; killing
11 orphans freed 21 GB, and a new batch of 9 appeared within two minutes.

The giveaway is `node (vitest N)` processes with PPID 1. Clear them, then find and slow the
session that is spawning them (their cwd names the checkout), or they come straight back:

```sh
ps -Ao pid=,ppid=,command= | awk '$2==1 && /^ *[0-9]+ +1 +node \(vitest/ {print $1}' | xargs kill
```

Avoid a per-process `lsof` loop over every process while the machine is in this state; it
does not finish inside two minutes. `lsof -a -p <pid> -d cwd` on a single orphan is fine.

Case from 2026-10-06: two orphan batches at once, from `dreamhack/core1` and `core2`
`apps/api`. 15-day uptime, load ~340, 116 MB free, 31 GB in the compressor, 37 of 38 GB swap
used. Seven workers sat at ~4 GB RSS each and died one by one at V8's default heap ceiling
(`FatalProcessOutOfMemory`). Workers that keep growing until they hit that ceiling point to
the suite leaking memory within a worker. Orphaning alone would not explain it.

## History: what the machine already recorded

macOS keeps no load or memory history, but it does leave crash and jetsam reports:

- `/Library/Logs/DiagnosticReports/JetsamEvent-*.ips` — written when the kernel kills
  processes for memory. The JSON lists every process with `rpages`, so it records memory by
  family at the moment of the kill.
- `~/Library/Logs/DiagnosticReports/node-*.ips` — a burst of these whose triggering thread
  shows `node::OOMErrorHandler` and whose parent is `launchd` is orphaned vitest workers
  hitting the heap ceiling. The timestamps date the episode.

For everything else there is `resource-log` (this repo's `bin/`). The
`com.nielsmadan.resource-log` LaunchAgent samples load, free/compressor/swap, process
families and orphaned node once a minute into `~/Library/Logs/resource-log/`, keeping 30 days.
`resource-log report --since 24h` (or `90m`, `7d`) prints a timeline and the heaviest families.
Per-process memory is RSS from `ps`, because `top` costs ~2.7 s per sample on this machine.
RSS double-counts pages shared between processes, which inflates multi-process browsers
(Brave read 13 GB by RSS against 7 GB by `top`). CPU is the change in each process's cumulative
CPU time since the previous sample (state in `cpu-state.json`). Samples before 2026-10-07 used
`ps`'s `%cpu`, which missed the exec loop below. A process that starts and exits between two
samples is still invisible.

## A process can pin a core while `ps` shows 0%

`ps`'s `%cpu` restarts at zero on every `exec`, so a process stuck re-execing itself reads
`0.0` in `ps` and in Activity Monitor's sorted list while burning a full core. The kernel time
of all those process starts shows up as a high `sys` share in `top`. The tell is cumulative
`TIME` climbing on a PID whose `%cpu` stays near zero. `resource-log sample --print` measures
this machine-wide; for a single suspect, read it twice:

```sh
ps -o pid=,pcpu=,time= -p <pid>; sleep 5; ps -o pid=,pcpu=,time= -p <pid>
```

Case from 2026-10-07: `~/ac/bin/gh` execed the mise shim, which had no active `gh` inside nono
sandboxes and fell back to the next `gh` on PATH, the wrapper again. Every sandboxed `gh` call
looped until the agent's tool timeout. Eight at once took load from ~20 to ~260 and timed out
dreamhack core's pre-push tests; one had run for 30 hours.

## Work the bottleneck, then remeasure

Sluggishness moves. Separate compressor and swap thrash from real CPU demand first, then
aggregate related processes into families rather than ranking individual PIDs, remove the
largest confirmed consumer, and measure again. The next bottleneck is usually somewhere else
entirely.

A high load average is not by itself evidence of a CPU-heavy process: threads blocked on page
faults or kernel work count toward it too.

**A readiness loop that shells out to `lsof -iTCP` is its own cause of slowness.** Each call
walks every process's open descriptors, so on a process-heavy machine the polling costs more
than whatever it is waiting for. Use bounded direct TCP connection attempts with backoff
instead.

## Known heavy residents (the floor, not the bug)

`watchman` is a persistent multi-GB resident on this machine (3.4-3.9 GB observed
across sessions), alongside `com.apple.Virtualization.VirtualMachine` and the usual
Electron stack (iTerm2, Telegram, Superhuman helpers, Teams, Chromium, WhatsApp).
Know that baseline before concluding some new process is the culprit.

The Cato VPN helper (`com.catonetworks.mac.CatoClient.helper`, a root LaunchDaemon) leaks: 4.5 GB
of physical footprint after 16 days of uptime. `launchd/com.nielsmadan.cato-restart.plist`
restarts it daily at 04:30, dropping the VPN for a few seconds. It runs as root, so `install.sh`
does not install it. Copy it rather than symlinking it, because launchd requires a root-owned
plist:

```sh
sudo install -m 644 -o root -g wheel ~/rc/launchd/com.nielsmadan.cato-restart.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/com.nielsmadan.cato-restart.plist
```

Edits to the repo copy need the same two commands again, preceded by
`sudo launchctl bootout system/com.nielsmadan.cato-restart`.

Every nono-sandboxed agent session also runs its own `/usr/bin/log stream --style ndjson`
watching for sandbox denials, at ~0.6% CPU each. Thirty-odd of them showing up as a "log"
family near half a core is just the session count, not a leak.
