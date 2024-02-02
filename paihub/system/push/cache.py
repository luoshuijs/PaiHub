from typing import Iterable, Optional

from paihub.base import Component
from paihub.dependence.redis import Redis


class PushCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client

    async def set_pending_push(self, work_id: int, values: Iterable[int]) -> int:
        return await self.client.sadd(f"push:pending:{work_id}", *values)

    async def get_pending_push(self, work_id: int) -> Optional[str]:
        data = await self.client.spop(f"push:pending:{work_id}", 1)
        if data is None:
            return None
        if len(data) == 0:
            return None
        return data[-1]

    async def get_push_count(self, work_id: int) -> int:
        return await self.client.scard(f"push:pending:{work_id}")
