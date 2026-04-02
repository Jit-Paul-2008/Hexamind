from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _service_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "ai-service"


def _load_benchmarking():
    service_dir = _service_dir()
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    from benchmarking import (  # type: ignore
        compare_with_previous_report,
        extended_benchmark_suite,
        run_benchmark_suite,
        save_benchmark_report,
    )

    return run_benchmark_suite, extended_benchmark_suite, save_benchmark_report, compare_with_previous_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hexamind benchmark suite and optionally compare with previous report.")
    parser.add_argument("--suite", choices=["default", "extended"], default="extended")
    parser.add_argument("--output", default="", help="Path for current benchmark JSON report")
    parser.add_argument("--compare-with", default="", help="Path to previous benchmark JSON report")
    args = parser.parse_args()

    run_benchmark_suite, extended_benchmark_suite, save_benchmark_report, compare_with_previous_report = _load_benchmarking()

    cases = None if args.suite == "default" else extended_benchmark_suite()
    report = run_benchmark_suite(cases=cases, suite_name=args.suite)
    out_path = save_benchmark_report(report, args.output or None)

    payload = {
        "suite": report.suite_name,
        "winRate": report.win_rate,
        "averageScoreDelta": report.average_score_delta,
        "averageTrustDelta": report.average_trust_delta,
        "passingRate": report.passing_rate,
        "regressionCount": report.regression_count,
        "outputPath": out_path,
    }

    if args.compare_with:
        alerts = compare_with_previous_report(report, args.compare_with)
        payload["alerts"] = [
            {
                "metric": a.metric,
                "previous": a.previous,
                "current": a.current,
                "delta": a.delta,
                "threshold": a.threshold,
                "severity": a.severity,
                "message": a.message,
            }
            for a in alerts
        ]
        payload["alertCount"] = len(alerts)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

