from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Column, Relationship, Field, BigInteger, Integer, VARCHAR, DateTime

from paihub.services.sites.models import Web


class Artist(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    web_id: Optional[int] = Field(default=None, foreign_key="web.id")
    artist_id: Optional[int] = Field(default=None, foreign_key="artist.id")
    status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
    remark: Optional[str] = Field(default=None, sa_column=Column("remark", VARCHAR(255)))

    artworks: List["Artwork"] = Relationship(back_populates="artist")
    web: Optional[Web] = Relationship()


class ArtistTable(Artist, table=True):
    __tablename__ = "artist"


class Artwork(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    web_id: Optional[int] = Field(default=None, foreign_key="web.id")
    original_id: Optional[int] = Field(default=None, sa_column=Column("original_id", BigInteger))
    artist_id: Optional[int] = Field(default=None, foreign_key="artist.id")

    artist: Optional[Artist] = Relationship(back_populates="artworks")
    web: Optional[Web] = Relationship()


class ArtworkTable(Artwork, table=True):
    __tablename__ = "artwork"


class Pixiv(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    title: Optional[str] = Field(default=None, sa_column=Column("title", VARCHAR(255)))
    tags: Optional[str] = Field(default=None, sa_column=Column("tags", VARCHAR(255)))
    view_count: Optional[int] = Field(default=None, sa_column=Column("view_count", BigInteger))
    like_count: Optional[int] = Field(default=None, sa_column=Column("like_count", BigInteger))
    love_count: Optional[int] = Field(default=None, sa_column=Column("love_count", BigInteger))
    artist_id: Optional[int] = Field(default=None, foreign_key="artist.id")
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column("update_time", DateTime))

    artist: Optional[Artist] = Relationship()


class PixivTable(Pixiv, table=True):
    __tablename__ = "pixiv"
