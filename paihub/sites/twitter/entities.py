from datetime import datetime

from sqlalchemy import func
from sqlmodel import BigInteger, Column, DateTime, Field, SQLModel

from paihub.entities.artwork import ArtWork
from paihub.entities.author import Author
from paihub.utils.sql_types import Tags


class Twitter(SQLModel, table=True):
    __tablename__ = "twitter"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    tags: list[str] | None = Field(default=None, sa_column=Column("tags", Tags))
    text: str | None
    views_count: int | None
    favorite_count: int | None
    retweet_count: int | None
    author_id: int | None
    create_time: datetime | None = Field(default=None, sa_column=Column("create_time", DateTime))
    update_time: datetime | None = Field(
        default=None, sa_column=Column("update_time", DateTime, default=func.now(), onupdate=func.now())
    )


class TwitterAuthor(Author):
    username: str

    @property
    def url(self) -> str:
        return f"https://twitter.com/{self.username}"


class TwitterArtWork(ArtWork):
    web_name: str = "Twitter"
    author: TwitterAuthor

    @property
    def url(self) -> str:
        return f"https://twitter.com/{self.author.username}/status/{self.artwork_id}"
