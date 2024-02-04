from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient

from paihub.base import BaseDependence
from paihub.config import MongodbConfig
from paihub.log import logger


class Mongodb(BaseDependence):
    def __init__(self):
        config = MongodbConfig()
        self.client = AsyncIOMotorClient(config.host, config.port)

    async def initialize(self) -> None:
        try:
            await self.client.admin.command("ping")
            logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as exc:
            logger.error("Connect MongoDB Failed", exc_info=exc)
            raise exc

    @property
    def db(self) -> AgnosticDatabase:
        return self.client["paihub"]
