from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from typing import Any, Dict

from apscheduler.triggers.interval import IntervalTrigger
from async_pixiv import PixivClient
from async_pixiv.const import APP_API_HOST
from async_pixiv.error import LoginError, PixivError
from async_pixiv.utils.rate_limiter import RateLimiter

from paihub.base import BaseApi
from paihub.entities.config import TomlConfig
from paihub.log import logger
from paihub.sites.pixiv.cache import PixivCache
from pixnet.client.web import WebClient
from pixnet.errors import BadRequest as PixNetBadRequest


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
        self.illust = self.client.ILLUST
        self.user = self.client.USER
        self.novel = self.client.NOVEL

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
        url = APP_API_HOST / "user/follow/add"
        data = {"user_id": user_id, "restrict": restrict}
        r = await self.client.request("POST", url, data=data)
        return r.json()


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
