from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import Organization

router = APIRouter(prefix="/api/v2/organizations", tags=["organizations"])


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    createdAt: float


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(session: AsyncSession = Depends(get_db_session)) -> list[OrganizationResponse]:
    rows = (await session.execute(select(Organization).order_by(Organization.created_at.desc()))).scalars().all()
    return [
        OrganizationResponse(
            id=row.id,
            name=row.name,
            slug=row.slug,
            createdAt=_timestamp(row.created_at),
        )
        for row in rows
    ]


@router.post("", response_model=OrganizationResponse)
async def create_organization(payload: OrganizationCreate, session: AsyncSession = Depends(get_db_session)) -> OrganizationResponse:
    existing = (await session.execute(select(Organization).where(Organization.slug == payload.slug))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already exists")

    record = Organization(name=payload.name, slug=payload.slug)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return OrganizationResponse(
        id=record.id,
        name=record.name,
        slug=record.slug,
        createdAt=_timestamp(record.created_at),
    )


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return value.timestamp()
