from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import Case, Run

router = APIRouter(prefix="/api/v2/runs", tags=["runs"])


class RunCreate(BaseModel):
    caseId: str
    mode: str = Field(default="deep_research", max_length=50)
    status: str = Field(default="pending", max_length=20)
    sessionId: str | None = Field(default=None, max_length=100)


class RunResponse(BaseModel):
    id: str
    caseId: str
    mode: str
    status: str
    sessionId: str | None
    createdAt: float


@router.get("", response_model=list[RunResponse])
async def list_runs(caseId: str | None = None, session: AsyncSession = Depends(get_db_session)) -> list[RunResponse]:
    stmt = select(Run).order_by(Run.created_at.desc())
    if caseId:
        stmt = stmt.where(Run.case_id == caseId)
    rows = (await session.execute(stmt)).scalars().all()
    return [_run_response(item) for item in rows]


@router.post("", response_model=RunResponse)
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_db_session)) -> RunResponse:
    case = (await session.execute(select(Case).where(Case.id == payload.caseId))).scalars().first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    record = Run(
        case_id=payload.caseId,
        mode=payload.mode,
        status=payload.status,
        session_id=payload.sessionId,
        started_at=datetime.utcnow(),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _run_response(record)


def _run_response(item: Run) -> RunResponse:
    return RunResponse(
        id=item.id,
        caseId=item.case_id,
        mode=item.mode,
        status=item.status,
        sessionId=item.session_id,
        createdAt=_timestamp(item.created_at),
    )


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return value.timestamp()
