from typing import Optional

from paihub.base import Component
from paihub.dependence.redis import Redis

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class WebClientCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client
        self.ttl = 60 * 60

    async def get_tweet_result_by_rest_id(self, tweet_id: int) -> Optional[dict]:
        data = await self.client.get(f"twitter:web:tweet_result_by_rest_id:{tweet_id}")
        if data is None:
            return None
        return jsonlib.loads(data)

    async def set_tweet_result_by_rest_id(self, tweet_id: int, value: dict):
        await self.client.set(f"twitter:web:tweet_result_by_rest_id:{tweet_id}", jsonlib.dumps(value), ex=self.ttl)

    async def get_tweet_detail(self, tweet_id: int) -> Optional[dict]:
        data = await self.client.get(f"twitter:web:tweet_detail:{tweet_id}")
        if data is None:
            return None
        return jsonlib.loads(data)

    async def set_tweet_detail(self, tweet_id: int, value: dict):
        await self.client.set(f"twitter:web:tweet_detail:{tweet_id}", jsonlib.dumps(value), ex=self.ttl)
