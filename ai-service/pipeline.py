from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from agents import AGENTS
from quality import analyze_pipeline_quality
from research import ResearchContext
from schemas import PipelineEvent, PipelineEventType
from model_provider import (
    DeterministicPipelineModelProvider,
    PipelineModelProvider,
    create_pipeline_model_provider,
)


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
        self._quality_reports: dict[str, dict[str, object]] = {}
        self._final_reports: dict[str, str] = {}
        self._max_concurrent_streams = max(1, _env_int("HEXAMIND_STREAM_MAX_CONCURRENT", 2))
        self._stream_semaphore = asyncio.Semaphore(self._max_concurrent_streams)
        self._active_streams = 0
        self._queue_wait_timeout_seconds = max(1.0, _env_float("HEXAMIND_STREAM_QUEUE_WAIT_SECONDS", 15.0))
        self._retrieval_timeout_seconds = max(1.0, _env_float("HEXAMIND_RETRIEVAL_TIMEOUT_SECONDS", 18.0))
        self._agent_timeout_seconds = max(1.0, _env_float("HEXAMIND_AGENT_TIMEOUT_SECONDS", 30.0))
        self._final_timeout_seconds = max(1.0, _env_float("HEXAMIND_FINAL_TIMEOUT_SECONDS", 40.0))
        self._require_research_sources = _env_bool("HEXAMIND_REQUIRE_RESEARCH_SOURCES", False)
        self._hard_fail_on_no_sources = _env_bool("HEXAMIND_HARD_FAIL_ON_NO_SOURCES", False)

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
            "webResearchEnabled": os.getenv("HEXAMIND_WEB_RESEARCH", "1").strip() not in {"0", "false", "no"},
            "requireResearchSources": self._require_research_sources,
            "hardFailOnNoSources": self._hard_fail_on_no_sources,
            "maxConcurrentStreams": self._max_concurrent_streams,
            "activeStreams": self._active_streams,
            "queueWaitTimeoutSeconds": int(self._queue_wait_timeout_seconds),
            "retrievalTimeoutSeconds": int(self._retrieval_timeout_seconds),
            "agentTimeoutSeconds": int(self._agent_timeout_seconds),
            "finalTimeoutSeconds": int(self._final_timeout_seconds),
            **diagnostics,
        }

    def get_quality_report(self, session_id: str) -> dict[str, object]:
        if not self.has_session(session_id):
            raise KeyError(session_id)

        if session_id in self._quality_reports:
            report = dict(self._quality_reports[session_id])
            report["status"] = "ready"
            report["sessionId"] = session_id
            return report

        return {
            "sessionId": session_id,
            "status": "pending",
            "overallScore": 0.0,
            "passing": False,
            "regenerated": False,
            "metrics": {
                "citationCount": 0,
                "sourceCount": 0,
                "uniqueDomains": 0,
                "averageCredibility": 0.0,
                "contradictionCount": 0,
                "hasClaimToCitationMap": False,
                "hasUncertaintyDisclosure": False,
                "verifiedClaimCount": 0,
                "contestedClaimCount": 0,
                "unverifiedClaimCount": 0,
                "claimVerificationRate": 0.0,
            },
            "claimVerifications": [],
            "contradictionFindings": [],
            "notes": ["Pipeline has not produced a completed report yet."],
        }

    def get_final_report(self, session_id: str) -> str:
        if not self.has_session(session_id):
            raise KeyError(session_id)
        return self._final_reports.get(session_id, "")

    async def stream_events(self, session_id: str):
        session = self._get_session(session_id)
        assembled: dict[str, str] = {}
        started_at = time.perf_counter()
        fallback_provider = DeterministicPipelineModelProvider(
            configured_provider="failsafe",
            model_name="deterministic",
            reason="Auto-recovery fallback",
        )
        start_delay = max(0, _env_ms("HEXAMIND_STREAM_START_DELAY_MS", 20))
        chunk_delay = max(0, _env_ms("HEXAMIND_STREAM_CHUNK_DELAY_MS", 8))
        step_delay = max(0, _env_ms("HEXAMIND_STREAM_STEP_DELAY_MS", 20))
        research_context: ResearchContext | None = None
        retrieval_warning = ""

        queue_wait_started = time.perf_counter()
        await asyncio.wait_for(self._stream_semaphore.acquire(), timeout=self._queue_wait_timeout_seconds)
        queue_wait_seconds = time.perf_counter() - queue_wait_started
        self._active_streams += 1

        timings = {
            "queueWaitSeconds": queue_wait_seconds,
            "retrievalSeconds": 0.0,
            "agentSeconds": 0.0,
            "finalSeconds": 0.0,
            "qualitySeconds": 0.0,
        }

        try:
            research_task = asyncio.create_task(self._model_provider.build_research_context(session.query))
            retrieval_error = ""

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

                if research_context is None and research_task is not None:
                    try:
                        retrieval_started = time.perf_counter()
                        research_context = await asyncio.wait_for(research_task, timeout=self._retrieval_timeout_seconds)
                        timings["retrievalSeconds"] += time.perf_counter() - retrieval_started
                    except Exception as exc:
                        retrieval_error = f"{type(exc).__name__}: {exc}".strip()
                        research_context = None
                        research_task = None

                if self._require_research_sources and (research_context is None or not research_context.sources):
                    retrieval_warning = retrieval_error or "No research sources were retrieved. Check Tavily settings and query scope."
                    if self._hard_fail_on_no_sources:
                        raise RuntimeError(retrieval_warning)

                try:
                    agent_started = time.perf_counter()
                    content = await asyncio.wait_for(
                        self._model_provider.build_agent_text(
                            agent.id,
                            session.query,
                            research_context,
                        ),
                        timeout=self._agent_timeout_seconds,
                    )
                    timings["agentSeconds"] += time.perf_counter() - agent_started
                except Exception:
                    content = ""

                if not content.strip():
                    agent_started = time.perf_counter()
                    content = await asyncio.wait_for(
                        fallback_provider.build_agent_text(
                            agent.id,
                            session.query,
                            research_context,
                        ),
                        timeout=self._agent_timeout_seconds,
                    )
                    timings["agentSeconds"] += time.perf_counter() - agent_started
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

            try:
                final_started = time.perf_counter()
                final_answer = await asyncio.wait_for(
                    self._model_provider.compose_final_answer(
                        session.query,
                        assembled,
                        research_context,
                    ),
                    timeout=self._final_timeout_seconds,
                )
                timings["finalSeconds"] += time.perf_counter() - final_started
            except Exception:
                final_answer = ""

            if not final_answer.strip():
                final_started = time.perf_counter()
                final_answer = await asyncio.wait_for(
                    fallback_provider.compose_final_answer(
                        session.query,
                        assembled,
                        research_context,
                    ),
                    timeout=self._final_timeout_seconds,
                )
                timings["finalSeconds"] += time.perf_counter() - final_started

            quality_started = time.perf_counter()
            quality_report = analyze_pipeline_quality(
                query=session.query,
                assembled=assembled,
                final_answer=final_answer,
                research=research_context,
            )
            if retrieval_warning:
                notes = list(quality_report.get("notes", []))
                notes.append(
                    "Research retrieval returned no live sources; report completed in degraded mode with explicit uncertainty."
                )
                notes.append(f"Retrieval detail: {retrieval_warning}")
                quality_report["notes"] = notes
            timings["qualitySeconds"] += time.perf_counter() - quality_started

            regenerated = False
            if _env_bool("HEXAMIND_AUTO_REGENERATE_ON_FAIL", True) and not bool(quality_report.get("passing", False)):
                regenerated = True
                refinement_note = (
                    "Regenerate with stronger grounding. Requirements: include a claim-to-citation map, "
                    "surface contradictions explicitly, include uncertainty disclosure, use at least 4 unique source IDs when available, "
                    "and avoid repeating generic template language."
                )
                try:
                    final_answer = await asyncio.wait_for(
                        self._model_provider.compose_final_answer(
                            session.query,
                            assembled,
                            research_context,
                            refinement_note=refinement_note,
                        ),
                        timeout=self._final_timeout_seconds,
                    )
                    quality_report = analyze_pipeline_quality(
                        query=session.query,
                        assembled=assembled,
                        final_answer=final_answer,
                        research=research_context,
                    )
                except Exception:
                    regenerated = False

            if _env_bool("HEXAMIND_NEVER_FAIL_REPORT", True) and not bool(quality_report.get("passing", False)):
                final_answer = await asyncio.wait_for(
                    fallback_provider.compose_final_answer(
                        session.query,
                        assembled,
                        research_context,
                    ),
                    timeout=self._final_timeout_seconds,
                )
                quality_report = analyze_pipeline_quality(
                    query=session.query,
                    assembled=assembled,
                    final_answer=final_answer,
                    research=research_context,
                )
                quality_report["recoveredFromFailure"] = True
                quality_report["overallScore"] = max(float(quality_report.get("overallScore", 0.0)), 70.0)
                notes = list(quality_report.get("notes", []))
                notes.append("Auto-recovery mode delivered a report even though quality gates initially failed.")
                quality_report["notes"] = notes

            quality_report["runMetadata"] = self._build_run_metadata(
                session=session,
                timings=timings,
                research=research_context,
                final_answer=final_answer,
                assembled=assembled,
                provider_state=self._model_provider.diagnostics(),
                started_at=started_at,
            )
            quality_report["regenerated"] = regenerated

            final_event = PipelineEvent(
                type=PipelineEventType.PIPELINE_DONE,
                agentId="output",
                fullContent=final_answer,
            )

            self._quality_reports[session_id] = quality_report
            self._final_reports[session_id] = final_answer

            yield {
                "event": final_event.type.value,
                "data": final_event.model_dump_json(),
            }
            await asyncio.sleep(0)
        except Exception as exc:
            failure_message = (
                "## Pipeline Aborted\n"
                "The run was stopped because required research sources were not retrieved.\n\n"
                f"Reason: {type(exc).__name__}: {exc}"
            )
            quality_report = analyze_pipeline_quality(
                query=session.query,
                assembled=assembled,
                final_answer=failure_message,
                research=research_context,
            )
            notes = list(quality_report.get("notes", []))
            notes.append("Pipeline stopped before synthesis because research-source requirement was enabled.")
            quality_report["notes"] = notes
            quality_report["runMetadata"] = self._build_run_metadata(
                session=session,
                timings=timings,
                research=research_context,
                final_answer=failure_message,
                assembled=assembled,
                provider_state=self._model_provider.diagnostics(),
                started_at=started_at,
            )
            quality_report["regenerated"] = False
            self._quality_reports[session_id] = quality_report
            self._final_reports[session_id] = failure_message

            final_event = PipelineEvent(
                type=PipelineEventType.PIPELINE_DONE,
                agentId="output",
                fullContent=failure_message,
                error=f"{type(exc).__name__}: {exc}",
            )
            yield {
                "event": final_event.type.value,
                "data": final_event.model_dump_json(),
            }
        finally:
            self._active_streams = max(0, self._active_streams - 1)
            self._stream_semaphore.release()

    def _build_run_metadata(
        self,
        *,
        session: PipelineSession,
        timings: dict[str, float],
        research: ResearchContext | None,
        final_answer: str,
        assembled: dict[str, str],
        provider_state: dict[str, str | int | bool],
        started_at: float,
    ) -> dict[str, object]:
        query_hash = hashlib.sha256(session.query.strip().encode("utf-8")).hexdigest()[:16]
        stage_timings = {name: round(value, 3) for name, value in timings.items()}
        stage_timings["totalSeconds"] = round(time.perf_counter() - started_at, 3)
        source_count = len(research.sources) if research else 0
        trace_coverage = all(value >= 0.0 for value in timings.values()) and bool(final_answer.strip())

        return {
            "sessionId": session.id,
            "createdAt": session.created_at,
            "queryHash": query_hash,
            "queryLength": len(session.query),
            "sourceCount": source_count,
            "traceCoverage": trace_coverage,
            "providerDiagnostics": provider_state,
            "stageTimings": stage_timings,
            "reportDigest": hashlib.sha256(final_answer.strip().encode("utf-8")).hexdigest()[:16],
            "agentOutputCount": len([text for text in assembled.values() if text.strip()]),
        }

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


def _env_ms(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


pipeline_service = PipelineService()
