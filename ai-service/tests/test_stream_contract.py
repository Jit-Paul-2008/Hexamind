from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import pipeline
from schemas import PipelineEvent, PipelineEventType


class _FakeAuroraGraph:
    def __init__(self, query: str, aga_mode: bool = False, math_mode: bool = False, task_tree=None):
        self.query = query
        self.aga_mode = aga_mode
        self.math_mode = math_mode
        self.task_tree = task_tree or []
        self.context = {"sources": ["local://source"]}

    async def run(self):
        yield {
            "data": PipelineEvent(
                type=PipelineEventType.AGENT_START,
                agentId="orchestrator",
                fullContent="",
            ).model_dump_json()
        }
        yield {
            "data": PipelineEvent(
                type=PipelineEventType.PIPELINE_DONE,
                agentId="output",
                fullContent="## Report\n\nContract OK",
            ).model_dump_json()
        }


class StreamContractTests(unittest.TestCase):
    def test_stream_events_accepts_typed_message_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage_path = Path(tmp) / "pipeline-sessions.json"
            service = pipeline.PipelineService(storage_path=storage_path)
            session_id = service.start("Validate stream contract")

            original_graph = pipeline.AuroraGraph
            pipeline.AuroraGraph = _FakeAuroraGraph
            try:
                emitted: list[dict[str, str]] = []

                async def _collect() -> None:
                    async for event in service.stream_events(session_id):
                        emitted.append(event)

                asyncio.run(_collect())
            finally:
                pipeline.AuroraGraph = original_graph

            self.assertEqual(len(emitted), 2)
            self.assertEqual(service.get_final_report(session_id), "## Report\n\nContract OK")

            quality = service.get_quality_report(session_id)
            self.assertEqual(quality.get("status"), "ready")


if __name__ == "__main__":
    unittest.main()
