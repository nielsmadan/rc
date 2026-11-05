from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("colima-watchdog")

COLIMA = """#!/bin/sh
d="$WD_TEST_DIR"
case "$1" in
  list) printf '{"name":"default","status":"%s"}\\n' "$(sh "$d/next" "$d/status.seq")" ;;
  stop) echo "stop $*" >> "$d/calls"; echo Stopped > "$d/status.seq" ;;
  start)
    echo "start $*" >> "$d/calls"; echo Running > "$d/status.seq"
    echo "${COLIMA_SAVE_CONFIG-unset}" > "$d/save_config"
    [ -f "$d/start_heals" ] && echo ok > "$d/docker.seq"
    exit "$(cat "$d/start_exit" 2>/dev/null || echo 0)" ;;
esac
"""

NEXT = """f="$1"
head -n 1 "$f"
if [ "$(wc -l < "$f")" -gt 1 ]; then tail -n +2 "$f" > "$f.tmp" && mv "$f.tmp" "$f"; fi
"""

DOCKER = """#!/bin/sh
[ "$(sh "$WD_TEST_DIR/next" "$WD_TEST_DIR/docker.seq")" = ok ]
"""

LIMACTL = """#!/bin/sh
echo "limactl $* home=$LIMA_HOME" >> "$WD_TEST_DIR/calls"; echo Stopped > "$WD_TEST_DIR/status.seq"
"""

LAUNCHCTL = """#!/bin/sh
exit 1
"""

PGREP = """#!/bin/sh
d="$WD_TEST_DIR"
[ -f "$d/busy" ] || { [ -f "$d/busy.seq" ] && [ "$(sh "$d/next" "$d/busy.seq")" = busy ]; }
"""

OSASCRIPT = """#!/bin/sh
echo "notify" >> "$WD_TEST_DIR/calls"
"""


class ColimaWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        stubs = self.dir / "stubs"
        stubs.mkdir()
        for name, body in [("colima", COLIMA), ("docker", DOCKER), ("pgrep", PGREP), ("osascript", OSASCRIPT),
                           ("launchctl", LAUNCHCTL), ("limactl", LIMACTL)]:
            path = stubs / name
            path.write_text(body)
            path.chmod(0o755)
        (self.dir / "next").write_text(NEXT)
        self.env = {
            "PATH": f"{stubs}:/usr/bin:/bin",
            "HOME": str(self.dir),
            "WD_TEST_DIR": str(self.dir),
            "COLIMA_WATCHDOG_INTERVAL": "0",
            "COLIMA_WATCHDOG_THRESHOLD": "3",
            "COLIMA_WATCHDOG_COOLDOWN": "3600",
            "COLIMA_WATCHDOG_LOG": str(self.dir / "watchdog.log"),
        }

    @property
    def force_stop(self):
        return f"limactl stop --force colima home={self.dir}/.colima/_lima"

    def run_watchdog(self, status, docker, ticks):
        status = [status] if isinstance(status, str) else status
        (self.dir / "status.seq").write_text("\n".join(status) + "\n")
        (self.dir / "docker.seq").write_text("\n".join(docker) + "\n")
        result = subprocess.run(
            ["/bin/sh", str(SCRIPT), "run"],
            env={**self.env, "COLIMA_WATCHDOG_TICKS": str(ticks)},
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.dir / "calls"
        return calls.read_text().splitlines() if calls.exists() else []

    def test_healthy_vm_is_left_alone(self):
        self.assertEqual(self.run_watchdog("Running", ["ok"], ticks=5), [])

    def test_stopped_vm_is_started_at_login(self):
        self.assertEqual(self.run_watchdog("Stopped", ["fail"], ticks=1), ["start start --profile default"])

    def test_start_leaves_the_linked_config_unwritten(self):
        self.run_watchdog("Stopped", ["fail"], ticks=1)
        self.assertEqual((self.dir / "save_config").read_text(), "0\n")

    def test_vm_stopped_after_login_stays_stopped(self):
        self.assertEqual(self.run_watchdog(["Running", "Stopped"], ["ok", "fail"], ticks=6), [])

    def test_dead_vm_reported_running_is_repaired_after_threshold(self):
        (self.dir / "start_heals").touch()
        calls = self.run_watchdog("Running", ["fail"], ticks=6)
        self.assertEqual(calls, ["notify", self.force_stop, "start start --profile default"])
        self.assertIn("repair: colima says Running", (self.dir / "watchdog.log").read_text())

    def test_two_failures_do_not_repair(self):
        self.assertEqual(self.run_watchdog("Running", ["fail", "fail", "ok", "fail", "fail", "ok"], ticks=6), [])

    def test_broken_status_is_repaired(self):
        calls = self.run_watchdog("Broken", ["fail"], ticks=3)
        self.assertEqual(calls[1:], [self.force_stop, "start start --profile default"])

    def test_repair_that_does_not_help_waits_for_cooldown(self):
        calls = self.run_watchdog("Running", ["fail"], ticks=12)
        self.assertEqual(calls.count(self.force_stop), 1)
        self.assertIn("last repair under 3600s ago", (self.dir / "watchdog.log").read_text())

    def test_repair_repeats_once_cooldown_has_passed(self):
        self.env["COLIMA_WATCHDOG_COOLDOWN"] = "0"
        calls = self.run_watchdog("Running", ["fail"], ticks=6)
        self.assertEqual(calls.count(self.force_stop), 2)

    def test_nothing_happens_while_another_colima_command_runs(self):
        (self.dir / "busy").touch()
        self.assertEqual(self.run_watchdog("Running", ["fail"], ticks=6), [])
        self.assertEqual(self.run_watchdog("Stopped", ["fail"], ticks=1), [])

    def test_login_start_waits_out_a_colima_command_still_running(self):
        (self.dir / "busy.seq").write_text("busy\nidle\n")
        self.assertEqual(self.run_watchdog("Stopped", ["fail"], ticks=3), ["start start --profile default"])

    def test_failed_start_notifies(self):
        (self.dir / "start_exit").write_text("1\n")
        calls = self.run_watchdog("Stopped", ["fail"], ticks=1)
        self.assertEqual(calls, ["start start --profile default", "notify"])
        self.assertIn("colima start: FAILED", (self.dir / "watchdog.log").read_text())

    def test_missing_colima_exits_cleanly(self):
        self.env["PATH"] = "/usr/bin:/bin"
        result = subprocess.run(
            ["/bin/sh", str(SCRIPT), "run"], env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("colima not on PATH", (self.dir / "watchdog.log").read_text())


if __name__ == "__main__":
    unittest.main()
