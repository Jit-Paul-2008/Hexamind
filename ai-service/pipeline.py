from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass

from agents import AGENTS
from schemas import PipelineEvent, PipelineEventType


@dataclass
class PipelineSession:
    id: str
    query: str
    created_at: float


class PipelineService:
    def __init__(self) -> None:
        self._sessions: dict[str, PipelineSession] = {}

    def start(self, query: str) -> str:
        session_id = f"session_{uuid.uuid4().hex[:10]}"
        self._sessions[session_id] = PipelineSession(
            id=session_id,
            query=query,
            created_at=time.time(),
        )
        return session_id

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    async def stream_events(self, session_id: str):
        session = self._sessions[session_id]
        assembled: dict[str, str] = {}

        for agent in AGENTS:
            start_event = PipelineEvent(
                type=PipelineEventType.AGENT_START,
                agentId=agent.id,
            )
            yield {
                "event": start_event.type.value,
                "data": start_event.model_dump_json(),
            }
            await asyncio.sleep(0.12)

            content = self._build_agent_text(agent.id, session.query)
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
                await asyncio.sleep(0.025)

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
            await asyncio.sleep(0.18)

        final_answer = self._compose_final_answer(session.query, assembled)
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

    def _build_agent_text(self, agent_id: str, query: str) -> str:
        q = query.strip()
        if agent_id == "advocate":
            return (
                f"Strongest case for '{q}': measurable upside exists if scope is narrow, "
                "constraints are explicit, and early metrics are tracked from day one."
            )
        if agent_id == "skeptic":
            return (
                f"Primary risks for '{q}': noisy assumptions, hidden dependency costs, "
                "and unclear ownership can break delivery quality and reliability."
            )
        if agent_id == "synthesiser":
            return (
                f"Balanced synthesis for '{q}': proceed in phased slices with guardrails, "
                "validate each increment, and stop expansion if confidence regresses."
            )
        return (
            f"Forecast for '{q}': likely positive outcome under controlled rollout, "
            "with biggest gains from fast feedback loops and strict review checkpoints."
        )

    def _compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        advocate = outputs.get("advocate", "")
        skeptic = outputs.get("skeptic", "")
        synthesis = outputs.get("synthesiser", "")
        oracle = outputs.get("oracle", "")
        return (
            f"Final synthesis for '{query}': {synthesis} "
            f"Support: {advocate} "
            f"Risks: {skeptic} "
            f"Outlook: {oracle}"
        )


pipeline_service = PipelineService()
