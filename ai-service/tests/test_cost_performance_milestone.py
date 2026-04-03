from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from model_provider import _compressed_research_block, _cost_aware_agent_model, _local_model_tier
from research import InternetResearcher, ResearchContext, ResearchSource, SearchHit
from workflow import build_workflow_profile


class CostPerformanceMilestoneTests(unittest.TestCase):
    def test_local_model_tier_tracks_query_complexity(self) -> None:
        low_context = self._build_context("Notes.", source_count=1)
        high_context = self._build_context(
            "Compare policy, engineering, and medical tradeoffs for deployment, reliability, and governance.",
            source_count=6,
        )

        self.assertEqual(_local_model_tier(low_context.query, low_context), "small")
        self.assertEqual(_local_model_tier(high_context.query, high_context), "large")

    def test_cost_aware_agent_model_prefers_cheaper_defaults(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"HEXAMIND_COST_MODE": "free", "HEXAMIND_AGENT_MODEL_ADVOCATE": ""}, clear=False):
            model_name = _cost_aware_agent_model("openrouter", "advocate", "default-model")

        self.assertEqual(model_name, "google/gemini-2.0-flash-exp:free")

    def test_compressed_research_block_respects_budget(self) -> None:
        context = self._build_context("How should we optimize model routing and cache evidence?")
        compressed = _compressed_research_block(context, 600)

        self.assertLessEqual(len(compressed), 600)
        # format_research_context collapses whitespace, so Source pack and sources appear in single-line format
        self.assertIn("Source pack", compressed)
        self.assertIn("S1", compressed)

    def test_research_results_are_cached(self) -> None:
        researcher = InternetResearcher()
        source_one = ResearchSource(
            id="",
            title="Guidance A",
            url="https://example.gov/a",
            domain="example.gov",
            snippet="",
            excerpt="Official guidance recommends a staged rollout.",
            authority="primary",
            credibility_score=0.95,
            recency_score=1.0,
            discovery_pass="official",
        )
        source_two = ResearchSource(
            id="",
            title="Guidance B",
            url="https://example.org/b",
            domain="example.org",
            snippet="",
            excerpt="Independent review confirms the same staged rollout.",
            authority="high",
            credibility_score=0.8,
            recency_score=0.9,
            discovery_pass="evidence",
        )

        with patch.object(researcher, "_search_hits", new=AsyncMock(return_value=[SearchHit(title="A", url=source_one.url, snippet="", relevance_score=0.9)])) as search_hits_mock:
            with patch.object(researcher, "_build_candidates", new=AsyncMock(return_value=[(0.9, source_one), (0.8, source_two)])):
                first = asyncio.run(researcher.research("How should we optimize model routing and cache evidence?"))
                second = asyncio.run(researcher.research("How should we optimize model routing and cache evidence?"))

        self.assertEqual(search_hits_mock.call_count, 1)
        self.assertEqual(first.sources, second.sources)
        self.assertEqual(first.search_passes, second.search_passes)

    def test_semantic_research_cache_reuses_near_duplicate_queries(self) -> None:
        researcher = InternetResearcher()
        source = ResearchSource(
            id="",
            title="Guidance A",
            url="https://example.gov/a",
            domain="example.gov",
            snippet="",
            excerpt="Official guidance recommends prompt compression and cache reuse.",
            authority="primary",
            credibility_score=0.95,
            recency_score=1.0,
            discovery_pass="official",
        )

        first_query = "How should we optimize model routing and cache evidence?"
        second_query = "What is the best way to optimize model routing and cache evidence?"

        with patch.object(researcher, "_search_hits", new=AsyncMock(return_value=[SearchHit(title="A", url=source.url, snippet="", relevance_score=0.9)])) as search_hits_mock:
            with patch.object(researcher, "_build_candidates", new=AsyncMock(return_value=[(0.9, source)])):
                first = asyncio.run(researcher.research(first_query))
                second = asyncio.run(researcher.research(second_query))

        self.assertEqual(search_hits_mock.call_count, 1)
        self.assertEqual(second.query, second_query)
        self.assertEqual(first.sources, second.sources)

    @staticmethod
    def _build_context(query: str, source_count: int = 3) -> ResearchContext:
        profile = build_workflow_profile(query)
        sources = [
            ResearchSource(
                id="S1",
                title="Primary guidance",
                url="https://example.gov/a",
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
                url="https://example.org/b",
                domain="example.org",
                snippet="",
                excerpt="Independent review notes risks, limitations, and failure modes.",
                authority="high",
                credibility_score=0.78,
                recency_score=0.7,
                discovery_pass="evidence",
            ),
            ResearchSource(
                id="S3",
                title="Operational note",
                url="https://example.net/c",
                domain="example.net",
                snippet="",
                excerpt="Operational notes emphasize cache reuse and prompt compression.",
                authority="secondary",
                credibility_score=0.7,
                recency_score=0.8,
                discovery_pass="recent",
            ),
            ResearchSource(
                id="S4",
                title="Benchmark note",
                url="https://example.com/d",
                domain="example.com",
                snippet="",
                excerpt="Benchmark note documents cost and performance tradeoffs.",
                authority="secondary",
                credibility_score=0.72,
                recency_score=0.9,
                discovery_pass="benchmark",
            ),
            ResearchSource(
                id="S5",
                title="Methods note",
                url="https://example.edu/e",
                domain="example.edu",
                snippet="",
                excerpt="Methods note gives a formal evaluation framework and protocol.",
                authority="primary",
                credibility_score=0.9,
                recency_score=0.85,
                discovery_pass="methodology",
            ),
            ResearchSource(
                id="S6",
                title="Tradeoff review",
                url="https://example.org/f",
                domain="example.org",
                snippet="",
                excerpt="Tradeoff review discusses comparison, limitations, and failure modes.",
                authority="high",
                credibility_score=0.8,
                recency_score=0.88,
                discovery_pass="comparison",
            ),
        ]
        sources = tuple(sources[: max(1, source_count)])
        return ResearchContext(
            query=query,
            workflow_profile=profile,
            search_terms=("routing", "cache", "evidence"),
            search_passes=("official", "evidence", "recent"),
            sources=sources,
            generated_at=0.0,
            contradictions=(("S1", "S2", "Operational guidance differs from review evidence."),),
        )


if __name__ == "__main__":
    unittest.main()
