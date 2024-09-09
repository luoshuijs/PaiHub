from paihub.base import BaseDependence
from paihub.config import RedisConfig
from paihub.log import logger
from paihub.utils.aioredis import RedisConnectionError, RedisTimeoutError, aioredis


class Redis(BaseDependence):
    def __init__(self):
        config = RedisConfig()
        self.client = aioredis.Redis(
            host=config.host, port=config.port, db=config.database, password=config.password, decode_responses=True
        )
        self.ttl = 600

    async def initialize(self):
        logger.info("正在尝试建立与 [red]Redis[/red] 连接")
        try:
            await self.client.ping()
        except RedisConnectionError as exc:
            logger.error("连接 [red]Redis[/red] 失败")
            raise exc
        except RedisTimeoutError as exc:
            logger.error("连接 [red]Redis[/red] 超时")
            raise exc
        else:
            logger.success("连接 [red]Redis[/red] 成功")

    async def shutdown(self):
        await self.client.close()
