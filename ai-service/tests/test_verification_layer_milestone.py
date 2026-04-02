from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from quality import analyze_pipeline_quality
from research import ResearchContext, ResearchSource
from workflow import build_workflow_profile


class VerificationLayerMilestoneTests(unittest.TestCase):
    def test_weakly_supported_claims_are_classified(self) -> None:
        research = self._build_research_context()
        final_answer = (
            "## Executive Summary\n"
            "- The deployment budget should be revised before launch and ownership clarified across teams [S1]\n"
            "- A separate note also mentions evidence gaps [S1]\n"
            "## Decision Recommendation\n"
            "- Proceed with caution [S1]\n"
        )

        report = analyze_pipeline_quality(
            query="Should we revise the deployment budget?",
            assembled={"advocate": final_answer, "skeptic": final_answer},
            final_answer=final_answer,
            research=research,
        )

        statuses = [item["status"] for item in report["claimVerifications"]]
        self.assertIn("weakly-supported", statuses)
        self.assertIn("trustScore", report)
        self.assertIn("citationIntegrityFindings", report)

    def test_trust_metrics_include_integrity_and_freshness(self) -> None:
        research = self._build_research_context()
        final_answer = (
            "## Executive Summary\n"
            "- Claim graph included and report plan present [S1][S2]\n"
            "## Research Scope\n"
            "- Report plan describes a policy frame [S1]\n"
            "## Analytical Breakdown\n"
            "### Claim Graph\n"
            "- Node C1 supports the rollout decision -> [S1]\n"
        )

        report = analyze_pipeline_quality(
            query="How should we change the policy for model deployment?",
            assembled={"advocate": final_answer, "skeptic": final_answer},
            final_answer=final_answer,
            research=research,
        )

        self.assertGreaterEqual(report["trustScore"], 0)
        self.assertIn("trustScoreComponents", report)
        self.assertIn("citationIntegrityScore", report["metrics"])
        self.assertIn("sourceFreshnessScore", report["metrics"])
        self.assertTrue(report["citationIntegrityFindings"])
        self.assertTrue(report["metrics"]["hasReportPlan"])

    @staticmethod
    def _build_research_context() -> ResearchContext:
        profile = build_workflow_profile("How should we change the policy for model deployment?")
        sources = (
            ResearchSource(
                id="S1",
                title="Policy memo",
                url="https://example.gov/policy",
                domain="example.gov",
                snippet="",
                excerpt="Official guidance discusses a separate topic with limited overlap.",
                authority="primary",
                credibility_score=0.95,
                recency_score=1.0,
                discovery_pass="official",
            ),
            ResearchSource(
                id="S2",
                title="Review note",
                url="https://example.org/review",
                domain="example.org",
                snippet="",
                excerpt="Independent review highlights limitations and failure modes.",
                authority="high",
                credibility_score=0.8,
                recency_score=0.7,
                discovery_pass="evidence",
            ),
        )
        contradictions = (("S1", "S2", "Policy guidance and review note diverge on rollout timing."),)
        return ResearchContext(
            query="How should we change the policy for model deployment?",
            workflow_profile=profile,
            search_terms=("policy", "deployment"),
            search_passes=("official", "evidence"),
            sources=sources,
            generated_at=0.0,
            contradictions=contradictions,
        )


if __name__ == "__main__":
    unittest.main()
