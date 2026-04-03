from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from competitive_research import (
    CompetitiveBatchReport,
    CompetitiveProviderSpec,
    CompetitiveRunResult,
    CompetitiveTopicResult,
    build_local_architecture_provider_specs,
    save_competitive_batch_report,
    update_competitive_results_ledger,
)
from research import ResearchContext


class FakeCompetitiveProvider:
    async def build_research_context(self, query: str) -> ResearchContext | None:
        return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
        prior_outputs: dict[str, str] | None = None,
    ) -> str:
        return "placeholder"

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        return "placeholder"

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {"configuredProvider": "fake", "isFallback": True}


class CompetitiveResearchTests(unittest.TestCase):
    def _make_report(self) -> CompetitiveBatchReport:
        provider_specs = (
            CompetitiveProviderSpec(label="ARIA", model_name="local-model", provider_factory=lambda: FakeCompetitiveProvider()),
            CompetitiveProviderSpec(label="Gemini", model_name="gemini-model", provider_factory=lambda: FakeCompetitiveProvider()),
            CompetitiveProviderSpec(label="GPT", model_name="gpt-model", provider_factory=lambda: FakeCompetitiveProvider()),
        )
        provider_results = (
            CompetitiveRunResult(
                label="ARIA",
                model_name="local-model",
                session_id="session-aria",
                query="How should we harden an API gateway for regulated enterprise traffic?",
                final_answer="## Executive Summary\nARIA report",
                quality_report={"overallScore": 90.0, "trustScore": 80.0},
                diagnostics={"configuredProvider": "local"},
                runtime_seconds=1.2,
            ),
            CompetitiveRunResult(
                label="Gemini",
                model_name="gemini-model",
                session_id="session-gemini",
                query="How should we harden an API gateway for regulated enterprise traffic?",
                final_answer="## Executive Summary\nGemini report",
                quality_report={"overallScore": 82.0, "trustScore": 74.0},
                diagnostics={"configuredProvider": "gemini"},
                runtime_seconds=1.4,
            ),
            CompetitiveRunResult(
                label="GPT",
                model_name="gpt-model",
                session_id="session-gpt",
                query="How should we harden an API gateway for regulated enterprise traffic?",
                final_answer="## Executive Summary\nGPT report",
                quality_report={"overallScore": 78.0, "trustScore": 70.0},
                diagnostics={"configuredProvider": "openrouter"},
                runtime_seconds=1.5,
            ),
        )
        topic = CompetitiveTopicResult(
            query="How should we harden an API gateway for regulated enterprise traffic?",
            provider_results=provider_results,
            winner="ARIA",
            notes=("ARIA wins on score and trust.",),
        )
        return CompetitiveBatchReport(
            batch_name="Demo Batch",
            generated_at=1_775_000_000.0,
            topics=(topic,),
            provider_specs=provider_specs,
        )

    def test_save_competitive_report_writes_markdown_and_json(self) -> None:
        report = self._make_report()
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_path = Path(temp_dir) / "competitive-report.md"
            md_result, json_result = save_competitive_batch_report(report, str(markdown_path))

            self.assertEqual(Path(md_result), markdown_path)
            self.assertTrue(Path(md_result).exists())
            self.assertTrue(Path(json_result).exists())
            self.assertIn("# Demo Batch", Path(md_result).read_text(encoding="utf-8"))
            self.assertIn("ARIA report", Path(md_result).read_text(encoding="utf-8"))
            self.assertIn("Gemini report", Path(md_result).read_text(encoding="utf-8"))
            self.assertIn("GPT report", Path(md_result).read_text(encoding="utf-8"))

    def test_update_ledger_appends_competitive_row(self) -> None:
        report = self._make_report()
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "aria-competitive-results.md"
            updated_path = update_competitive_results_ledger(report, str(ledger_path))

            self.assertEqual(Path(updated_path), ledger_path)
            ledger_text = ledger_path.read_text(encoding="utf-8")
            self.assertIn("Demo Batch (1 topics)", ledger_text)
            self.assertIn("Research Quality: ARIA vs Gemini vs GPT", ledger_text)
            self.assertIn("xychart-beta", ledger_text)

    def test_local_architecture_specs_are_generated(self) -> None:
        specs = build_local_architecture_provider_specs(max_architectures=4)

        self.assertGreaterEqual(len(specs), 3)
        self.assertTrue(all(spec.label.startswith("Local-") for spec in specs))
        self.assertTrue(all(spec.role_models for spec in specs))


if __name__ == "__main__":
    unittest.main()
