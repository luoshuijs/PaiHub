from datetime import date

from pixnet.client.base import BaseClient
from pixnet.utils.types import JSONDict


class Illust(BaseClient):
    async def get_detail(self, illust_id: int, lang: str | None = None) -> JSONDict:
        params = {"illust_id": illust_id, "lang": self.lang or lang}
        return await self.request_api("GET", "https://www.pixiv.net/touch/ajax/illust/details", params=params)

    async def search_illusts(
        self,
        word: str,
        page: int | None = None,
        search_mode: str = "s_tag_full",
        search_type: str = "all",
        lang: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> JSONDict:
        params = {"word": word, "s_mode": search_mode, "type": search_type, "lang": self.lang or lang}
        if start_date is not None:
            params["scd"] = start_date.strftime("%Y-%m-%d")
        if end_date is not None:
            params["ecd"] = end_date.strftime("%Y-%m-%d")
        if page is not None:
            params["p"] = page
        return await self.request_api("GET", "https://www.pixiv.net/touch/ajax/search/illusts", params=params)

    async def get_follow_latest(self, page: int | None = None, mode: str = "all", lang: str | None = None):
        params = {"mode": mode, "lang": self.lang or lang}
        if page is not None:
            params["p"] = page
        return await self.request_api("GET", "https://www.pixiv.net/ajax/follow_latest/illust", params=params)

    async def get_recommend(self, illust_id: int, limit: int = 18, lang: str | None = None) -> JSONDict:
        params = {"limit": limit, "lang": self.lang or lang}
        url = f"https://www.pixiv.net/ajax/illust/{illust_id}/recommend/init"
        return await self.request_api("GET", url, params=params)
