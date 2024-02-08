from typing import Dict, Optional, Mapping, Any

from paihub.base import BaseService
from paihub.dependence.mongodb import Mongodb


class PixivSpiderDocument(BaseService):
    def __init__(self, mogo: Mongodb):
        self.web_search = mogo.db["pixiv_spider_web_search_data"]
        self.web_follow = mogo.db["pixiv_spider_web_follow"]
        self.pixiv_spider_author_info = mogo.db["pixiv_spider_artist"]

    async def initialize(self) -> None:
        await self.web_search.create_index([("id", 1)])
        await self.web_follow.create_index([("id", 1)])
        await self.pixiv_spider_author_info.create_index([("user_id", 1)], unique=True)

    async def set_web_search_data(self, data: Dict):
        data_id = data.get("id")
        if data_id is None:
            raise KeyError
        return await self.web_search.update_one({"id": data_id}, {"$set": data}, upsert=True)

    async def get_web_search_data(self, data_id: int) -> Optional[Mapping[str, Any]]:
        return await self.web_search.find_one({"id": f"{data_id}"})

    async def get_web_search_tags(self, data_id: int) -> Optional[Mapping[str, Any]]:
        return await self.web_search.find_one({"id": f"{data_id}"}, {"_id": 0, "tags": 1})

    async def set_web_follow_data(self, data: Dict):
        data_id = data.get("id")
        if data_id is None:
            raise KeyError
        return await self.web_follow.update_one({"id": data_id}, {"$set": data}, upsert=True)

    async def get_web_follow_data(self, data_id: int):
        return await self.web_follow.find_one({"id": f"{data_id}"})

    async def get_web_follow_tags(self, data_id: int) -> Optional[Mapping[str, Any]]:
        return await self.web_follow.find_one({"id": f"{data_id}"}, {"_id": 0, "tags": 1})

    async def set_not_exist_user(self, user_id: int):
        return await self.pixiv_spider_author_info.update_one(
            {"user_id": user_id}, {"$set": {"not_exist": True}}, upsert=True
        )

    async def set_artwork_fetch_status(self, user_id: int):
        return await self.pixiv_spider_author_info.update_one(
            {"user_id": user_id}, {"$set": {"artwork_fetch_status": True}}, upsert=True
        )

    async def if_user_not_exist(self, user_id: int) -> bool:
        document = await self.pixiv_spider_author_info.find_one({"user_id": user_id}, {"_id": 0, "not_exist": 1})
        if document is None:
            return False
        return document.get("not_exist") is True

    async def if_artwork_fetch_status(self, user_id: int) -> bool:
        document = await self.pixiv_spider_author_info.find_one(
            {"user_id": user_id}, {"_id": 0, "artwork_fetch_status": 1}
        )
        if document is None:
            return False
        return document.get("artwork_fetch_status") is True
