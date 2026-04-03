from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import os

os.environ["HEXAMIND_WEB_RESEARCH"] = "0"

from fastapi.testclient import TestClient

from agents import AGENTS
from main import app
import pipeline
from pipeline import pipeline_service


class PipelineApiTests(unittest.TestCase):
    def setUp(self) -> None:
        pipeline_service._sessions.clear()
        self.client = TestClient(app)

    def test_health_and_agents(self) -> None:
        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        health_payload = health_response.json()
        self.assertEqual(health_payload["status"], "ok")
        self.assertIn("activeProvider", health_payload)
        self.assertIn("isFallback", health_payload)

        agents_response = self.client.get("/api/agents")
        self.assertEqual(agents_response.status_code, 200)
        agents = agents_response.json()
        self.assertEqual(len(agents), len(AGENTS))
        self.assertEqual([agent["id"] for agent in agents], [agent.id for agent in AGENTS])

    def test_pipeline_stream_emits_expected_sequence(self) -> None:
        with patch.object(pipeline.asyncio, "sleep", new=AsyncMock(return_value=None)):
            start_response = self.client.post(
                "/api/pipeline/start",
                json={"query": "How should we ship the MVP?"},
            )

            self.assertEqual(start_response.status_code, 200)
            session_id = start_response.json()["sessionId"]

            with self.client.stream("GET", f"/api/pipeline/{session_id}/stream") as response:
                self.assertEqual(response.status_code, 200)
                frames = self._collect_sse_frames(response.iter_lines())

        event_types = [frame["event"] for frame in frames]
        self.assertEqual(event_types[0], "agent_start")
        self.assertEqual(event_types[-1], "pipeline_done")
        self.assertEqual(event_types.count("agent_start"), len(AGENTS))
        self.assertEqual(event_types.count("agent_done"), len(AGENTS))

        start_events = [json.loads(frame["data"]) for frame in frames if frame["event"] == "agent_start"]
        done_events = [json.loads(frame["data"]) for frame in frames if frame["event"] == "agent_done"]
        final_event = json.loads(frames[-1]["data"])

        self.assertEqual([event["agentId"] for event in start_events], [agent.id for agent in AGENTS])
        self.assertEqual([event["agentId"] for event in done_events], [agent.id for agent in AGENTS])
        self.assertEqual(final_event["agentId"], "output")
        self.assertIn("## Abstract", final_event["fullContent"])

        quality_response = self.client.get(f"/api/pipeline/{session_id}/quality")
        self.assertEqual(quality_response.status_code, 200)
        quality_payload = quality_response.json()
        self.assertEqual(quality_payload["sessionId"], session_id)
        self.assertEqual(quality_payload["status"], "ready")
        self.assertIn("overallScore", quality_payload)
        self.assertIn("metrics", quality_payload)
        self.assertIn("contradictionFindings", quality_payload)
        self.assertIn("notes", quality_payload)

    def test_unknown_session_returns_404(self) -> None:
        response = self.client.get("/api/pipeline/does-not-exist/stream")
        self.assertEqual(response.status_code, 404)

        quality_response = self.client.get("/api/pipeline/does-not-exist/quality")
        self.assertEqual(quality_response.status_code, 404)

    def test_sarvam_transform_and_export_endpoints(self) -> None:
        with patch.object(pipeline.asyncio, "sleep", new=AsyncMock(return_value=None)):
            start_response = self.client.post(
                "/api/pipeline/start",
                json={"query": "Compare laptop-first versus cloud-first development workflows."},
            )
            self.assertEqual(start_response.status_code, 200)
            session_id = start_response.json()["sessionId"]

            with self.client.stream("GET", f"/api/pipeline/{session_id}/stream") as response:
                self.assertEqual(response.status_code, 200)
                _ = self._collect_sse_frames(response.iter_lines())

        transform_response = self.client.post(
            f"/api/pipeline/{session_id}/sarvam-transform",
            json={"targetLanguageCode": "hi-IN", "instruction": "make it concise"},
        )
        self.assertEqual(transform_response.status_code, 200)
        transform_payload = transform_response.json()
        self.assertEqual(transform_payload["sessionId"], session_id)
        self.assertIn("text", transform_payload)
        self.assertIn("languageCode", transform_payload)

        export_response = self.client.post(
            f"/api/pipeline/{session_id}/export-docx",
            json={"targetLanguageCode": "hi-IN", "instruction": "keep bullets"},
        )
        self.assertEqual(export_response.status_code, 200)
        # Content type depends on whether python-docx is installed (fallback is text/plain)
        content_type = export_response.headers.get("content-type")
        self.assertIn(
            content_type,
            [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain; charset=utf-8",
            ],
        )
        self.assertIn("attachment; filename=", export_response.headers.get("content-disposition", ""))
        self.assertGreater(len(export_response.content), 100)

    @staticmethod
    def _collect_sse_frames(lines: object) -> list[dict[str, str]]:
        frames: list[dict[str, str]] = []
        current: dict[str, str] = {}

        for raw_line in lines:
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
            if line == "":
                if current:
                    frames.append(current)
                    current = {}
                continue

            key, value = line.split(": ", 1)
            current[key] = value

        if current:
            frames.append(current)

        return frames


if __name__ == "__main__":
    unittest.main()
