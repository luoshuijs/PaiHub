import enum
from datetime import datetime

from sqlmodel import Column, DateTime, Enum, Field, Integer, SQLModel

__all__ = ("User", "PermissionsEnum")


class PermissionsEnum(enum.IntEnum):
    OWNER = 1
    ADMIN = 2
    PUBLIC = 3


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, sa_column=Column("id", Integer, primary_key=True, autoincrement=True))
    user_id: int = Field(sa_column=Column("user_id", Integer, unique=True))
    permissions: PermissionsEnum | None = Field(sa_column=Column("permissions", Enum(PermissionsEnum)))
    locale: str | None
    ban_end_time: datetime | None = Field(sa_column=Column("ban_end_time", DateTime(timezone=True)))
    ban_start_time: datetime | None = Field(sa_column=Column("ban_start_time", DateTime(timezone=True)))
    is_banned: int | None
