from datetime import UTC, datetime
from enum import IntEnum

from pydantic import BaseModel

from paihub.entities.author import Author


class ImageType(IntEnum):
    STATIC = 1
    DYNAMIC = 2


class ArtWork(BaseModel):
    web_name: str
    artwork_id: int
    title: str
    tags: list[str] = []
    create_time: datetime
    author: Author
    nsfw: bool = False
    source: str | None = None
    is_sourced: bool = False
    image_type: ImageType = ImageType.STATIC

    def get_create_time_timestamp(self) -> int:
        return int(self.create_time.replace(tzinfo=UTC).timestamp())

    @property
    def url(self) -> str:
        return ""
