import uuid
from fastapi_users import schemas
from app.models.user import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    role: UserRole


class UserCreate(schemas.BaseUserCreate):
    role: UserRole = UserRole.editor


class UserUpdate(schemas.BaseUserUpdate):
    role: UserRole | None = None
