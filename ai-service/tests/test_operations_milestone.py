from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from pipeline import PipelineService
from research import ResearchContext, ResearchSource
from workflow import build_workflow_profile


class _TelemetryPipelineProvider:
    async def build_research_context(self, query: str) -> ResearchContext:
        profile = build_workflow_profile(query)
        return ResearchContext(
            query=query,
            workflow_profile=profile,
            search_terms=("telemetry", "trace"),
            search_passes=("official",),
            sources=(
                ResearchSource(
                    id="S1",
                    title="Operations note",
                    url="https://example.gov/ops",
                    domain="example.gov",
                    snippet="",
                    excerpt="Official guidance recommends staged rollout and traceable run metadata.",
                    authority="primary",
                    credibility_score=0.96,
                    recency_score=1.0,
                    discovery_pass="official",
                ),
            ),
            generated_at=0.0,
            contradictions=(),
        )

    async def build_agent_text(self, agent_id: str, query: str, research: ResearchContext | None = None) -> str:
        return (
            f"## {agent_id.title()}\n"
            "- Traceable output with a source citation [S1]\n"
            "- Operational telemetry is available [S1]\n"
        )

    async def compose_final_answer(self, query: str, outputs: dict[str, str], research: ResearchContext | None = None) -> str:
        return (
            "## Executive Summary\n"
            "- Run metadata is captured for reproducible launch review [S1]\n"
            "## Research Scope\n"
            "- Trace coverage and timing data are part of the report artifact [S1]\n"
            "## Evidence Snapshot\n"
            "- Source inventory includes an operations note [S1]\n"
            "## Analytical Breakdown\n"
            "### Claim Graph\n"
            "- C1: telemetry is emitted for each completed run -> [S1]\n"
            "## Decision Recommendation\n"
            "- Launch with operational reporting enabled [S1]\n"
            "## Action Plan\n"
            "- Monitor queue wait, retrieval, agent, final, and quality timings [S1]\n"
            "## Confidence and Open Questions\n"
            "- Confidence is moderate pending live load tests [S1]\n"
            "## Source Inventory\n"
            "- S1: https://example.gov/ops\n"
        )

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": "telemetry-test",
            "activeProvider": "telemetry-test",
            "modelName": "telemetry",
            "isFallback": False,
            "fallbackCount": 0,
            "lastError": "",
            "circuitState": "closed",
        }


class OperationsMilestoneTests(unittest.TestCase):
    def test_quality_report_contains_run_metadata(self) -> None:
        service = PipelineService(model_provider=_TelemetryPipelineProvider())
        session_id = service.start("How should we surface launch telemetry for the research pipeline?")

        async def run_stream() -> None:
            async for _ in service.stream_events(session_id):
                pass

        asyncio.run(run_stream())

        report = service.get_quality_report(session_id)
        metadata = report["runMetadata"]

        self.assertEqual(report["status"], "ready")
        self.assertTrue(metadata["traceCoverage"])
        self.assertIn("stageTimings", metadata)
        self.assertGreater(metadata["stageTimings"]["totalSeconds"], 0)
        self.assertEqual(metadata["providerDiagnostics"]["configuredProvider"], "telemetry-test")


if __name__ == "__main__":
    unittest.main()