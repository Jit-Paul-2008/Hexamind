from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Agent(BaseModel):
    id: str
    codename: str
    role: str
    purpose: str
    accentColor: str
    glowColor: str
    shape: str
    processingOrder: int


class StartPipelineRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class StartPipelineResponse(BaseModel):
    sessionId: str


class PipelineEventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_CHUNK = "agent_chunk"
    AGENT_DONE = "agent_done"
    PIPELINE_DONE = "pipeline_done"
    ERROR = "error"


class PipelineEvent(BaseModel):
    type: PipelineEventType
    agentId: str
    chunk: str | None = None
    fullContent: str | None = None
    error: str | None = None
