import os
from datetime import datetime, timezone
from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel

from paihub.entities.author import Author
from paihub.utils.name_map import NameMap

cur_path = os.path.realpath(os.getcwd())
log_path = os.path.join(cur_path, "metadata")
name_map_file = os.path.join(log_path, "name_map.json")
name_map = NameMap(name_map_file)


class ImageType(IntEnum):
    STATIC = 1
    DYNAMIC = 2


class ArtWork(BaseModel):
    web_name: str
    artwork_id: int
    title: str
    tags: List[str] = []
    create_time: datetime
    author: Author
    nsfw: bool = False
    source: Optional[str] = None
    is_upload: bool = False
    image_type: ImageType = ImageType.STATIC

    def format_tags(self, filter_character_tags: bool = False) -> str:
        if filter_character_tags:
            return name_map.filter_character_tags(self.tags)
        return " ".join(f"#{tag}" for tag in self.tags)

    def get_create_time_timestamp(self) -> int:
        return int(self.create_time.replace(tzinfo=timezone.utc).timestamp())

    @property
    def url(self) -> str:
        return ""
