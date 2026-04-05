from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from model_provider import DeterministicPipelineModelProvider
from research import ResearchContext, ResearchSource
from workflow import build_workflow_profile


class SynthesisQualityMilestoneTests(unittest.TestCase):
    def test_final_answer_uses_requested_paper_structure(self) -> None:
        provider = DeterministicPipelineModelProvider()
        research = self._build_research_context(
            "How should we change the policy for model deployment?",
            mode="policy",
        )
        outputs = self._build_outputs()

        report = asyncio.run(provider.compose_final_answer("How should we change the policy for model deployment?", outputs, research))

        self.assertIn("## Title", report)
        self.assertIn("## Author", report)
        self.assertIn("## Abstract", report)
        self.assertIn("## Keywords", report)
        self.assertIn("## Introduction", report)
        self.assertIn("## Methods", report)
        self.assertIn("## Results", report)
        self.assertIn("## Discussion/Conclusion", report)

    def test_final_answer_includes_references_and_domain_content(self) -> None:
        provider = DeterministicPipelineModelProvider()
        research = self._build_research_context(
            "How do we reduce latency in the backend architecture?",
            mode="engineering",
        )
        outputs = self._build_outputs()

        report = asyncio.run(provider.compose_final_answer("How do we reduce latency in the backend architecture?", outputs, research))

        self.assertIn("## References", report)
        self.assertIn("architecture", report.lower())

    @staticmethod
    def _build_outputs() -> dict[str, str]:
        return {
            "advocate": "## Strategic Upside\n- Better execution [S1]\n",
            "skeptic": "## Primary Failure Modes\n- Reliability issues [S2]\n",
            "synthesiser": "## Decision Rule\nProceed with staged deployment [S1][S2]\n",
            "oracle": "## Most Likely Outcome (60%)\nThe rollout improves metrics [S1]\n",
        }

    @staticmethod
    def _build_research_context(query: str, mode: str) -> ResearchContext:
        profile = build_workflow_profile(query)
        sources = (
            ResearchSource(
                id="S1",
                title="Primary guidance",
                url="https://example.gov/guidance",
                domain="example.gov",
                snippet="",
                excerpt="Official guidance recommends a staged rollout and direct verification.",
                authority="primary",
                credibility_score=0.95,
                recency_score=1.0,
                discovery_pass="official",
            ),
            ResearchSource(
                id="S2",
                title="Independent review",
                url="https://example.org/review",
                domain="example.org",
                snippet="",
                excerpt="Independent review notes risks, limitations, and failure modes.",
                authority="high",
                credibility_score=0.78,
                recency_score=0.7,
                discovery_pass="evidence",
            ),
        )
        contradictions = (("S1", "S2", "Evidence polarity differs across sources."),)
        return ResearchContext(
            query=query,
            workflow_profile=profile,
            search_terms=("guidance", "review"),
            search_passes=("official", "evidence"),
            sources=sources,
            generated_at=0.0,
            contradictions=contradictions,
        )


if __name__ == "__main__":
    unittest.main()
