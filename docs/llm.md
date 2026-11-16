# LLM host (`llm` profile)

A Linux box with an NVIDIA GPU that serves an OpenAI-compatible API to the fleet over Tailscale; today the ASUS Ascent GX10 (`gx10`, DGX OS). The machine's setup history, measurements and open steps live in the notes vault (`work/localllm/gx10-setup.md`); this file is how the repo side works.

## What runs

- **`llm.service`**: `docker compose up` in `/srv/llm` with `llm/compose.yaml`. vLLM (pinned image digest and model revision) as the `vllm` system user, all capabilities dropped, behind nginx (`llm/nginx.conf`). nginx publishes on the Tailscale address and `127.0.0.1`, port 8000, and passes only `/v1/{chat/completions,completions,models,messages,messages/count_tokens,responses}` and `/health`; vLLM's other routes (`/invocations`, `/pause`, `/update_weights`, ...) have no authentication, so they get 404. The unit waits for the Tailscale address and restarts on failure.
- **`llm-egress.service`**: loads `llm/egress.nft`, table `inet llm_egress`. No new connections from the host or its containers to the home network (RFC 1918, link-local, ULA, multicast, and IPv6 reached on-link whatever the prefix), except DNS and DHCP to the router, ping to the router, mDNS, and tailscaled's port 41641. It also drops new LAN connections to published container ports. Rejects are logged as `llm-egress-drop`. It does not stop root.
- **`/etc/llm/llm.env`** (root, 0600): `TS_IP`, the `vllm` IDs, and `VLLM_API_KEY`, generated on the first run and never printed. Clients read the same key from `GX10_API_KEY` in their own secrets.
- **`/etc/llm/egress-local.nft`**: the machine's `LAN_IFS`, `ROUTER4`, `ROUTER_LL` and `ROUTER_IID`, written from the routes on the first run and kept out of this public repo. Edit it by hand when the router or the interfaces change (a cable, the CX7), then re-run `llm-install`. `ROUTER_LL` must be the router's current link-local address or IPv6 internet stops; IPv4 keeps working.
- NetworkManager's connected LAN connections get `ipv6.ignore-auto-dns yes`: the router keeps advertising its DNS address from the previous IPv6 prefix, which changes daily, and `systemd-resolved` got stuck on it (SERVFAIL for everything). DNS goes to the router's IPv4 address instead. A connection that comes up later (a new cable) needs another `llm-install` run.

## Install and update

The machine runs a root-owned checkout at `/opt/rc`, so nothing the login user or an agent can write runs as root.

```
sudo git clone https://github.com/nielsmadan/rc /opt/rc
sudo /opt/rc/bin/llm-install --check --profile llm
sudo /opt/rc/bin/llm-install --profile llm
```

Prerequisites: Docker with the NVIDIA runtime (DGX OS ships both), NetworkManager, nftables, and Tailscale logged in. The first start downloads the vLLM image and the model; follow it with `journalctl -u llm -f`.

After a push: `sudo git -C /opt/rc pull --ff-only && sudo /opt/rc/bin/llm-install --check`, then without `--check`. It installs only files that differ, reloads the egress table when it changed, and restarts `llm.service` only when the compose file, `nginx.conf`, the unit or the Tailscale address changed (pulling images only for a compose change). Test a change from a clone first: `llm-install` takes its files from the checkout it runs from.

Check with the key: `sudo bash /opt/rc/llm/test-with-key.sh`. Undo the egress block: `sudo systemctl disable --now llm-egress`.

Tests: `python3 bin/test_llm_install.py` (stubs for systemctl, nmcli, ip, docker, nft and the rest, runs on the Mac).

## Gotchas

- Hugging Face's Xet downloader stalled twice on an idle connection with no timeout during the first model download; `HF_HUB_DISABLE_XET=1` in the compose file makes it plain HTTPS, which times out and resumes.
- `llm-install` retires the earlier `gx10-egress.service` (`/etc/gx10-egress.nft`, table `gx10_egress`) after `llm_egress` is loaded, so there is no gap.
- The router's Tailscale port mapping (NAT-PMP/PCP 5351, UPnP 1900/49000) is blocked on purpose; direct paths rely on hole punching.
