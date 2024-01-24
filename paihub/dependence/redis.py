from paihub.base import BaseDependence
from paihub.config import Redis as RedisConfig
from paihub.log import logger
from paihub.utils.aioredis import aioredis, RedisTimeoutError, RedisConnectionError


class Redis(BaseDependence):
    def __init__(self, config: RedisConfig):
        self.client = aioredis.Redis(host=config.host, port=config.port, db=config.database, password=config.password)
        self.ttl = 600

    async def get_redis(self) -> aioredis.Redis:
        return self.client

    async def ping(self):
        if await self.client.ping():
            logger.info("连接 Redis 成功")
        else:
            logger.info("连接 Redis 失败")
            raise RuntimeError("连接 Redis 失败")

    async def initialize(self):
        logger.info("正在尝试建立与 Redis 连接")
        # try:
        #     await self.ping()
        # except (RedisTimeoutError, RedisConnectionError) as exc:
        #     if isinstance(exc, RedisTimeoutError):
        #         logger.warning("连接 Redis 超时，使用 fakeredis 模拟")
        #     if isinstance(exc, RedisConnectionError):
        #         logger.warning("连接 Redis 失败，使用 fakeredis 模拟")
        await self.ping()

    async def shutdown(self):
        await self.client.close()
