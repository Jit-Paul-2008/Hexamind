from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from knowledge_cache import LocalKnowledgeCache
from research import ResearchContext, ResearchSource
from workflow import build_workflow_profile


class KnowledgeCacheTests(unittest.TestCase):
    def test_roundtrip_persists_research_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = LocalKnowledgeCache(cache_dir=Path(temp_dir))
            research = self._build_context()

            cache.cache_research(research.query, research)
            restored = cache.get_cached_research(research.query)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.query, research.query)
        self.assertEqual(restored.sources[0].url, research.sources[0].url)
        self.assertEqual(restored.workflow_profile.query_type, research.workflow_profile.query_type)

    @staticmethod
    def _build_context() -> ResearchContext:
        profile = build_workflow_profile("How should we use local cache and embeddings?")
        source = ResearchSource(
            id="S1",
            title="Local cache note",
            url="https://example.gov/cache",
            domain="example.gov",
            snippet="",
            excerpt="Official guidance recommends caching and offline reuse.",
            authority="primary",
            credibility_score=0.95,
            recency_score=1.0,
            discovery_pass="official",
        )
        return ResearchContext(
            query="How should we use local cache and embeddings?",
            workflow_profile=profile,
            search_terms=("cache", "embeddings"),
            search_passes=("official",),
            sources=(source,),
            generated_at=0.0,
            contradictions=(),
            evidence_graph=(("S1", "Caching supports offline reuse.", "high"),),
            corroboration_pairs=(),
            topic_coverage_score=0.8,
            research_depth_score=0.9,
        )


if __name__ == "__main__":
    unittest.main()