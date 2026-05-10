import enum
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    editor = "editor"
    reviewer = "reviewer"
    admin = "admin"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"),
        default=UserRole.editor,
        nullable=False,
        server_default=UserRole.editor.value,
    )
