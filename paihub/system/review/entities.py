from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Column, Relationship, BigInteger, Integer, DateTime, VARCHAR, Text

from paihub.system.artwork.entities import Artwork


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    artwork_id: Optional[int] = Field(default=None, foreign_key="artwork.id")
    work_id: Optional[int] = Field(default=None, foreign_key="work.id")
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    auto: Optional[int] = Field(default=None, sa_column=Column("auto", Integer))
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column("reviewer_notes", VARCHAR(255)))
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column("update_time", DateTime))

    # artwork: Optional[Artwork] = Relationship()
    # work: Optional[Work] = Relationship()


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