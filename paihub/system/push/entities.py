from datetime import datetime

from sqlalchemy import func
from sqlmodel import BigInteger, Column, DateTime, Field, Integer, SQLModel

from paihub.utils.sql_types import JSON


class Push(SQLModel, table=True):
    __tablename__ = "push"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    review_id: int | None = Field(default=None, foreign_key="review.id")
    channel_id: int | None = Field(default=None, sa_column=Column("channel_id", Integer))
    message_id: int | None = Field(default=None, sa_column=Column("message_id", Integer))
    status: bool | None = Field(default=False, sa_column=Column("status", Integer))
    ext: dict | None = Field(default=None, sa_column=Column("ext", JSON))
    create_by: int | None = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: datetime | None = Field(default=None, sa_column=Column("create_time", DateTime, default=func.now()))
    update_by: int | None = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: datetime | None = Field(default=None, sa_column=Column("update_time", DateTime, onupdate=func.now()))

    # review: Optional[Review] = Relationship()
