from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, Relationship, BigInteger, Integer, DateTime

from paihub.system.review.entities import Review


class Push(SQLModel):
    __tablename__ = "push"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    review_id: Optional[int] = Field(default=None, foreign_key="review.id")
    date: Optional[datetime] = Field(default=None, sa_column=Column("date", DateTime))
    status: Optional[str] = Field(default=None, sa_column=Column("status", Integer))
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_at", DateTime))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column("update_at", DateTime))

    # review: Optional[Review] = Relationship()
