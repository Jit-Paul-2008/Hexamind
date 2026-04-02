from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from benchmarking import default_benchmark_suite, run_benchmark_suite


class BenchmarkingMilestoneTests(unittest.TestCase):
    def test_default_suite_has_target_segments(self) -> None:
        suite = default_benchmark_suite()

        self.assertGreaterEqual(len(suite), 3)
        self.assertEqual(suite[0].domain, "policy")
        self.assertEqual(suite[1].domain, "engineering")
        self.assertEqual(suite[2].domain, "operations")

    def test_head_to_head_report_scores_candidate_outputs(self) -> None:
        report = run_benchmark_suite()

        self.assertGreaterEqual(report.win_rate, 0.66)
        self.assertGreater(report.average_score_delta, 0.0)
        self.assertGreaterEqual(report.passing_rate, 0.66)
        self.assertEqual(len(report.cases), 3)


if __name__ == "__main__":
    unittest.main()