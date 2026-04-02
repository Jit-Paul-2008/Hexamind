from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str | int | bool]:
    return pipeline_service.health()


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
