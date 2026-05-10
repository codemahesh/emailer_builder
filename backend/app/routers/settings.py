import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.database import get_async_session
from app.models.settings import GlobalSettings, KeywordMapping
from app.models.user import User
from app.schemas.settings import (
    GlobalSettingsRead,
    GlobalSettingsUpdate,
    KeywordMappingCreate,
    KeywordMappingRead,
    KeywordMappingUpdate,
)
from fastapi_users.password import PasswordHelper

password_helper = PasswordHelper()


class CreateUserBody(BaseModel):
    email: str
    password: str

router = APIRouter()

SINGLETON_ID = 1


async def _get_or_create_settings(session: AsyncSession) -> GlobalSettings:
    """Return the singleton GlobalSettings row, creating it with defaults if absent."""
    result = await session.execute(
        select(GlobalSettings).where(GlobalSettings.id == SINGLETON_ID)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = GlobalSettings(id=SINGLETON_ID)
        session.add(row)
        await session.flush()
        await session.refresh(row)
    return row


# ── Global Settings ────────────────────────────────────────────────────────────


@router.get("", response_model=GlobalSettingsRead)
async def get_settings(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> GlobalSettings:
    return await _get_or_create_settings(session)


@router.patch("", response_model=GlobalSettingsRead)
async def update_settings(
    data: GlobalSettingsUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> GlobalSettings:
    row = await _get_or_create_settings(session)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value)
    await session.flush()
    await session.refresh(row)
    return row


# ── Keyword Mappings ───────────────────────────────────────────────────────────


@router.get("/keywords", response_model=List[KeywordMappingRead])
async def list_keyword_mappings(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> List[KeywordMapping]:
    result = await session.execute(
        select(KeywordMapping).order_by(KeywordMapping.created_at.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/keywords",
    response_model=KeywordMappingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_keyword_mapping(
    data: KeywordMappingCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> KeywordMapping:
    # Check for duplicate keyword
    existing = await session.execute(
        select(KeywordMapping).where(KeywordMapping.keyword == data.keyword)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Keyword '{data.keyword}' already exists",
        )
    mapping = KeywordMapping(id=uuid.uuid4(), keyword=data.keyword, icon=data.icon)
    session.add(mapping)
    await session.flush()
    await session.refresh(mapping)
    return mapping


@router.patch("/keywords/{mapping_id}", response_model=KeywordMappingRead)
async def update_keyword_mapping(
    mapping_id: uuid.UUID,
    data: KeywordMappingUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> KeywordMapping:
    result = await session.execute(
        select(KeywordMapping).where(KeywordMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword mapping not found",
        )
    update_data = data.model_dump(exclude_unset=True)
    # Check for keyword uniqueness if keyword is being updated
    if "keyword" in update_data and update_data["keyword"] != mapping.keyword:
        dup = await session.execute(
            select(KeywordMapping).where(
                KeywordMapping.keyword == update_data["keyword"]
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Keyword '{update_data['keyword']}' already exists",
            )
    for field, value in update_data.items():
        setattr(mapping, field, value)
    await session.flush()
    await session.refresh(mapping)
    return mapping


@router.delete("/keywords/{mapping_id}")
async def delete_keyword_mapping(
    mapping_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
) -> dict:
    result = await session.execute(
        select(KeywordMapping).where(KeywordMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword mapping not found",
        )
    await session.delete(mapping)
    await session.commit()
    return {}


# ── User Management (admin only) ───────────────────────────────────────────────


@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> list:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    result = await session.execute(select(User).order_by(User.email))
    users = list(result.scalars().all())
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserBody,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user),
) -> dict:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    hashed_password = password_helper.hash(body.password)
    new_user = User(
        email=body.email,
        hashed_password=hashed_password,
        role="reviewer",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    session.add(new_user)
    await session.flush()
    await session.refresh(new_user)
    await session.commit()
    return {"id": str(new_user.id), "email": new_user.email, "role": new_user.role}
