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

- **Autostart differs per machine.** Here `colima start` / `colima stop` are yours to run. On the mini — reached over ssh, where a stopped VM means every `docker` command fails with no console to notice — `brew services start colima` is enabled, which is the autostart path Colima's own FAQ endorses. The `-f` in the formula's `colima start -f` is `--foreground`, not `--force`: the job is *meant* to block for the VM's lifetime, and `keep_alive successful_exit: true` restarts it if colima exits. **So never `colima start` by hand on a machine where that service is loaded** — the foreground job then finds the VM already up, logs `already running, ignoring`, exits 0, and launchd respawns it every 10s forever into an unrotated `/opt/homebrew/var/log/colima.log`. Untangle with `brew services stop colima && colima stop && brew services start colima`, then confirm `launchctl list sh.brew.colima` holds a stable PID.
- **`colima list` reports `Running` for a VM that is dead.** The lima hostagent hosts the VZ VM in-process and keeps reporting `Running` after the VM dies, leaving a stale `docker.sock` behind — so every `docker` command fails with "Cannot connect to the Docker daemon" while Colima insists it's up. The tell is `colima status` failing with `error retrieving current runtime: empty value` while `colima list` says Running. Confirm in `~/.colima/_lima/colima/ha.stderr.log`: `[VZ] - vm state change: VirtualMachineStateError` followed by `VZErrorDomain Code=3 "The virtual machine is no longer live."` repeating forever. Fix: **`colima stop --force`** then `colima start` — a plain `colima stop` can't stop a VM that isn't answering. Seen 2026-08-15 and 2026-08-20; the second went unnoticed for two days. Cause unknown. For a real liveness check use `docker version --format '{{.Server.Version}}'`, which exercises the socket end to end — `colima list` does not.
- Registry auth moved from Docker Desktop's `desktop` credential helper to `osxkeychain` (`~/.docker/config.json`), so a `docker login` may be needed once. `cliPluginsExtraDirs` in that file points at `/opt/homebrew/lib/docker/cli-plugins` so the brew compose/buildx plugins are found.
- `binfmt: true` is set, so amd64/386 images run under emulation without extra setup. `rosetta` is off.
