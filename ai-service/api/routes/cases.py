from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import Case, Project

router = APIRouter(prefix="/api/v2/cases", tags=["cases"])


class CaseCreate(BaseModel):
    projectId: str
    name: str = Field(min_length=2, max_length=300)
    initialQuestion: str = Field(min_length=2, max_length=4000)


class CaseResponse(BaseModel):
    id: str
    projectId: str
    name: str
    initialQuestion: str
    createdAt: float
    updatedAt: float


@router.get("", response_model=list[CaseResponse])
async def list_cases(projectId: str | None = None, session: AsyncSession = Depends(get_db_session)) -> list[CaseResponse]:
    stmt = select(Case).order_by(Case.updated_at.desc())
    if projectId:
        stmt = stmt.where(Case.project_id == projectId)
    rows = (await session.execute(stmt)).scalars().all()
    return [_case_response(item) for item in rows]


@router.post("", response_model=CaseResponse)
async def create_case(payload: CaseCreate, session: AsyncSession = Depends(get_db_session)) -> CaseResponse:
    project = (await session.execute(select(Project).where(Project.id == payload.projectId))).scalars().first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    record = Case(
        project_id=payload.projectId,
        name=payload.name,
        initial_question=payload.initialQuestion,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _case_response(record)


def _case_response(item: Case) -> CaseResponse:
    return CaseResponse(
        id=item.id,
        projectId=item.project_id,
        name=item.name,
        initialQuestion=item.initial_question,
        createdAt=_timestamp(item.created_at),
        updatedAt=_timestamp(item.updated_at),
    )


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return value.timestamp()
