from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field, Column, Relationship, BigInteger, Integer, DateTime, VARCHAR, Text

from core.services.artwork.models import Artwork


class WorkChannel(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: Optional[int] = Field(default=None, foreign_key="work.id")
    channel_id: Optional[int] = Field(default=None, sa_column=Column("channel_id", BigInteger))

    work: Optional["WorkTable"] = Relationship(back_populates="channels")


class WorkChannelTable(WorkChannel, table=True):
    __tablename__ = "work_channel"


class Work(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    name: Optional[str] = Field(default=None, sa_column=Column("name", VARCHAR(255)))
    description: Optional[str] = Field(default=None, sa_column=Column("description", VARCHAR(255)))

    auto_review_rules: List["AutoReviewRulesTable"] = Relationship(back_populates="work")
    work_rules: List["WorkRulesTable"] = Relationship(back_populates="work")
    channels: List[WorkChannel] = Relationship(back_populates="work")


class WorkTable(Work, table=True):
    __tablename__ = "work"


class AutoReviewRule(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: Optional[int] - Field(default=None, foreign_key="work.id")
    name: Optional[str] = Field(default=None, sa_column=Column("name", VARCHAR(255)))
    description: Optional[str] = Field(default=None, sa_column=Column("description", VARCHAR(255)))
    action: Optional[int] = Field(default=None, sa_column=Column("action", Integer))
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    rules: Optional[str] = Field(default=None, sa_column=Column("rules", Text))

    work: Optional[Work] = Relationship(back_populates="auto_review_rules")


class AutoReviewRulesTable(AutoReviewRule, table=True):
    __tablename__ = "auto_review_rules"


class Review(SQLModel):
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

    artwork: Optional[Artwork] = Relationship()
    work: Optional[Work] = Relationship()


class ReviewTable(Review, table=True):
    __tablename__ = "review"


class WorkRule(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: Optional[int] = Field(default=None, foreign_key="work.id")
    order_num: Optional[int] = Field(default=None, sa_column=Column("order_num", Integer))
    name: Optional[str] = Field(default=None, sa_column=Column("name", VARCHAR(255)))
    description: Optional[str] = Field(default=None, sa_column=Column("description", VARCHAR(255)))
    pattern: Optional[str] = Field(default=None, sa_column=Column("pattern", VARCHAR(255)))
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    action: Optional[int] = Field(default=None, sa_column=Column("action", Integer))
    rules: Optional[str] = Field(default=None, sa_column=Column("rules", Text))

    work: Optional[Work] = Relationship(back_populates="work_rules")


class WorkRulesTable(WorkRule, table=True):
    __tablename__ = "work_rules"
