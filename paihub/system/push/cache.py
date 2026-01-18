from collections.abc import Iterable

from paihub.base import Component
from paihub.dependence.redis import Redis


class PushCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client

    async def set_pending_push(self, work_id: int, values: Iterable[int]) -> int:
        return await self.client.sadd(f"push:pending:{work_id}", *values)

    async def get_pending_push(self, work_id: int) -> str | None:
        data = await self.client.spop(f"push:pending:{work_id}", 1)
        if data is None:
            return None
        if len(data) == 0:
            return None
        return data[-1]

    async def get_push_count(self, work_id: int) -> int:
        return await self.client.scard(f"push:pending:{work_id}")

    async def remove_from_push_queue(self, work_id: int, review_id: int) -> bool:
        """从推送队列中移除指定的 review

        Args:
            work_id: 工作ID
            review_id: 审核ID

        Returns:
            是否成功移除（True表示原本存在并已移除）
        """
        removed_count = await self.client.srem(f"push:pending:{work_id}", review_id)
        return removed_count > 0
