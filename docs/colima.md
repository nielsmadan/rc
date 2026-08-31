# Colima

Docker runtime for this machine, configured by [`colima/colima.yaml`](../colima/colima.yaml):
6 CPUs, 12 GB, aarch64, VZ.

## The recurring wedge is a host-side failure, not a guest one

Under severe macOS memory-compressor and swap pressure, the host stops scheduling the VM's
vCPUs for long enough that Virtualization.framework's watchdog gives up and kills it.

From inside the guest this looks alarming and misleading: soft lockups and large jumps in wall
clock, but **no OOM kill, no kernel panic, and no storage, virtio, or guest memory-pressure
fault**. Nothing in the guest is at fault, so nothing in the guest is worth tuning. The VM asks
for 12 GB, which is what makes it the thing that dies when the host is squeezed.

The routine that avoids it entirely: `colima stop` before anything memory-hungry, `colima start` afterwards.

## `Running` does not mean running

After the VM dies, the lima hostagent and the Docker socket can both survive, so `colima status`
happily reports `Running` against a VM that no longer exists.

- Confirm the mismatch in `~/.colima/_lima/colima/ha.stderr.log`.
- For an end-to-end liveness check that actually crosses into the VM, use
  `docker version --format '{{.Server.Version}}'`. The client half of `docker version` answers
  without the VM and will not tell you anything.

Recover with `colima stop --force && colima start`. Reach for `--force` only when already
wedged; it is not a routine stop.

## Checking filesystem isolation

Verify against the live `virtiofs` mounts, not a directory listing from inside the guest. A
listing shows what is reachable at that moment and cannot distinguish a mount that is absent
from one that is merely empty.
