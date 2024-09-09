from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from httpx import AsyncClient
from pybooru import Danbooru, PybooruHTTPError

from paihub.base import BaseApi
from paihub.error import ArtWorkNotFoundError, BadRequest
from paihub.sites.danbooru.cache import DanbooruCache
from paihub.sites.danbooru.entities import DanbooruArtWork, DanbooruUploader
from paihub.utils.functools import async_wrap


class DanbooruApi(BaseApi):
    def __init__(self, cache: DanbooruCache):
        self.api = Danbooru("danbooru")
        executor = ThreadPoolExecutor(max_workers=2)
        self.post_show = async_wrap(self.api.post_show, executor=executor)
        self.post_list = async_wrap(self.api.post_list, executor=executor)
        self.cache = cache
        self.download_client = AsyncClient()

    async def get_post(self, post_id: Optional[int] = None, md5: Optional[str] = None) -> Dict[str, Any]:
        try:
            if post_id:
                post = await self.post_show(post_id)
            else:
                post = await self.post_list(md5=md5)
        except PybooruHTTPError as err:
            message = err.__str__()
            if "Not Found" in message:
                raise ArtWorkNotFoundError("Post not found") from err
            raise BadRequest("Pybooru HTTP Error") from err
        if "file_url" not in post:
            raise BadRequest("You may need a gold account to view this post\nSource: " + post["source"])
        return post

    async def get_artwork_info(self, post_id: Optional[int] = None) -> DanbooruArtWork:
        post = await self.cache.get_result(post_id)
        if post is None:
            post = await self.get_post(post_id)
            await self.cache.set_result(post_id, post)
        created_at = datetime.fromisoformat(post["created_at"])
        source = post["source"]
        tags = post["tag_string"].split(" ")
        uploader_id = post["uploader_id"]
        uploader = DanbooruUploader(auther_id=uploader_id, name="Danbooru Uploader")
        return DanbooruArtWork(
            artwork_id=post["id"],
            tags=tags,
            title=str(post["id"]),
            create_time=created_at,
            author=uploader,
            source=source,
        )

    async def get_artwork_images(self, post_id: Optional[int] = None) -> List[bytes]:
        post = await self.cache.get_result(post_id)
        if post is None:
            post = await self.get_post(post_id)
            await self.cache.set_result(post_id, post)
        url = post["file_url"]
        data = b""
        async with self.download_client.stream("GET", url) as response:
            async for chunk in response.aiter_bytes():
                data += chunk
        return [data]
