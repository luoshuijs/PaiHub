from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from typing import Any, Dict, TYPE_CHECKING, Optional, List

from apscheduler.triggers.interval import IntervalTrigger
from async_pixiv import PixivClient
from async_pixiv.const import APP_API_HOST
from async_pixiv.error import LoginError, PixivError
from async_pixiv.model import Illust, PixivModel
from async_pixiv.model.other.result import PageResult
from async_pixiv.utils.context import set_pixiv_client
from async_pixiv.utils.rate_limiter import RateLimiter
from pydantic import Field

from paihub.base import BaseApi
from paihub.entities.config import TomlConfig
from paihub.log import logger
from paihub.sites.pixiv.cache import PixivCache
from pixnet.client.web import WebClient
from pixnet.errors import BadRequest as PixNetBadRequest

if TYPE_CHECKING:
    from async_pixiv.client.api._illust import IllustAPI
    from async_pixiv.client.api._user import UserAPI, UserPreview
    from async_pixiv.client.api._novel import NovelAPI
else:
    from async_pixiv.client.api._user import UserPreview


class UserIllustsResult(PageResult[Illust]):
    illusts: List[Illust]


class UserRelatedResult(PixivModel):
    users: List[UserPreview] = Field(alias="user_previews")


class IllustSearchResult(UserIllustsResult):
    pass


class PixivMobileApi(BaseApi):
    def __init__(self, cache: PixivCache):
        limiter = RateLimiter(max_rate=100, time_period=60)
        self.client = PixivClient(
            limiter=limiter,
            trust_env=True,
            retry_times=3,
            retry_sleep=1,
        )
        self.cache = cache
        self.config = TomlConfig("config/pixiv.toml")
        self.illust: "IllustAPI" = self.client.ILLUST
        self.user: "UserAPI" = self.client.USER
        self.novel: "NovelAPI" = self.client.NOVEL

    async def initialize(self) -> None:
        await self.login()
        self.application.scheduler.add_job(
            self.login, IntervalTrigger(minutes=30), next_run_time=datetime.now() + timedelta(minutes=30)
        )

    async def login(self):
        login_token = await self.cache.get_login_token()
        if login_token is None:
            raise RuntimeError("The [blue]Pixiv[/blue] Mobile API login has been deprecated.")
        else:
            try:
                user = await self.client.login_with_token(login_token)
                await self.cache.set_login_token(self.client.refresh_token)
                logger.success("[blue]Pixiv[/blue] Login with Token Success, Login User [%s]%s", user.id, user.name)
            except LoginError:
                logger.error("[blue]Pixiv[/blue] Login Error")
            except PixivError as exc:
                logger.error("[blue]Pixiv[/blue] Login Error", exc_info=exc)

    async def user_follow_add(self, user_id: int | str, restrict: str = "public") -> Dict[str, Any]:
        url = APP_API_HOST / "v1/user/follow/add"
        data = {"user_id": user_id, "restrict": restrict}
        response = await self.client.request("POST", url, data=data)
        return response.json()

    async def user_illusts(
        self,
        account_id: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> UserIllustsResult:
        if account_id is None:
            account_id = self.client.account.id
        response = await self.client.request_get(
            APP_API_HOST / "v1/user/illusts",
            params={
                "user_id": account_id,
                "type": "illust",
                "filter": "for_ios",
                "offset": offset,
            },
        )
        with set_pixiv_client(self.client):
            return UserIllustsResult.model_validate(response.json())

    async def illust_follow(self, offset: Optional[int] = None) -> IllustSearchResult:
        response = await self.client.request_get(
            APP_API_HOST / "v2/illust/follow",
            params={"restrict": "public", "offset": offset},
        )

        with set_pixiv_client(self.client):
            return IllustSearchResult.model_validate(response.json())


class PixivWebAPI(BaseApi):
    def __init__(self):
        self.config = TomlConfig(
            "config/pixiv.toml",
        )
        login = self.config.get("login")
        cookie = SimpleCookie()
        cookie.load(login.get("cookies"))
        cookies = {key: morsel.value for key, morsel in cookie.items()}
        self.client = WebClient(cookies=cookies, lang="zh")

    async def initialize(self) -> None:
        try:
            result = await self.client.get_user_status()
            if result["is_logged_in"]:
                logger.success(
                    "[blue]Pixiv[/blue] Web API Login with Cookies Success, Login User [%s]%s",
                    result["user_id"],
                    result["user_name"],
                )
            else:
                logger.warning("[blue]Pixiv[/blue] Web API Cookies Expire")
        except PixNetBadRequest as exc:
            logger.error("[blue]Pixiv[/blue] Web API Login Error", exc_info=exc)
