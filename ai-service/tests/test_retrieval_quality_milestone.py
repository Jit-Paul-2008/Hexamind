from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from quality import analyze_pipeline_quality
from research import (
    ResearchContext,
    ResearchSource,
    _detect_source_contradictions,
    _rank_and_dedupe_candidates,
)
from workflow import build_workflow_profile


class RetrievalQualityMilestoneTests(unittest.TestCase):
    def test_workflow_builds_intent_specific_search_passes(self) -> None:
        profile = build_workflow_profile("Compare GPT vs Gemini for latest policy research")

        self.assertIn("comparison", profile.search_passes)
        self.assertIn("recent", profile.search_passes)
        self.assertIn("official", profile.search_passes)
        self.assertIn("evidence", profile.search_passes)

    def test_ranked_sources_filter_boilerplate_and_duplicates(self) -> None:
        candidates = [
            (
                0.55,
                ResearchSource(
                    id="",
                    title="National AI guidance",
                    url="https://www.gov.example/guidance",
                    domain="www.gov.example",
                    snippet="Updated guidance for current research workflows.",
                    excerpt="Updated guidance for current research workflows with implementation detail.",
                    authority="primary",
                    credibility_score=0.95,
                    recency_score=1.0,
                    discovery_pass="official",
                ),
            ),
            (
                0.52,
                ResearchSource(
                    id="",
                    title="National AI guidance duplicate",
                    url="https://blog.example/national-ai-guidance",
                    domain="blog.example",
                    snippet="Updated guidance for current research workflows.",
                    excerpt="Updated guidance for current research workflows with implementation detail.",
                    authority="secondary",
                    credibility_score=0.35,
                    recency_score=0.2,
                    discovery_pass="recent",
                ),
            ),
            (
                0.5,
                ResearchSource(
                    id="",
                    title="Cookie policy",
                    url="https://example.com/privacy",
                    domain="example.com",
                    snippet="Cookie policy and terms of service.",
                    excerpt="Cookie policy and terms of service for the site.",
                    authority="secondary",
                    credibility_score=0.1,
                    recency_score=0.1,
                    discovery_pass="evidence",
                ),
            ),
        ]

        selected = _rank_and_dedupe_candidates(candidates, build_workflow_profile("Compare GPT vs Gemini for latest policy research"))

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][1].title, "National AI guidance")

    def test_contradictions_feed_quality_analysis(self) -> None:
        sources = (
            ResearchSource(
                id="S1",
                title="Study A",
                url="https://example.com/a",
                domain="example.com",
                snippet="",
                excerpt="This method shows strong evidence of improvement and success.",
                authority="high",
                credibility_score=0.8,
                recency_score=0.7,
                discovery_pass="evidence",
            ),
            ResearchSource(
                id="S2",
                title="Study B",
                url="https://example.com/b",
                domain="example.com",
                snippet="",
                excerpt="This method has weak evidence, limitation risk, and may fail in practice.",
                authority="high",
                credibility_score=0.8,
                recency_score=0.7,
                discovery_pass="evidence",
            ),
        )
        contradictions = tuple(_detect_source_contradictions("Does the method work?", sources))
        research = ResearchContext(
            query="Does the method work?",
            workflow_profile=build_workflow_profile("Does the method work?"),
            search_terms=("method work",),
            search_passes=("evidence",),
            sources=sources,
            generated_at=0.0,
            contradictions=contradictions,
        )

        report = analyze_pipeline_quality(
            query="Does the method work?",
            assembled={"advocate": "- Claim supported by evidence [S1]", "skeptic": "- Contradiction noted [S2]"},
            final_answer="## Executive Summary\n- Contradiction discussed explicitly [S1][S2]\n",
            research=research,
        )

        self.assertGreaterEqual(report["metrics"]["contradictionCount"], 1)
        self.assertTrue(report["contradictionFindings"])


if __name__ == "__main__":
    unittest.main()
