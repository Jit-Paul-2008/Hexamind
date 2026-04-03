from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from model_provider import _ProviderHealthManager, _invoke_with_resilience
from pipeline import PipelineService
from research import ResearchContext


class _SlowPipelineProvider:
    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": "slow",
            "activeProvider": "slow",
            "modelName": "slow",
            "isFallback": False,
            "fallbackCount": 0,
            "lastError": "",
        }

    async def build_research_context(self, query: str) -> ResearchContext | None:
        await asyncio.sleep(0.05)
        return None

    async def build_agent_text(self, agent_id: str, query: str, research: ResearchContext | None = None) -> str:
        await asyncio.sleep(0.05)
        return (
            "## Slow Path\n"
            "- This path should not be used when the pipeline stage timeout is working.\n"
        )

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
    ) -> str:
        await asyncio.sleep(0.05)
        return "## Slow Final\n- This path should not be used when the pipeline stage timeout is working."


class ReliabilityMilestoneTests(unittest.TestCase):
    def test_provider_circuit_breaker_opens_after_retry_budget(self) -> None:
        health = _ProviderHealthManager(
            provider_name="test",
            retry_budget=1,
            failure_threshold=2,
            cooldown_seconds=60.0,
            backoff_seconds=0.0,
        )
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            asyncio.run(_invoke_with_resilience(health, "final", operation, timeout_seconds=0.01))

        self.assertEqual(attempts, 2)
        self.assertTrue(health.is_open())
        self.assertEqual(health.snapshot()["circuitState"], "open")
        self.assertEqual(health.snapshot()["failureCount"], 2)

    def test_pipeline_falls_back_when_stage_timeouts_fire(self) -> None:
        service = PipelineService(model_provider=_SlowPipelineProvider())
        service._retrieval_timeout_seconds = 0.001
        service._agent_timeout_seconds = 0.001
        service._final_timeout_seconds = 0.001
        service._queue_wait_timeout_seconds = 0.1

        with patch.dict(
            os.environ,
            {
                "HEXAMIND_STREAM_START_DELAY_MS": "0",
                "HEXAMIND_STREAM_CHUNK_DELAY_MS": "0",
                "HEXAMIND_STREAM_STEP_DELAY_MS": "0",
                "HEXAMIND_NEVER_FAIL_REPORT": "1",
                "HEXAMIND_AUTO_REGENERATE_ON_FAIL": "1",
            },
            clear=False,
        ):
            session_id = service.start("How should we ship the MVP?")

            frames = asyncio.run(self._collect_frames(service.stream_events(session_id)))

        self.assertGreater(len(frames), 0)
        self.assertEqual(frames[-1]["event"], "pipeline_done")

        report_text = service.get_final_report(session_id)
        self.assertIn("## Abstract", report_text)
        self.assertIn("## 1. Introduction", report_text)

        health = service.health()
        self.assertIn("maxConcurrentStreams", health)
        self.assertIn("retrievalTimeoutSeconds", health)
        self.assertIn("agentTimeoutSeconds", health)
        self.assertIn("finalTimeoutSeconds", health)

    @staticmethod
    async def _collect_frames(stream: object) -> list[dict[str, str]]:
        frames: list[dict[str, str]] = []
        async for frame in stream:
            frames.append(frame)
        return frames


if __name__ == "__main__":
    unittest.main()
