from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import Organization, Project

router = APIRouter(prefix="/api/v2/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    orgId: str
    name: str = Field(min_length=2, max_length=200)
    description: str = ""


class ProjectResponse(BaseModel):
    id: str
    orgId: str
    name: str
    description: str
    createdAt: float
    updatedAt: float


@router.get("", response_model=list[ProjectResponse])
async def list_projects(orgId: str | None = None, session: AsyncSession = Depends(get_db_session)) -> list[ProjectResponse]:
    stmt = select(Project).order_by(Project.updated_at.desc())
    if orgId:
        stmt = stmt.where(Project.org_id == orgId)
    rows = (await session.execute(stmt)).scalars().all()
    return [_project_response(item) for item in rows]


@router.post("", response_model=ProjectResponse)
async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(get_db_session)) -> ProjectResponse:
    org = (await session.execute(select(Organization).where(Organization.id == payload.orgId))).scalars().first()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    record = Project(
        org_id=payload.orgId,
        name=payload.name,
        description=payload.description,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _project_response(record)


def _project_response(item: Project) -> ProjectResponse:
    return ProjectResponse(
        id=item.id,
        orgId=item.org_id,
        name=item.name,
        description=item.description,
        createdAt=_timestamp(item.created_at),
        updatedAt=_timestamp(item.updated_at),
    )


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return value.timestamp()
