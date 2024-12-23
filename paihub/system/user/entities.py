import enum
from datetime import datetime

from sqlmodel import BigInteger, Column, DateTime, Enum, Field, Integer, SQLModel

__all__ = ("User", "PermissionsEnum")


class PermissionsEnum(enum.IntEnum):
    OWNER = 1
    ADMIN = 2
    PUBLIC = 3


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, sa_column=Column(Integer(), primary_key=True, autoincrement=True))
    user_id: int = Field(sa_column=Column(BigInteger(), unique=True))
    permissions: PermissionsEnum | None = Field(sa_column=Column(Enum(PermissionsEnum)))
    locale: str | None = Field()
    ban_end_time: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    ban_start_time: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    is_banned: int | None = Field()
