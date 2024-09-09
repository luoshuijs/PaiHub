from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlmodel import BigInteger, Column, DateTime, Field, SQLModel

from paihub.entities.artwork import ArtWork
from paihub.entities.author import Author
from paihub.utils.sql_types import Tags


class Pixiv(SQLModel, table=True):
    __tablename__ = "pixiv"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    title: Optional[str]
    tags: Optional[List[str]] = Field(default=None, sa_column=Column("tags", Tags))
    view_count: Optional[int]
    like_count: Optional[int]
    love_count: Optional[int]
    author_id: Optional[int]
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_time: Optional[datetime] = Field(
        default=None, sa_column=Column("update_time", DateTime, default=func.now(), onupdate=func.now())
    )


class PixivAuthor(Author):
    @property
    def url(self) -> str:
        return f"https://www.pixiv.net/users/{self.auther_id}"


class PixivArtWork(ArtWork):
    web_name: str = "Pixiv"
    author: PixivAuthor

    @property
    def url(self) -> str:
        return f"https://www.pixiv.net/artworks/{self.artwork_id}"
