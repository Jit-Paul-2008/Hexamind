from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

import httpx
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sse_starlette.sse import EventSourceResponse


# Repo root is one level above ai-service/ (Docker WORKDIR is ai-service; .env lives at project root).
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / ".env.local")
load_dotenv()

from agents import AGENTS
from api.routes import auth_router, cases_router, projects_router, runs_router, workspaces_router
from database.connection import init_db
from governance import resolve_tenant_resolution
from pipeline import pipeline_service
from sarvam_service import SarvamService, docx_supported
from competitive_research import load_latest_competitive_batch_report
from advanced_features import router as advanced_router
from schemas import (
    Agent,
    SarvamTransformRequest,
    SarvamTransformResponse,
    StartPipelineRequest,
    StartPipelineResponse,
)


def _cors_allowed_origins() -> list[str]:
    """Resolve allowed CORS origins from env for public deployments.

    HEXAMIND_CORS_ORIGINS supports comma-separated values.
    """
    raw = os.getenv("HEXAMIND_CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]

    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for Aurora backend services."""
    if _db_persistence_enabled():
        await init_db()
    yield

app = FastAPI(title="Hexamind AI Service", version="1.0.0", lifespan=lifespan)

sarvam_service = SarvamService()
_REQUEST_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_AUDIT_LOG_PATH = Path(__file__).resolve().with_name(".data").joinpath("audit-log.jsonl")
_REQUEST_TOTAL = Counter(
    "hexamind_http_requests_total",
    "Total HTTP requests handled by Hexamind service",
    ["method", "path", "status"],
)
_REQUEST_DURATION_SECONDS = Histogram(
    "hexamind_http_request_duration_seconds",
    "HTTP request latency for Hexamind service",
    ["method", "path"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)








app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(cases_router)
app.include_router(runs_router)
app.include_router(auth_router)
app.include_router(advanced_router)


@app.middleware("http")
async def security_and_audit_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    client_ip = request.client.host if request.client else "unknown"
    tenant_resolution = resolve_tenant_resolution(request.headers)
    request.state.tenant_id = tenant_resolution.tenant_id
    started_at = time.perf_counter()

    rate_limit = _rate_limit_per_minute()
    if rate_limit > 0 and not _rate_limit_allows(f"{tenant_resolution.tenant_id}:{client_ip}", rate_limit):
        response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        _append_audit_log(
            request_id=request_id,
            request=request,
            status_code=response.status_code,
            duration_seconds=0.0,
            client_ip=client_ip,
            tenant_id=tenant_resolution.tenant_id,
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
                tenant_id=tenant_resolution.tenant_id,
                rate_limited=False,
            )
            return response

    response = await call_next(request)
    elapsed = round(time.perf_counter() - started_at, 4)
    _append_audit_log(
        request_id=request_id,
        request=request,
        status_code=response.status_code,
        duration_seconds=elapsed,
        client_ip=client_ip,
        tenant_id=tenant_resolution.tenant_id,
        rate_limited=False,
    )
    _REQUEST_TOTAL.labels(request.method, request.url.path, str(response.status_code)).inc()
    _REQUEST_DURATION_SECONDS.labels(request.method, request.url.path).observe(elapsed)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health_check() -> dict[str, object]:
    payload = pipeline_service.health()
    payload["rateLimitPerMinute"] = _rate_limit_per_minute()
    payload["auditLoggingEnabled"] = True
    payload["authRequired"] = _auth_token_required()
    return payload


@app.get("/health/liveness")
def health_liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/readiness")
def health_readiness() -> dict[str, str | bool]:
    return {
        "status": "ready",
        "databasePersistenceEnabled": _db_persistence_enabled(),
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/models/status")
async def model_status() -> dict[str, object]:
    payload = pipeline_service.health()
    payload["cloudOnlyMode"] = True
    payload["providerDiagnostics"] = payload.copy()
    return payload


@app.get("/api/benchmark/competitive")
def competitive_benchmark_report() -> dict[str, object]:
    return load_latest_competitive_batch_report()


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
def start_pipeline(payload: StartPipelineRequest, request: Request) -> StartPipelineResponse:
    tenant_id = getattr(request.state, "tenant_id", "default")
    session_id = pipeline_service.start(
        payload.query.strip(),
        tenant_id=tenant_id,
        report_length=payload.reportLength,
        aga_mode=payload.agaMode,
        math_mode=payload.mathMode,
    )
    return StartPipelineResponse(sessionId=session_id)


@app.get("/api/pipeline/{session_id}/stream")
def stream_pipeline(session_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not pipeline_service.has_session(session_id, tenant_id):
        raise HTTPException(status_code=404, detail="Unknown pipeline session")
    return EventSourceResponse(
        pipeline_service.stream_events(session_id, tenant_id),
        ping=10,
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.get("/api/pipeline/{session_id}/quality")
def pipeline_quality(session_id: str, request: Request) -> dict[str, object]:
    try:
        return pipeline_service.get_quality_report(session_id, getattr(request.state, "tenant_id", None))
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown pipeline session")


@app.post("/api/pipeline/{session_id}/sarvam-transform", response_model=SarvamTransformResponse)
async def pipeline_sarvam_transform(
    session_id: str,
    payload: SarvamTransformRequest,
    request: Request,
) -> SarvamTransformResponse:
    try:
        report_text = pipeline_service.get_final_report(session_id, getattr(request.state, "tenant_id", None))
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
    request: Request,
) -> Response:
    try:
        report_text = pipeline_service.get_final_report(session_id, getattr(request.state, "tenant_id", None))
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
    has_real_docx = docx_supported()
    extension = "docx" if has_real_docx else "txt"
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if has_real_docx
        else "text/plain; charset=utf-8"
    )
    filename = f"hexamind-{session_id}-{result.language_code}.{extension}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Hexamind-Transform-Provider": result.provider,
        "X-Hexamind-Transform-Fallback": str(result.fallback).lower(),
        "X-Hexamind-Export-Format": extension,
    }
    return Response(
        content=docx_bytes,
        media_type=media_type,
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


def _db_persistence_enabled() -> bool:
    raw = os.getenv("HEXAMIND_ENABLE_DATABASE_PERSISTENCE", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _append_audit_log(
    *,
    request_id: str,
    request: Request,
    status_code: int,
    duration_seconds: float,
    client_ip: str,
    tenant_id: str,
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
            "tenantId": tenant_id,
            "rateLimited": rate_limited,
            "timestamp": time.time(),
        }
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def _local_base_url() -> str:
    provider = getattr(pipeline_service, "_model_provider", None)
    base_url = getattr(provider, "_base_url", os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://127.0.0.1:11434/api/chat"))
    return str(base_url).rstrip("/")


def _required_local_models() -> list[str]:
    required = [
        os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", "deepseek-r1:14b").strip() or "deepseek-r1:14b",
        os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", "deepseek-r1:14b").strip() or "deepseek-r1:14b",
        os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "deepseek-r1:14b").strip() or "deepseek-r1:14b",
    ]
    deduped: list[str] = []
    for model in required:
        if model not in deduped:
            deduped.append(model)
    return deduped


async def _local_model_status() -> dict[str, object]:
    base_url = _local_base_url()
    required = _required_local_models()
    # Check Ollama tags via native API (usually at /api/tags regardless of chat endpoint)
    root_url = base_url.removesuffix("/api/chat")
    endpoints = [
        f"{root_url}/api/tags",
        f"{root_url}/api/show", # Alternative check
    ]
    last_error = ""

    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in endpoints:
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                payload = response.json()
                installed = _extract_local_models(payload)
                missing = [model for model in required if model not in installed]
                return {
                    "baseUrl": base_url,
                    "installed": installed,
                    "installedCount": len(installed),
                    "required": required,
                    "missing": missing,
                    "ready": not missing,
                    "endpoint": endpoint,
                }
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}".strip()

    return {
        "baseUrl": base_url,
        "installed": [],
        "installedCount": 0,
        "required": required,
        "missing": required,
        "ready": False,
        "error": last_error or "Local model service is unavailable",
    }


async def _benchmark_local_models() -> dict[str, object]:
    status = await _local_model_status()
    base_url = str(status.get("baseUrl", _local_base_url()))
    models = list(status.get("installed") or status.get("required") or _required_local_models())
    models = [model for model in models if isinstance(model, str) and model.strip()]

    prompt = "Summarize the benefits and risks of renewable energy in 3 sentences."
    results: list[dict[str, object]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in models:
            started = time.perf_counter()
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a concise benchmark assistant."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 128,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = _extract_chat_content(payload)
                latency = max(0.001, time.perf_counter() - started)
                token_estimate = max(1, len(content.split()))
                results.append(
                    {
                        "model": model,
                        "latencySeconds": round(latency, 3),
                        "tokensGenerated": token_estimate,
                        "tokensPerSecond": round(token_estimate / latency, 2),
                        "preview": content[:240],
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "model": model,
                        "error": f"{type(exc).__name__}: {exc}".strip(),
                    }
                )

    return {
        "baseUrl": base_url,
        "ready": bool(status.get("ready")),
        "installed": status.get("installed", []),
        "required": status.get("required", []),
        "benchmarks": results,
    }


def _extract_local_models(payload: object) -> list[str]:
    models: list[str] = []
    if not isinstance(payload, dict):
        return models

    for entry in payload.get("models", []) if isinstance(payload.get("models"), list) else []:
        if isinstance(entry, dict):
            name = str(entry.get("name") or entry.get("id") or "").strip()
            if name and name not in models:
                models.append(name)

    for entry in payload.get("data", []) if isinstance(payload.get("data"), list) else []:
        if isinstance(entry, dict):
            name = str(entry.get("id") or entry.get("name") or "").strip()
            if name and name not in models:
                models.append(name)

    return models


def _extract_chat_content(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content", "")
                if isinstance(content, list):
                    parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
                    return "\n".join(part for part in parts if part).strip()
                return str(content).strip()

    return str(payload.get("response", "")).strip()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
