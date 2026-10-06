from datetime import date, datetime, timedelta
import gzip
import json
from pathlib import Path
import runpy
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("resource-log")
MODULE = runpy.run_path(str(SCRIPT))

PS_STATS = """\
  100     1  4194304  95.0 node
  101     1  2097152  10.0 node
  200    50   204800   5.0 2.1.280
  201    50   102400   1.0 /Users/me/.local/bin/claude
  300     1   512000  40.0 /Applications/Brave Browser.app/Contents/MacOS/Brave Browser Helper (Renderer)
  301     1   256000   2.0 /Applications/Brave Browser.app/Contents/MacOS/Brave Browser
  400   399    51200   0.0 node
"""
PS_ARGS = """\
  100 node (vitest 3)
  101 node (vitest 7)
  200 claude
  201 /Users/me/.local/bin/claude --resume
  300 /Applications/Brave Browser.app/Contents/MacOS/Brave Browser Helper (Renderer) --type=renderer
  301 /Applications/Brave Browser.app/Contents/MacOS/Brave Browser
  400 node /repo/node_modules/typescript/lib/tsserver.js --useInferredProjectPerProjectRoot
"""
VM_STAT = """\
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     3745.
Pages speculative:                              4011.
Pages wired down:                             671110.
Pages occupied by compressor:                2017716.
Pages stored in compressor:                  7118043.
Anonymous pages:                              961365.
File-backed pages:                            483641.
"Translation faults":                    38473705717.
"""
SWAP = "total = 37888.00M  used = 37072.56M  free = 815.44M  (encrypted)"
LOAD = "{ 274.06 336.09 340.28 }"


def sample_at(timestamp, free_mb=1000, families=None, orphans=None):
    return {
        "t": timestamp, "load": [10.0, 9.0, 8.0],
        "mem_mb": {"free": free_mb, "compressor": 2048, "swap_used": 1024},
        "agents": {"claude": 2, "codex": 1}, "orphan_node": orphans or {},
        "families": families or [["node", 4, 4096, 80.0]],
    }


class FamilyTest(unittest.TestCase):
    def test_names_processes_by_role(self):
        cases = {
            ("node", "node (vitest 3)"): "vitest",
            ("node", "node /x/typescript/lib/tsserver.js"): "tsserver",
            ("node", "node /x/.bin/context7-mcp"): "mcp",
            ("context7-mcp", "npm exec @upstash/context7-mcp"): "mcp",
            ("node", "node server.js"): "node",
            ("2.1.280", "claude"): "claude",
            ("/a/Brave Browser Helper (Renderer).app/Contents/MacOS/Brave Browser Helper (Renderer)", ""): "Brave Browser",
            ("/a/Chromium Helper", ""): "Chromium",
        }
        for (comm, args), expected in cases.items():
            with self.subTest(comm=comm, args=args):
                self.assertEqual(MODULE["family"](comm, args), expected)


class SampleTest(unittest.TestCase):
    def setUp(self):
        rows = MODULE["parse_ps"](PS_STATS, PS_ARGS)
        self.sample = MODULE["build_sample"](datetime(2026, 10, 6, 15, 24, 7), rows, VM_STAT, SWAP, LOAD, "4\n")

    def test_reads_system_memory(self):
        self.assertEqual(self.sample["mem_mb"]["free"], 121)
        self.assertEqual(self.sample["mem_mb"]["compressor"], 31527)
        self.assertEqual(self.sample["mem_mb"]["swap_used"], 37073)
        self.assertEqual(self.sample["load"], [274.06, 336.09, 340.28])
        self.assertEqual(self.sample["pressure"], 4)

    def test_aggregates_families_heaviest_first(self):
        self.assertEqual(self.sample["families"][0], ["vitest", 2, 6144, 105.0])
        self.assertEqual(self.sample["families"][1], ["Brave Browser", 2, 750, 42.0])

    def test_counts_agent_sessions_across_comm_spellings(self):
        self.assertEqual(self.sample["agents"]["claude"], 2)

    def test_reports_node_orphaned_to_launchd(self):
        self.assertEqual(self.sample["orphan_node"], {"vitest": [2, 6144]})

    def test_keeps_command_lines_of_heaviest_processes(self):
        self.assertEqual(self.sample["procs"][0], [100, 1, 4096, 95.0, "node (vitest 3)"])


class StorageTest(unittest.TestCase):
    def test_maintenance_compresses_past_days_and_drops_expired(self):
        names = ["2026-10-06.jsonl", "2026-10-05.jsonl", "2026-09-01.jsonl.gz", "notes.txt"]
        delete, compress = MODULE["maintenance_plan"](names, date(2026, 10, 6), 30)
        self.assertEqual(delete, ["2026-09-01.jsonl.gz"])
        self.assertEqual(compress, ["2026-10-05.jsonl"])

    def test_reads_back_plain_and_compressed_days_within_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            MODULE["write_sample"](log_dir, sample_at("2026-10-05T23:59:00"), date(2026, 10, 5))
            MODULE["write_sample"](log_dir, sample_at("2026-10-06T00:01:00"), date(2026, 10, 6))
            MODULE["write_sample"](log_dir, sample_at("2026-10-06T09:00:00"), date(2026, 10, 6))
            self.assertEqual(sorted(p.name for p in log_dir.iterdir()), ["2026-10-05.jsonl.gz", "2026-10-06.jsonl"])
            samples = MODULE["read_samples"](log_dir, datetime(2026, 10, 5, 23, 0))
        self.assertEqual([s["t"] for s in samples], ["2026-10-05T23:59:00", "2026-10-06T00:01:00", "2026-10-06T09:00:00"])


class ReportTest(unittest.TestCase):
    def test_timeline_keeps_worst_sample_per_bucket(self):
        samples = [
            sample_at("2026-10-06T15:01:00", free_mb=4096),
            sample_at("2026-10-06T15:05:00", free_mb=512, families=[["vitest", 9, 30720, 300.0]]),
            sample_at("2026-10-06T15:12:00", free_mb=2048),
        ]
        rows = MODULE["timeline"](samples, 10)
        self.assertEqual([r[0] for r in rows], ["10-06 15:00", "10-06 15:10"])
        self.assertEqual(rows[0][2], 0.5)
        self.assertEqual(rows[0][6], "vitest 30.0G")

    def test_family_stats_average_over_all_samples(self):
        samples = [
            sample_at("2026-10-06T15:00:00", families=[["vitest", 9, 30720, 300.0]]),
            sample_at("2026-10-06T15:01:00", families=[["node", 1, 1024, 1.0]]),
        ]
        stats = {row[0]: row for row in MODULE["family_stats"](samples)}
        self.assertEqual(stats["vitest"], ["vitest", 4.5, 15.0, 30.0, 150.0, 300.0])

    def test_orphan_peaks_record_when_they_peaked(self):
        samples = [
            sample_at("2026-10-06T15:00:00", orphans={"vitest": [3, 9000]}),
            sample_at("2026-10-06T15:01:00", orphans={"vitest": [7, 26000]}),
        ]
        self.assertEqual(MODULE["orphan_peaks"](samples), [["vitest", 7, 26000, "2026-10-06T15:01:00"]])

    def test_since_accepts_minutes_hours_days(self):
        self.assertEqual(MODULE["parse_since"]("90m"), timedelta(minutes=90))
        self.assertEqual(MODULE["parse_since"]("7d"), timedelta(days=7))


if __name__ == "__main__":
    unittest.main()
