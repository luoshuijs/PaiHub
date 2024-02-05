from datetime import datetime
from typing import Optional, List

from sqlalchemy import func
from sqlmodel import SQLModel, Column, Field, BigInteger, DateTime

from paihub.entities.artwork import ArtWork
from paihub.entities.author import Author
from paihub.utils.sql_types import Tags


class Twitter(SQLModel, table=True):
    __tablename__ = "twitter"

    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    tags: Optional[List[str]] = Field(default=None, sa_column=Column("tags", Tags))
    text: Optional[str]
    views_count: Optional[int]
    favorite_count: Optional[int]
    retweet_count: Optional[int]
    author_id: Optional[int]
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_time: Optional[datetime] = Field(
        default=None, sa_column=Column("update_time", DateTime, default=func.now(), onupdate=func.now())
    )


class TwitterAuthor(Author):
    username: str

    @property
    def url(self) -> str:
        return f"https://twitter.com/{self.username}"


class TwitterArtWork(ArtWork):
    web_name = "Twitter"
    author: TwitterAuthor

    @property
    def url(self) -> str:
        return f"https://twitter.com/{self.author.username}/status/{self.artwork_id}"
