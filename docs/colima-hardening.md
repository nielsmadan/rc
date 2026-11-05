# Colima hardening

This repo installs Colima and keeps it running. Using Docker is not its business — the agent-facing guidance for an unreachable daemon is a global instruction (the `containers` fragment in `~/ac/loadout/instructions/`), so it reaches every harness in every repo rather than only sessions that can read this file.

Docker Desktop was removed in favour of [Colima](https://github.com/abiosoft/colima), which runs upstream `dockerd` (moby) inside a Lima VM and points the stock `docker` CLI at it via a Docker context it registers itself (`autoActivate: true`) — same engine, same API, same BuildKit. Docker Engine needs a Linux kernel, so every option on this platform is a VM; this is the thinnest wrapper that still gives real dockerd.

The CLI side comes from Homebrew, **not** from Colima — `colima` bundles no client. `brew install colima docker docker-compose docker-buildx docker-credential-helper`. Docker Desktop used to own `/usr/local/bin/docker*` as symlinks into the app bundle; those are gone, which is what lets the brew CLI win — don't count on PATH order for that, it differs per machine (`/opt/homebrew/bin` precedes `/usr/local/bin` here, but on the mini `/usr/local/bin` is first and Docker Desktop's symlinks shadowed everything until they were removed). `kubectl` also used to come from the app bundle — it now comes from mise.

Uninstalling Docker Desktop is `sudo /Applications/Docker.app/Contents/MacOS/uninstall` (its own documented CLI uninstaller). It drops the `/usr/local/bin/docker*` symlinks, `com.docker.vmnetd`, and the `~/Library/Containers/com.docker.docker` VM disk — but it leaves `/Library/LaunchDaemons/com.docker.socket.plist` plus `/Library/PrivilegedHelperTools/com.docker.socket` behind, and does not delete `/Applications/Docker.app`. An "operation not permitted" complaint about `.com.apple.containermanagerd.metadata.plist` at the end is normal. Wipe `~/.docker` afterwards (Desktop's `credsStore` and contexts live there) and write it back with just `credsStore` + `cliPluginsExtraDirs`.

### `colima/colima.yaml` — the `mounts:` list is a security control

`colima/colima.yaml` is committed and symlinked to `~/.colima/default/colima.yaml`. Only one block in it is load-bearing:

```yaml
mounts:
  - location: ~/wrksp
    writable: true
  - location: /var/folders
    writable: true
```

**The Mac Studio links `colima/colima.studio.yaml` instead**, which mounts `~/fleet/work`, the agents' worktrees, in place of `~/wrksp`, and the same `/var/folders`; keep the two files identical apart from that one entry.

**`colima start` must not write the file back.** By default every start re-encodes the config into Colima's own commented template and writes it to `~/.colima/default/colima.yaml` (`--save-config`, on unless `COLIMA_SAVE_CONFIG` says otherwise), which through the link would rewrite this repo's file, and fails outright on the Studio, whose link points at the deploy-owned `/opt/rc` (`error writing yaml file: … permission denied`). `.zshrc`, `bin/colima-watchdog` and the Studio's `zsh/studio.zshenv` set `COLIMA_SAVE_CONFIG=0`, so change settings here: a `colima start --cpus …` flag then lasts one start. The link stays a link because on the Studio a copy would belong to the shared user, who could then edit its `mounts:`. Colima keeps the arch, `vmType`, runtime, `mountType` and network mode of the VM it created and warns that a new value is "discarded"; those need `colima delete` and a fresh start. `~/.colima/_templates/default.yaml` is no alternative: Colima reads it only when a profile has no config yet.

**`~/wrksp`, not an absolute path** — this file is one symlink shared by two Macs with different homes (`/Users/nielsmadan` here, `/Users/nielsm` on the mini). Colima expands `~` per machine when it writes the lima config, so the absolute form silently mounted nothing on the other box. Verify the expansion landed with `grep -A4 '^mounts:' ~/.colima/_lima/colima/lima.yaml`.

**This is the same control the Docker Desktop `filesharingDirectories` key used to provide, and it exists for the same reason.** Agents run inside a [nono](https://nono.sh) sandbox enforced by Seatbelt, but the container daemon is *outside* that boundary — so anything holding the socket can ask it to bind-mount a host path and write through it. Mounting `$HOME` would make `docker run -v /Users/nielsmadan:/h …` a one-line escape from every restriction, including the `~/.ssh` and `~/.zshrc` denies nono marks unremovable.

Enforcement is **structural, not policy**: `dockerd` runs inside the VM, so a host path the VM never mounted does not exist in the daemon's namespace. An out-of-scope `-v` yields an empty directory and writes into the VM's own filesystem, never the host. Verify after any change:

```bash
colima ssh -- mount | grep virtiofs   # must list ONLY wrksp and /var/folders
docker run --rm -v $HOME:/h alpine ls /h    # must NOT show real home contents
docker run --rm -v ~/wrksp:/w alpine ls /w   # must work
```

Check `mount`, not `ls`. An out-of-scope `-v` leaves an empty directory behind in the guest that outlives the container, so `ls $HOME` accumulates entries that were never mounts — guest `~/ac` is one, left by a past escape probe. Those stale dirs make the `ls` form report a breach that isn't there; `mount` shows only live virtiofs.

Two things that make this work, neither of them obvious:

- **An explicit `mounts:` list REPLACES the default, it does not merge.** `environment/vm/lima/yaml.go` branches on `len(conf.Mounts) == 0` → mount `~` writable, else use only the listed entries. The shipped default is an *empty* list, i.e. **whole `$HOME` writable** — so a fresh `colima start` with no config is exactly the escape this guards against. This replace-not-merge behaviour is also why Colima beats raw Lima here: Lima's own `FillDefault` unions mount lists with no removal semantics, so a Lima `override.yaml` can only ever *add* mounts. (Same flaw rules out Rancher Desktop, which hardcodes `~` writable in `getMounts()` and regenerates it on every start.)
- **`/var/folders` is needed for testcontainers**, which `namefinder`'s api and workers packages use — macOS `$TMPDIR` lives under it. `/tmp` is deliberately *not* mounted: mounting host `/private/tmp` onto the guest `/tmp` would shadow the VM's own.

**Unlike Docker Desktop's `settings.json`, nothing rewrites this file.** Docker Desktop owned its config, rewrote it on every settings change, replaced the symlink with a real file, and could only be edited while fully quit — which is why the hardening never actually landed there. Colima reads its config and leaves it alone; `colima restart` preserves the symlink (verified). Changing the mount list does need a restart to take effect, and `mountType` specifically cannot change after VM creation.

### Gotchas

- **Autostart is `bin/colima-watchdog`, not `brew services`.** `install.sh` links it and loads `launchd/com.nielsmadan.colima-watchdog.plist` on every machine, and unloads `sh.brew.colima` if it finds it (that restarts the VM once). At login the watchdog starts a Stopped VM; after that it checks every 30s and repairs a VM that Colima calls Running or Broken while `docker version` has failed three checks in a row, at most once per 10 minutes. A VM that says Stopped after login is left alone, so `colima stop` sticks, and it never holds Colima in the foreground, so a manual `colima start` is harmless. Log: `~/Library/Logs/colima-watchdog.log`; `colima-watchdog check` prints what it sees. Skip it per machine with `colima-watchdog-agent` in `install.local`. Tests: `python3 bin/test_colima_watchdog.py`.
- **Why not `brew services start colima`.** The formula runs `colima start -f` (`--foreground`) under `keep_alive successful_exit: true` and trusts Colima's status. Any manual `colima start` leaves the VM up when the job next runs, so the job logs `already running, ignoring`, exits 0, and launchd respawns it every 10s forever; in that loop a `colima stop` is undone within 10s. It also cannot see the dead-VM case below. Both happened on 2026-11-04: a logout killed the VM, and the service looped `already running` for 22 hours while docker was down.
- **`colima list` reports `Running` for a VM that is dead.** Lima's VZ driver exits the hostagent only on `VirtualMachineStateStopped`; `VirtualMachineStateError` falls through to a debug log (`pkg/driver/vz/vm_darwin.go`, v2.2.1 and master as of 2026-11-05). So when the VM process dies, the hostagent lives on, `colima list` says Running, and `docker.sock` goes nowhere: "Cannot connect to the Docker daemon", or `ECONNREFUSED` on published ports. The tell is `colima status` failing with `error retrieving current runtime: empty value` while `colima list` says Running, and `ha.stderr.log` showing `VirtualMachineStateError` / `VZErrorDomain Code=3 "The virtual machine is no longer live."`. **A logout causes it**: loginwindow quits "Virtual Machine Service for limactl" before colima gets SIGTERM, and the hostagent, in its own process group under launchd, survives into the next session. A restart that macOS turns into a logout does the same, and the kernel boot time then stays unchanged. Earlier occurrences (2026-08-15, 2026-08-20) had no known trigger. **Fix by hand with `LIMA_HOME=~/.colima/_lima limactl stop --force colima` then `colima start`.** `colima stop --force` hangs after `stopping colima` in this state; measured at the 120s timeout on 2026-11-05, while the limactl form returned at once. The watchdog does this itself. For a real liveness check use `docker version --format '{{.Server.Version}}'`, which goes through the socket; `colima list` does not.
- **Reproducing the dead VM**, to test the watchdog: `pkill -9 -f com.apple.Virtualization.VirtualMachine`. `colima list` keeps saying Running and docker fails within seconds. Measured 2026-11-05: the watchdog logged `repair:` 118s after the kill and docker answered at 132s. Then `colima stop`, wait two minutes, and `colima list` should still say Stopped.
- Registry auth moved from Docker Desktop's `desktop` credential helper to `osxkeychain` (`~/.docker/config.json`), so a `docker login` may be needed once. `cliPluginsExtraDirs` in that file points at `/opt/homebrew/lib/docker/cli-plugins` so the brew compose/buildx plugins are found.
- `binfmt: true` is set, so amd64/386 images run under emulation without extra setup. `rosetta` is off.
