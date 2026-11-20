import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("llm-install")
RC_LLM = Path(__file__).resolve().parent.parent / "llm"
FIRST_RUN = ("--profile", "llm", "--host", "gx10")

STUBS = {
    # Units are enabled and active once `enable --now` ran, until `disable --now`.
    "systemctl": """#!/bin/sh
echo "systemctl $*" >> "$STUB_LOG"
case "$1" in
  is-enabled|is-active) [ -e "$STUB_STATE/unit-$3" ] ;;
  enable) touch "$STUB_STATE/unit-$3" ;;
  disable) rm -f "$STUB_STATE/unit-$3" ;;
esac
""",
    "nmcli": """#!/bin/sh
case "$*" in
  "-t -f DEVICE,TYPE,STATE device")
    printf 'wlP9s9:wifi:connected\\ntailscale0:tun:connected (externally)\\nenP7s7:ethernet:unavailable\\nveth1:ethernet:unmanaged\\n' ;;
  "-t -f DEVICE,TYPE,STATE,CONNECTION device")
    printf 'wlP9s9:wifi:connected:internetz\\ntailscale0:tun:connected (externally):tailscale0\\nenP7s7:ethernet:unavailable:\\n' ;;
  "-g ipv6.ignore-auto-dns connection show internetz")
    cat "$STUB_STATE/dns" 2>/dev/null || echo no ;;
  "connection modify internetz ipv6.ignore-auto-dns yes")
    echo "nmcli $*" >> "$STUB_LOG"; echo yes > "$STUB_STATE/dns" ;;
  *) echo "nmcli $*" >> "$STUB_LOG" ;;
esac
""",
    "ip": """#!/bin/sh
case "$*" in
  "-4 route show default") echo "default via 192.168.178.1 dev wlP9s9 proto dhcp src 192.168.178.131 metric 600" ;;
  "-6 route show default") echo "default via fe80::2e91:abff:fee6:ad4d dev wlP9s9 proto ra metric 600 pref medium" ;;
esac
""",
    "tailscale": """#!/bin/sh
echo "$STUB_TS_IP"
""",
    "useradd": """#!/bin/sh
echo "useradd $*" >> "$STUB_LOG"
touch "$STUB_STATE/user"
""",
    "id": """#!/bin/sh
for a in "$@"; do last="$a"; done
if [ "${last:-}" = vllm ]; then [ -e "$STUB_STATE/user" ] && echo 990; exit $?; fi
exec /usr/bin/id "$@"
""",
    # Drops the owner and group, which this user cannot set.
    "install": """#!/bin/sh
args=""
while [ $# -gt 0 ]; do
  case "$1" in -o|-g) shift 2 ;; *) args="$args '$1'"; shift ;; esac
done
eval exec /usr/bin/install $args
""",
    "docker": """#!/bin/sh
echo "docker $*" >> "$STUB_LOG"
""",
    "nft": """#!/bin/sh
echo "nft $*" >> "$STUB_LOG"
""",
}


class LlmInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.etc = root / "etc-llm"
        self.srv = root / "srv-llm"
        self.units = root / "units"
        self.units.mkdir()
        self.profile = root / "rc-profile"
        self.state = root / "state"
        self.state.mkdir()
        self.log = root / "log"
        stubs = self.stubs = root / "stubs"
        stubs.mkdir()
        for name, body in STUBS.items():
            (stubs / name).write_text(body)
            (stubs / name).chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "RC_PROFILE_FILE": str(self.profile),
            "LLM_ETC_DIR": str(self.etc),
            "LLM_SRV_DIR": str(self.srv),
            "LLM_UNIT_DIR": str(self.units),
            "LLM_OLD_EGRESS_NFT": str(root / "gx10-egress.nft"),
            "LLM_INSTALL_ROOTLESS": "1",
            "STUB_LOG": str(self.log),
            "STUB_STATE": str(self.state),
            "STUB_TS_IP": "100.64.0.7",
        }

    def run_script(self, *args):
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=self.env, capture_output=True, text=True, timeout=60,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_check_on_a_new_machine_lists_the_steps_and_writes_nothing(self):
        result, calls = self.run_script("--check", *FIRST_RUN)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"+ write llm to {self.profile}", result.stdout)
        self.assertIn('    define LAN_IFS = { "wlP9s9", "enP7s7" }', result.stdout)
        self.assertIn("+ systemctl enable --now llm.service", result.stdout)
        self.assertFalse(self.profile.exists())
        self.assertFalse(self.etc.exists())
        self.assertEqual([c for c in calls if c.startswith(("systemctl enable", "useradd", "nmcli connection"))], [])

    def test_first_run_writes_the_network_file_from_the_routes(self):
        result, _ = self.run_script(*FIRST_RUN)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.etc / "egress-local.nft").read_text().splitlines()[1:],
            [
                'define LAN_IFS = { "wlP9s9", "enP7s7" }',
                "define ROUTER4 = 192.168.178.1",
                "define ROUTER_LL = fe80::2e91:abff:fee6:ad4d",
                "define ROUTER_IID = ::2e91:abff:fee6:ad4d",
            ],
        )
        self.assertEqual(self.profile.read_text(), "llm\n")
        self.assertEqual((self.etc / "host").read_text(), "gx10\n")

    def test_first_run_creates_a_private_env_file_with_a_key(self):
        self.run_script(*FIRST_RUN)
        env_file = self.etc / "llm.env"
        self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)
        lines = env_file.read_text().splitlines()
        self.assertEqual(lines[:3], ["TS_IP=100.64.0.7", "VLLM_UID=990", "VLLM_GID=990"])
        self.assertRegex(lines[3], r"^VLLM_API_KEY=[0-9a-f]{64}$")

    def test_first_run_installs_the_files_and_starts_both_units(self):
        _, calls = self.run_script(*FIRST_RUN)
        for src, dest in [
            ("egress.nft", self.etc / "egress.nft"),
            ("llm-egress.service", self.units / "llm-egress.service"),
            ("llm.service", self.units / "llm.service"),
            ("compose.yaml", self.srv / "compose.yaml"),
            ("nginx.conf", self.srv / "nginx.conf"),
            ("hosts/gx10/engine.yaml", self.srv / "engine.yaml"),
        ]:
            self.assertEqual(dest.read_bytes(), (RC_LLM / src).read_bytes(), src)
        self.assertIn("docker compose pull --quiet", calls)
        self.assertLess(calls.index("systemctl enable --now llm-egress.service"),
                        calls.index("systemctl enable --now llm.service"))

    def test_first_run_stops_taking_dns_servers_from_router_advertisements(self):
        _, calls = self.run_script(*FIRST_RUN)
        self.assertIn("nmcli connection modify internetz ipv6.ignore-auto-dns yes", calls)
        self.assertIn("nmcli device reapply wlP9s9", calls)
        self.assertIn("systemctl restart systemd-resolved", calls)

    def test_old_gx10_egress_unit_is_retired_after_the_new_block_loads(self):
        (self.units / "gx10-egress.service").write_text("[Unit]\n")
        (self.state / "unit-gx10-egress.service").touch()
        _, calls = self.run_script(*FIRST_RUN)
        self.assertLess(calls.index("systemctl enable --now llm-egress.service"),
                        calls.index("systemctl disable --now gx10-egress.service"))
        self.assertFalse((self.units / "gx10-egress.service").exists())

    def test_second_run_has_nothing_to_do(self):
        self.run_script(*FIRST_RUN)
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "llm-install: nothing to do\n")
        self.assertEqual([c for c in calls if c.startswith("systemctl") and " is-" not in c], [])

    def test_an_existing_network_file_is_kept(self):
        self.etc.mkdir(mode=0o700)
        (self.etc / "egress-local.nft").write_text("define LAN_IFS = { \"eth9\" }\n")
        self.run_script(*FIRST_RUN)
        self.assertEqual((self.etc / "egress-local.nft").read_text(), "define LAN_IFS = { \"eth9\" }\n")

    def test_changed_nginx_conf_restarts_the_service_without_a_pull(self):
        self.run_script(*FIRST_RUN)
        (self.srv / "nginx.conf").write_text("old\n")
        _, calls = self.run_script()
        self.assertIn("systemctl restart llm.service", calls)
        self.assertNotIn("docker compose pull --quiet", calls)

    def test_new_tailscale_address_updates_the_env_file_and_keeps_the_key(self):
        self.run_script(*FIRST_RUN)
        key = (self.etc / "llm.env").read_text().splitlines()[3]
        self.env["STUB_TS_IP"] = "100.64.0.8"
        _, calls = self.run_script()
        lines = (self.etc / "llm.env").read_text().splitlines()
        self.assertEqual(lines[0], "TS_IP=100.64.0.8")
        self.assertEqual(lines[3], key)
        self.assertIn("systemctl restart llm.service", calls)

    def test_first_run_without_a_host_names_the_hosts_and_writes_nothing(self):
        result, calls = self.run_script("--profile", "llm")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pass --host NAME on the first run (hosts: gx10", result.stderr)
        self.assertFalse(self.profile.exists())
        self.assertEqual(calls, [])

    def test_unknown_host_is_refused(self):
        result, calls = self.run_script("--profile", "llm", "--host", "gx10/../gx10")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no llm/hosts/gx10/../gx10/engine.yaml", result.stderr)
        self.assertEqual(calls, [])

    def test_recorded_host_is_used_on_later_runs(self):
        self.run_script(*FIRST_RUN)
        (self.srv / "engine.yaml").write_text("old\n")
        _, calls = self.run_script()
        self.assertEqual((self.srv / "engine.yaml").read_bytes(),
                         (RC_LLM / "hosts/gx10/engine.yaml").read_bytes())
        self.assertIn("docker compose pull --quiet", calls)
        self.assertIn("systemctl restart llm.service", calls)

    def test_without_networkmanager_the_dns_step_is_skipped(self):
        (self.stubs / "nmcli").unlink()
        self.etc.mkdir(mode=0o700)
        (self.etc / "egress-local.nft").write_text('define LAN_IFS = { "eth0" }\n')
        result, calls = self.run_script(*FIRST_RUN)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("systemctl restart systemd-resolved", calls)
        self.assertIn("systemctl enable --now llm.service", calls)

    def test_without_networkmanager_or_a_network_file_asks_for_one(self):
        (self.stubs / "nmcli").unlink()
        result, _ = self.run_script(*FIRST_RUN)
        self.assertEqual(result.returncode, 1)
        self.assertIn("write " + str(self.etc / "egress-local.nft") + " by hand", result.stderr)

    def test_another_profile_is_refused(self):
        self.profile.write_text("studio\n")
        result, calls = self.run_script(*FIRST_RUN)
        self.assertEqual(result.returncode, 1)
        self.assertIn("names studio", result.stderr)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
