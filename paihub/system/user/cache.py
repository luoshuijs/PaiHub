from typing import List

from paihub.base import Component
from paihub.dependence.redis import Redis


class UserAdminCache(Component):
    def __init__(self, redis: Redis):
        self.client = redis.client
        self.qname = "users:admin"

    async def ismember(self, user_id: int) -> bool:
        return await self.client.sismember(self.qname, user_id)

    async def get_all(self) -> List[int]:
        return [int(str_data) for str_data in await self.client.smembers(self.qname)]

    async def set(self, user_id: int) -> bool:
        return await self.client.sadd(self.qname, user_id)

    async def remove(self, user_id: int) -> bool:
        return await self.client.srem(self.qname, user_id)

    async def remove_all(self) -> bool:
        return await self.client.delete(self.qname)