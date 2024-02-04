from typing import Dict

from paihub.base import BaseService
from paihub.dependence.mongodb import Mongodb


class PixivSpiderDocument(BaseService):
    def __init__(self, mogo: Mongodb):
        self.collection = mogo.db["web_search_data"]

    async def initialize(self) -> None:
        await self.collection.create_index([("id", 1)])

    async def set_web_search_data(self, data: Dict):
        data_id = data.get("id")
        if data_id is None:
            raise KeyError
        return await self.collection.update_one({"id": data_id}, {"$set": data}, upsert=True)

    async def get_web_search_data(self, data_id: int):
        return await self.collection.find_one({"id": f"{data_id}"})

    async def get_web_search_tags(self, data_id: int):
        return await self.collection.find_one({"id": f"{data_id}"}, {"_id": 0, "tags": 1})
