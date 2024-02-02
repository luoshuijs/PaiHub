from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import SQLModel, Field, Column, BigInteger, Integer, DateTime

from paihub.utils.sql_types import JSON


class Push(SQLModel, table=True):
    __tablename__ = "push"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    review_id: Optional[int] = Field(default=None, foreign_key="review.id")
    channel_id: Optional[int] = Field(default=None, sa_column=Column("channel_id", Integer))
    message_id: Optional[int] = Field(default=None, sa_column=Column("message_id", Integer))
    status: Optional[bool] = Field(default=False, sa_column=Column("status", Integer))
    ext: Optional[dict] = Field(default=None, sa_column=Column("ext", JSON))
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime, default=func.now()))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(
        default=None, sa_column=Column("update_time", DateTime, onupdate=func.now())
    )

    # review: Optional[Review] = Relationship()
