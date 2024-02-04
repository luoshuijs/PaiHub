from typing import Optional
from datetime import date
from pixnet.client.base import BaseClient
from pixnet.utils.types import JSONDict


class Illust(BaseClient):
    async def get_detail(self, illust_id: int, lang: Optional[str] = None) -> JSONDict:
        params = {"illust_id": illust_id, "lang": self.lang or lang}
        return await self.request_api("GET", "https://www.pixiv.net/touch/ajax/illust/detail", params=params)

    async def search_illusts(
        self,
        word: str,
        search_mode: str = "s_tag_full",
        search_type: str = "all",
        lang: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> JSONDict:
        params = {"word": word, "s_mode": search_mode, "type": search_type, "lang": self.lang or lang}
        if start_date is not None:
            params["scd"] = start_date.strftime("%Y-%m-%d")
        if end_date is not None:
            params["ecd"] = end_date.strftime("%Y-%m-%d")
        return await self.request_api("GET", "https://www.pixiv.net/touch/ajax/search/illusts", params=params)

    async def get_recommend(self, illust_id: int, limit: int = 18, lang: Optional[str] = None) -> JSONDict:
        params = {"limit": limit, "lang": self.lang or lang}
        url = f"https://www.pixiv.net/ajax/illust/{illust_id}/recommend/init"
        return await self.request_api("GET", url, params=params)
