import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel
from watchfiles import awatch

from paihub.base import Component
from paihub.entities.author import Author
from paihub.log import logger
from paihub.utils.name_map import NameMap

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


__name_map__ = NameMap(Path(os.getcwd()) / "metadata" / "name_map.json")


class ImageType(IntEnum):
    STATIC = 1
    DYNAMIC = 2


class ArtWork(BaseModel):
    __name_nap__: ClassVar[NameMap] = __name_map__

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

    def format_tags(self, filter_character_tags: bool = False) -> str:
        if filter_character_tags:
            return self.__name_nap__.filter_character_tags(self.tags)
        return " ".join(f"#{tag}" for tag in self.tags)

    def get_create_time_timestamp(self) -> int:
        return int(self.create_time.replace(tzinfo=UTC).timestamp())

    @property
    def url(self) -> str:
        return ""


class WatchNameMap(Component):
    __name_nap__: ClassVar[NameMap] = __name_map__
    executor = ThreadPoolExecutor()
    stop_event: asyncio.Event = asyncio.Event()
    waiter_task: asyncio.Task = None
    loop: asyncio.AbstractEventLoop

    async def initialize(self):
        self.loop = asyncio.get_event_loop()
        self.waiter_task = asyncio.create_task(self.watch_name())

    async def shutdown(self):
        self.stop_event.set()
        if self.waiter_task:
            await self.waiter_task

    async def watch_name(self):
        logger.success("Successfully added Watch NameMap.")
        try:
            async for changes in awatch(self.__name_nap__.data_file, stop_event=self.stop_event):
                for change, path in changes:
                    logger.debug("Detected change: Path=%s, Event=%s", path, change.name)
                    try:
                        await self.loop.run_in_executor(self.executor, self.__name_nap__.load)
                    except jsonlib.JSONDecodeError as e:
                        logger.warning("NameMap loader json error")
                        logger.debug("Json error", exc_info=e)
                    except Exception as e:
                        logger.error("Exception", exc_info=e)
                    else:
                        logger.success("NameMap has been modified, reloaded successfully!")
        except Exception as exc:
            logger.error("Watch NameMap could not be loaded", exc_info=exc)
