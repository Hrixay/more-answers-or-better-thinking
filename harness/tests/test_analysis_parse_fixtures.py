"""The D-76 parse rules are pinned by Karen's fixtures (research/fixtures/sim-main-v2: parse_cases, pieces_cases, final_cases). Her runner
must report zero mismatches against this checkout's harness/analysis/trace_parse.py; the parse rules are part of the D-69 lock."""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "research" / "fixtures" / "sim-main-v2" / "run_parse_cases.py"


class KarensParseCases(unittest.TestCase):
    def test_every_case_passes(self):
        r = subprocess.run([sys.executable, str(RUNNER), str(ROOT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r"(\d+) of (\d+) cases pass", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertEqual(m.group(1), m.group(2), r.stdout)
        self.assertGreaterEqual(int(m.group(2)), 223, "fewer parse cases than Karen's round 2 (223)")


if __name__ == "__main__":
    unittest.main()
