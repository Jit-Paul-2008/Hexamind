from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from agents import AGENTS
from schemas import PipelineEvent, PipelineEventType
from model_provider import PipelineModelProvider, create_pipeline_model_provider


@dataclass
class PipelineSession:
    id: str
    query: str
    created_at: float


class PipelineService:
    def __init__(
        self,
        storage_path: Path | None = None,
        model_provider: PipelineModelProvider | None = None,
    ) -> None:
        self._storage_path = storage_path or Path(__file__).resolve().with_name(
            ".data"
        ).joinpath("pipeline-sessions.json")
        self._model_provider = model_provider or create_pipeline_model_provider()
        self._sessions: dict[str, PipelineSession] = self._load_sessions()

    def start(self, query: str) -> str:
        session_id = f"session_{uuid.uuid4().hex[:10]}"
        self._sessions[session_id] = PipelineSession(
            id=session_id,
            query=query,
            created_at=time.time(),
        )
        self._save_sessions()
        return session_id

    def has_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            return True

        self._sessions = self._load_sessions()
        return session_id in self._sessions

    def health(self) -> dict[str, str | int | bool]:
        diagnostics = self._model_provider.diagnostics()
        return {
            "status": "ok",
            "sessions": len(self._sessions),
            **diagnostics,
        }

    async def stream_events(self, session_id: str):
        session = self._get_session(session_id)
        assembled: dict[str, str] = {}
        start_delay = max(0, _env_ms("HEXAMIND_STREAM_START_DELAY_MS", 20))
        chunk_delay = max(0, _env_ms("HEXAMIND_STREAM_CHUNK_DELAY_MS", 8))
        step_delay = max(0, _env_ms("HEXAMIND_STREAM_STEP_DELAY_MS", 20))

        for agent in AGENTS:
            start_event = PipelineEvent(
                type=PipelineEventType.AGENT_START,
                agentId=agent.id,
            )
            yield {
                "event": start_event.type.value,
                "data": start_event.model_dump_json(),
            }
            await asyncio.sleep(start_delay / 1000)

            warmup_event = PipelineEvent(
                type=PipelineEventType.AGENT_CHUNK,
                agentId=agent.id,
                chunk="Analyzing request... ",
            )
            yield {
                "event": warmup_event.type.value,
                "data": warmup_event.model_dump_json(),
            }

            content = await self._model_provider.build_agent_text(agent.id, session.query)
            words = content.split(" ")
            full = ""
            for idx, word in enumerate(words):
                chunk = word + (" " if idx < len(words) - 1 else "")
                full += chunk
                chunk_event = PipelineEvent(
                    type=PipelineEventType.AGENT_CHUNK,
                    agentId=agent.id,
                    chunk=chunk,
                )
                yield {
                    "event": chunk_event.type.value,
                    "data": chunk_event.model_dump_json(),
                }
                await asyncio.sleep(chunk_delay / 1000)

            assembled[agent.id] = full
            done_event = PipelineEvent(
                type=PipelineEventType.AGENT_DONE,
                agentId=agent.id,
                fullContent=full,
            )
            yield {
                "event": done_event.type.value,
                "data": done_event.model_dump_json(),
            }
            await asyncio.sleep(step_delay / 1000)

        final_answer = await self._model_provider.compose_final_answer(
            session.query, assembled
        )
        final_event = PipelineEvent(
            type=PipelineEventType.PIPELINE_DONE,
            agentId="output",
            fullContent=final_answer,
        )
        yield {
            "event": final_event.type.value,
            "data": final_event.model_dump_json(),
        }
        await asyncio.sleep(0)

    def _get_session(self, session_id: str) -> PipelineSession:
        if session_id not in self._sessions:
            self._sessions = self._load_sessions()

        return self._sessions[session_id]

    def _load_sessions(self) -> dict[str, PipelineSession]:
        if not self._storage_path.exists():
            return {}

        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        sessions: dict[str, PipelineSession] = {}
        for session_id, item in payload.items():
            try:
                sessions[session_id] = PipelineSession(
                    id=item["id"],
                    query=item["query"],
                    created_at=float(item["created_at"]),
                )
            except (KeyError, TypeError, ValueError):
                continue

        return sessions

    def _save_sessions(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            session_id: {
                "id": session.id,
                "query": session.query,
                "created_at": session.created_at,
            }
            for session_id, session in self._sessions.items()
        }

        temp_path = self._storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self._storage_path)


pipeline_service = PipelineService()


def _env_ms(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
