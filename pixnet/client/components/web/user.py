from typing import Optional

from pixnet.client.base import BaseClient
from pixnet.utils.types import JSONDict


class User(BaseClient):
    async def get_user_status(self, lang: Optional[str] = None) -> JSONDict:
        params = {"lang": self.lang or lang}
        result = await self.request_json("https://www.pixiv.net/touch/ajax/user/self/status", params=params)
        return result["user_status"]

    async def get_user_following(
        self, user_id: Optional[int] = None, offset: int = 0, limit: int = 24, lang: Optional[str] = None
    ) -> JSONDict:
        user_id = user_id or self.user_id
        if user_id is None:
            raise RuntimeError
        params = {"offset": offset, "limit": limit, "lang": self.lang or lang}
        url = f"https://www.pixiv.net/ajax/user/{user_id}/following"
        return await self.request_json(url, params=params)

    async def add_bookmark_user(self, user_id: int):
        params = {"mode": "add_bookmark_user", "restrict": 0, "user_id": user_id}
        await self.request("POST", "https://www.pixiv.net/touch/ajax_api/ajax_api.php", params=params)

    async def delete_bookmark_user(self, user_id: int):
        params = {"mode": "delete_bookmark_user", "user_id": user_id}
        await self.request("POST", "https://www.pixiv.net/touch/ajax_api/ajax_api.php", params=params)
