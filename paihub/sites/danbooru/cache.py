from paihub.base import Component
from paihub.dependence.redis import Redis

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class DanbooruCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client
        self.ttl = 60 * 60

    async def get_result(self, post_id: int) -> dict | None:
        data = await self.client.get(f"danbooru:web:{post_id}")
        if data is None:
            return None
        return jsonlib.loads(data)

    async def set_result(self, post_id: int, value: dict):
        await self.client.set(f"danbooru:web:{post_id}", jsonlib.dumps(value), ex=self.ttl)
