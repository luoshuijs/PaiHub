from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import SQLModel, Field, Column, BigInteger, Integer, DateTime, VARCHAR


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: Optional[int] = Field(default=None, foreign_key="work.id")
    web_id: Optional[int] = Field(default=None, foreign_key="sites.id")
    artwork_id: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    auto: Optional[bool] = Field(default=None, sa_column=Column("auto", Integer))
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column("reviewer_notes", VARCHAR(255)))
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime, default=func.now()))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(
        default=None, sa_column=Column("update_time", DateTime, onupdate=func.now())
    )


# class AutoReviewRule(SQLModel):
#     __tablename__ = "auto_review_rules"
#
#     id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
#     work_id: Optional[int] = Field(default=None, foreign_key="work.id")
#     name: Optional[str] = Field(default=None, sa_column=Column("name", VARCHAR(255)))
#     description: Optional[str] = Field(default=None, sa_column=Column("description", VARCHAR(255)))
#     action: Optional[int] = Field(default=None, sa_column=Column("action", Integer))
#     status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
#     rules: Optional[str] = Field(default=None, sa_column=Column("rules", Text))
#
#     work: Optional[Work] = Relationship(back_populates="auto_review_rules")
#