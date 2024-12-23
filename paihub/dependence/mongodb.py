from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient

from paihub.base import BaseDependence
from paihub.config import MongodbConfig
from paihub.log import logger


class Mongodb(BaseDependence):
    def __init__(self):
        config = MongodbConfig()
        self.client = AsyncIOMotorClient(config.host, config.port)
        self.default_database: str = config.default_database

    async def initialize(self) -> None:
        try:
            await self.client.admin.command("ping")
            logger.success("Pinged your deployment. You successfully connected to [green]MongoDB[/green]!")
        except Exception as exc:
            logger.error("Connect MongoDB Failed", exc_info=exc)
            raise

    @property
    def db(self) -> AgnosticDatabase:
        return self.client[self.default_database]
