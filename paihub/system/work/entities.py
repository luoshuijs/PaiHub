from typing import Optional

from sqlmodel import BigInteger, Column, Field, Relationship, SQLModel


class Work(SQLModel, table=True):
    __tablename__ = "work"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    name: str | None
    description: str | None

    work_rules: list["WorkRule"] = Relationship(back_populates="work")
    work_channels: list["WorkChannel"] = Relationship(back_populates="work")


class WorkRule(SQLModel, table=True):
    __tablename__ = "work_rules"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: int = Field(foreign_key="work.id")
    name: str | None
    description: str | None
    search_text: str
    is_pattern: bool

    work: Optional["Work"] = Relationship(back_populates="work_rules")


class WorkChannel(SQLModel, table=True):
    __tablename__ = "work_channel"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: int | None = Field(default=None, foreign_key="work.id")
    channel_id: int | None = Field(default=None, sa_column=Column("channel_id", BigInteger))

    work: Optional["Work"] = Relationship(back_populates="work_channels")
