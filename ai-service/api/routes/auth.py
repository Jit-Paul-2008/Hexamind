from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from auth.jwt import create_access_token
from auth.password import hash_password, verify_password
from database.connection import get_db_session
from database.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    displayName: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    userId: str
    email: str
    displayName: str


class MeResponse(BaseModel):
    userId: str
    email: str
    displayName: str
    isActive: bool
    createdAt: float


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> AuthResponse:
    existing = (await session.execute(select(User).where(User.email == payload.email))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        display_name=payload.displayName,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(
        accessToken=token,
        userId=user.id,
        email=user.email,
        displayName=user.display_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> AuthResponse:
    user = (await session.execute(select(User).where(User.email == payload.email))).scalars().first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id)
    return AuthResponse(
        accessToken=token,
        userId=user.id,
        email=user.email,
        displayName=user.display_name,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        userId=user.id,
        email=user.email,
        displayName=user.display_name,
        isActive=user.is_active,
        createdAt=_timestamp(user.created_at),
    )


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    return value.timestamp()
