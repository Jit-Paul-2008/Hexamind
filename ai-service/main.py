from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from agents import AGENTS
from pipeline import pipeline_service
from sarvam_service import SarvamService
from schemas import (
    Agent,
    SarvamTransformRequest,
    SarvamTransformResponse,
    StartPipelineRequest,
    StartPipelineResponse,
)


app = FastAPI(title="Hexamind AI Service", version="1.0.0")
sarvam_service = SarvamService()
_REQUEST_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_AUDIT_LOG_PATH = Path(__file__).resolve().with_name(".data").joinpath("audit-log.jsonl")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_audit_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    client_ip = request.client.host if request.client else "unknown"
    started_at = time.perf_counter()

    rate_limit = _rate_limit_per_minute()
    if rate_limit > 0 and not _rate_limit_allows(client_ip, rate_limit):
        response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        _append_audit_log(
            request_id=request_id,
            request=request,
            status_code=response.status_code,
            duration_seconds=0.0,
            client_ip=client_ip,
            rate_limited=True,
        )
        return response

    if _auth_token_required() and _is_sensitive_route(request.url.path):
        provided = request.headers.get("Authorization", "")
        token = _auth_token()
        if provided != f"Bearer {token}" and request.headers.get("X-Hexamind-Auth", "") != token:
            response = JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            _append_audit_log(
                request_id=request_id,
                request=request,
                status_code=response.status_code,
                duration_seconds=0.0,
                client_ip=client_ip,
                rate_limited=False,
            )
            return response

    response = await call_next(request)
    _append_audit_log(
        request_id=request_id,
        request=request,
        status_code=response.status_code,
        duration_seconds=round(time.perf_counter() - started_at, 4),
        client_ip=client_ip,
        rate_limited=False,
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health_check() -> dict[str, str | int | bool]:
    payload = pipeline_service.health()
    payload["rateLimitPerMinute"] = _rate_limit_per_minute()
    payload["auditLoggingEnabled"] = True
    payload["authRequired"] = _auth_token_required()
    return payload


@app.get("/api/agents", response_model=list[Agent])
def get_agents() -> list[Agent]:
    return [
        Agent(
            id=a.id,
            codename=a.codename,
            role=a.role,
            purpose=a.purpose,
            accentColor=a.accent_color,
            glowColor=a.glow_color,
            shape=a.shape,
            processingOrder=a.processing_order,
        )
        for a in AGENTS
    ]


@app.post("/api/pipeline/start", response_model=StartPipelineResponse)
def start_pipeline(payload: StartPipelineRequest) -> StartPipelineResponse:
    session_id = pipeline_service.start(payload.query.strip())
    return StartPipelineResponse(sessionId=session_id)


@app.get("/api/pipeline/{session_id}/stream")
def stream_pipeline(session_id: str):
    if not pipeline_service.has_session(session_id):
        raise HTTPException(status_code=404, detail="Unknown pipeline session")
    return EventSourceResponse(pipeline_service.stream_events(session_id))


@app.get("/api/pipeline/{session_id}/quality")
def pipeline_quality(session_id: str) -> dict[str, object]:
    try:
        return pipeline_service.get_quality_report(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown pipeline session")


@app.post("/api/pipeline/{session_id}/sarvam-transform", response_model=SarvamTransformResponse)
async def pipeline_sarvam_transform(
    session_id: str,
    payload: SarvamTransformRequest,
) -> SarvamTransformResponse:
    try:
        report_text = pipeline_service.get_final_report(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown pipeline session")
    if not report_text.strip():
        raise HTTPException(status_code=400, detail="No completed report found for this session")

    result = await sarvam_service.transform_report(
        text=report_text,
        target_language_code=payload.targetLanguageCode,
        instruction=payload.instruction,
    )
    return SarvamTransformResponse(
        sessionId=session_id,
        text=result.text,
        languageCode=result.language_code,
        instructionApplied=result.instruction_applied,
        provider=result.provider,
        fallback=result.fallback,
        notes=list(result.notes),
    )


@app.post("/api/pipeline/{session_id}/export-docx")
async def pipeline_export_docx(
    session_id: str,
    payload: SarvamTransformRequest,
) -> Response:
    try:
        report_text = pipeline_service.get_final_report(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown pipeline session")
    if not report_text.strip():
        raise HTTPException(status_code=400, detail="No completed report found for this session")

    docx_bytes, result = await sarvam_service.build_docx(
        title=f"Hexamind Research Report - {session_id}",
        text=report_text,
        target_language_code=payload.targetLanguageCode,
        instruction=payload.instruction,
    )
    filename = f"hexamind-{session_id}-{result.language_code}.docx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Hexamind-Transform-Provider": result.provider,
        "X-Hexamind-Transform-Fallback": str(result.fallback).lower(),
    }
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


def _rate_limit_per_minute() -> int:
    value = _env_int("HEXAMIND_RATE_LIMIT_PER_MINUTE", 0)
    return max(0, value)


def _rate_limit_allows(client_ip: str, limit_per_minute: int) -> bool:
    now = time.time()
    bucket = _REQUEST_BUCKETS[client_ip]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit_per_minute:
        return False
    bucket.append(now)
    return True


def _auth_token_required() -> bool:
    return bool(_auth_token())


def _auth_token() -> str:
    return os.getenv("HEXAMIND_AUTH_TOKEN", "").strip()


def _is_sensitive_route(path: str) -> bool:
    return path.startswith("/api/pipeline/") and (
        path.endswith("/sarvam-transform") or path.endswith("/export-docx") or path.endswith("/regenerate") or path.endswith("/start")
    )


def _append_audit_log(
    *,
    request_id: str,
    request: Request,
    status_code: int,
    duration_seconds: float,
    client_ip: str,
    rate_limited: bool,
) -> None:
    try:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "requestId": request_id,
            "method": request.method,
            "path": request.url.path,
            "statusCode": status_code,
            "durationSeconds": duration_seconds,
            "clientIp": client_ip,
            "rateLimited": rate_limited,
            "timestamp": time.time(),
        }
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
