from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import httpx

from model_provider import LocalPipelineModelProvider
from research import InternetResearcher, search_duckduckgo, search_wikipedia


class FreeApiIntegrationTests(unittest.TestCase):
    def test_duckduckgo_helper_returns_sources(self) -> None:
        async def _run() -> int:
            sources = await search_duckduckgo("machine learning", max_results=3, timeout_seconds=8.0)
            return len(sources)

        try:
            count = asyncio.run(_run())
        except httpx.HTTPError as exc:
            self.skipTest(f"Network unavailable for DuckDuckGo test: {exc}")
            return

        self.assertGreaterEqual(count, 1)

    def test_wikipedia_helper_returns_sources(self) -> None:
        async def _run() -> int:
            sources = await search_wikipedia("artificial intelligence", max_results=3, timeout_seconds=8.0)
            return len(sources)

        try:
            count = asyncio.run(_run())
        except httpx.HTTPError as exc:
            self.skipTest(f"Network unavailable for Wikipedia test: {exc}")
            return

        self.assertGreaterEqual(count, 1)

    def test_research_pipeline_can_emit_free_source_signal(self) -> None:
        async def _run() -> bool:
            researcher = InternetResearcher()
            context = await researcher.research('topic: "AI safety" overview definition')
            return any(
                (src.discovery_pass.startswith("web_search")
                 or src.discovery_pass.startswith("wiki_search")
                 or "wikipedia" in src.domain
                 or "duckduckgo" in src.domain)
                for src in context.sources
            )

        try:
            has_signal = asyncio.run(_run())
        except httpx.HTTPError as exc:
            self.skipTest(f"Network unavailable for research signal test: {exc}")
            return

        self.assertTrue(has_signal)

    def test_local_provider_exposes_hf_fallback_diagnostics(self) -> None:
        provider = LocalPipelineModelProvider("llama3.1:8b")
        diagnostics = provider.diagnostics()

        self.assertIn("hfFallbackEnabled", diagnostics)
        self.assertIn("hfFallbackAvailable", diagnostics)
        self.assertIn("openrouterFallbackEnabled", diagnostics)
        self.assertIn("openrouterFallbackAvailable", diagnostics)
        self.assertIn("activeProvider", diagnostics)


if __name__ == "__main__":
    unittest.main()
