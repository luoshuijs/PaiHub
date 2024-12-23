from collections.abc import Iterable

from paihub.base import Component
from paihub.dependence.redis import Redis


class ReviewCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client

    async def set_pending_review(self, values: Iterable[int], work_id: int) -> int:
        return await self.client.sadd(f"review:pending:{work_id}", *values)

    async def get_pending_review(self, work_id: int) -> str | None:
        data = await self.client.spop(f"review:pending:{work_id}", 1)
        if data is None:
            return None
        return data[-1]

    async def get_review_count(self, work_id: int) -> int:
        return await self.client.scard(f"review:pending:{work_id}")
