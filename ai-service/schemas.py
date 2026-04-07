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
    reportLength: str = Field(default="moderate", pattern="^(brief|moderate|huge)$")


class StartPipelineResponse(BaseModel):
    sessionId: str


class SarvamTransformRequest(BaseModel):
    targetLanguageCode: str = Field(min_length=2, max_length=20)
    instruction: str = Field(default="", max_length=2000)


class SarvamTransformResponse(BaseModel):
    sessionId: str
    text: str
    languageCode: str
    instructionApplied: bool
    provider: str
    fallback: bool
    notes: list[str] = Field(default_factory=list)


class PipelineEventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_CHUNK = "agent_chunk"
    AGENT_DONE = "agent_done"
    PIPELINE_DONE = "pipeline_done"
    PIPELINE_ERROR = "pipeline_error"
    ERROR = "error"


class PipelineEvent(BaseModel):
    type: PipelineEventType
    agentId: str
    chunk: str | None = None
    fullContent: str | None = None
    error: str | None = None
