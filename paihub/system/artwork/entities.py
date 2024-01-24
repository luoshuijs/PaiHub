from typing import Optional, List

from sqlmodel import SQLModel, Column, Relationship, Field, BigInteger, Integer, VARCHAR

from paihub.system.sites.entities import Web


class Artist(SQLModel, table=True):
    __tablename__ = "artist"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    web_id: Optional[int] = Field(default=None, foreign_key="web.id")
    artist_id: Optional[int] = Field(default=None, foreign_key="artist.id")
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    remark: Optional[str] = Field(default=None, sa_column=Column("remark", VARCHAR(255)))

    artworks: List["Artwork"] = Relationship(back_populates="artist")
    # web: Optional[Web] = Relationship()


class Artwork(SQLModel, table=True):
    __tablename__ = "artwork"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    web_id: Optional[int] = Field(default=None, foreign_key="web.id")
    original_id: Optional[int] = Field(default=None, sa_column=Column("original_id", BigInteger))
    artist_id: Optional[int] = Field(default=None, foreign_key="artist.id")

    artist: Optional[Artist] = Relationship(back_populates="artworks")
    # web: Optional[Web] = Relationship()
