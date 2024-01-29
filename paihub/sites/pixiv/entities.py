from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import SQLModel, Column, Field, BigInteger, DateTime


class Pixiv(SQLModel, table=True):
    __tablename__ = "pixiv"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    title: Optional[str]
    tags: Optional[str]
    view_count: Optional[int]
    like_count: Optional[int]
    love_count: Optional[int]
    artist_id: Optional[int]
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column("update_time", DateTime, default=func.now()))
