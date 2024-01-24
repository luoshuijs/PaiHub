from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, BigInteger, Relationship


class Work(SQLModel, table=True):
    __tablename__ = "work"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    name: Optional[str]
    description: Optional[str]

    work_rules: List["WorkRule"] = Relationship(back_populates="work")
    work_channels: List["WorkChannel"] = Relationship(back_populates="work")


class WorkRule(SQLModel, table=True):
    __tablename__ = "work_rule"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: int = Field(foreign_key="work.id")
    name: Optional[str]
    description: Optional[str]
    search_text: str
    is_pattern: bool

    work: Optional["Work"] = Relationship(back_populates="work_rules")


class WorkChannel(SQLModel, table=True):
    __tablename__ = "work_channel"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: Optional[int] = Field(default=None, foreign_key="work.id")
    channel_id: Optional[int] = Field(default=None, sa_column=Column("channel_id", BigInteger))

    work: Optional["Work"] = Relationship(back_populates="work_channels")
