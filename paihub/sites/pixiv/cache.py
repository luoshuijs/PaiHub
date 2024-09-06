from typing import Iterable, List, Optional

from paihub.base import Component
from paihub.dependence.redis import Redis

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class PixivReviewCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client

    async def del_review_all_cache(self):
        await self.client.delete("pixiv:review:database")
        await self.client.delete("pixiv:review:already")

    async def set_database_artwork_ids(self, values: Iterable[int]) -> int:
        return await self.client.sadd("pixiv:review:database", *values)

    async def set_already_review_artwork_ids(self, values: Iterable[int]) -> int:
        return await self.client.sadd("pixiv:review:already", *values)

    async def get_ready_review_artwork_ids(self) -> List[int]:
        return await self.client.sdiff("pixiv:review:database", "pixiv:review:already")


class PixivCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client
        self.ttl = 60 * 10

    async def set_login_token(self, token: str):
        await self.client.set("pixiv:login:token", token)

    async def get_login_token(self) -> Optional[str]:
        return await self.client.get("pixiv:login:token")

    async def get_illust_detail(self, artwork_id: int) -> Optional[dict]:
        data = await self.client.get(f"pixiv:illust:detail:{artwork_id}")
        return jsonlib.loads(data)

    async def set_illust_detail(self, artwork_id: int, value: str):
        await self.client.set(f"pixiv:illust:detail:{artwork_id}", value, ex=self.ttl)
