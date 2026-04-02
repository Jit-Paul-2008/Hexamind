from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from agents import AGENTS
from pipeline import pipeline_service
from schemas import Agent, StartPipelineRequest, StartPipelineResponse


app = FastAPI(title="Hexamind AI Service", version="1.0.0")

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
