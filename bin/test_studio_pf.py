import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("studio-pf")

PFCTL = """#!/bin/sh
echo "pfctl $*" >> "$STUB_LOG"
if [ "$1 $2" = "-s info" ]; then echo "Status: $STUB_STATUS for 0 days"; fi
"""


class StudioPfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.log = root / "log"
        pfctl = root / "pfctl"
        pfctl.write_text(PFCTL)
        pfctl.chmod(0o755)
        self.env = {
            **os.environ,
            "STUDIO_PFCTL": str(pfctl),
            "STUDIO_PF_RULES": "/rules.conf",
            "STUB_LOG": str(self.log),
        }

    def run_helper(self, status):
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT)],
            env={**self.env, "STUB_STATUS": status}, capture_output=True, text=True, timeout=30,
        )
        return result, self.log.read_text().splitlines()

    def test_loads_the_anchor_and_enables_a_disabled_pf(self):
        result, calls = self.run_helper("Disabled")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            ["pfctl -q -a com.apple/900.studio-isolation -f /rules.conf", "pfctl -s info", "pfctl -q -E"],
        )

    def test_reloads_the_anchor_without_another_enable_reference_when_pf_is_on(self):
        result, calls = self.run_helper("Enabled")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["pfctl -q -a com.apple/900.studio-isolation -f /rules.conf", "pfctl -s info"])


class PfRulesTests(unittest.TestCase):
    def test_rules_parse(self):
        rules = Path(__file__).parent.parent / "studio" / "pf-isolation.conf"
        result = subprocess.run(
            ["/sbin/pfctl", "-n", "-a", "com.apple/900.studio-isolation", "-f", str(rules)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
