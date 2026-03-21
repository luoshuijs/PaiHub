from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Integer
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from paihub.system.name_map.entities import NameMapConfig


class Work(SQLModel, table=True):
    __tablename__ = "work"

    id: int | None = Field(sa_column=Column("id", Integer, primary_key=True, autoincrement=True, nullable=False))
    name: str | None
    description: str | None

    work_rules: list["WorkRule"] = Relationship(back_populates="work")
    work_channels: list["WorkChannel"] = Relationship(back_populates="work")
    name_map_configs: list["NameMapConfig"] = Relationship(
        back_populates="work", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class WorkRule(SQLModel, table=True):
    __tablename__ = "work_rules"

    id: int | None = Field(sa_column=Column("id", Integer, primary_key=True, autoincrement=True, nullable=False))
    work_id: int = Field(foreign_key="work.id")
    name: str | None
    description: str | None
    search_text: str
    is_pattern: bool

    work: Optional["Work"] = Relationship(back_populates="work_rules")


class WorkChannel(SQLModel, table=True):
    __tablename__ = "work_channel"

    id: int | None = Field(sa_column=Column("id", Integer, primary_key=True, autoincrement=True, nullable=False))
    work_id: int = Field(foreign_key="work.id")
    channel_id: int = Field(sa_column=Column("channel_id", BigInteger, nullable=False))

    work: Optional["Work"] = Relationship(back_populates="work_channels")
