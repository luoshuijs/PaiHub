from datetime import datetime
from typing import List

from pydantic import BaseModel

from paihub.entities.author import Auther


class ArtWork(BaseModel):
    artwork_id: int
    title: str
    tags: List[str] = []
    create_time: datetime
    auther: Auther
