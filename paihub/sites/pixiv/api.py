from http.cookies import SimpleCookie

import toml
from async_pixiv import PixivClient
from async_pixiv.error import LoginError, PixivError
from playwright.async_api import Error as PlaywrightError

from paihub.base import BaseApi
from paihub.log import logger
from paihub.sites.pixiv.cache import PixivCache
from pixnet.client.web import WebClient
from pixnet.errors import BadRequest as PixNetBadRequest


class PixivMobileApi(BaseApi):
    def __init__(self, cache: PixivCache):
        self.client = PixivClient(
            max_rate=100,  # API 请求速率限制。默认 100 次
            rate_time_period=60,
            timeout=10,  # 默认超时秒数
            proxies=None,
            trust_env=True,
            retry=5,
            retry_sleep=1,  # 默认重复请求间隔秒数
        )
        self.cache = cache
        self.config: dict = {}
        with open("config/pixiv.toml", "r", encoding="utf-8") as f:
            self.config = toml.load(f)
        self.illust = self.client.ILLUST
        self.user = self.client.USER
        self.novel = self.client.NOVEL

    async def initialize(self) -> None:
        login_token = await self.cache.get_login_token()
        if login_token is None:
            try:
                login = self.config.get("login")
                username = login.get("username")
                password = login.get("password")
                proxy = login.get("proxy") if login.get("proxy") != "" else None
                if password != "" or username != "":
                    user = await self.client.login_with_pwd(username, password, proxy=proxy)
                    logger.info("Pixiv Mobile API Login with Password Success, Login User [%s]%s", user.id, user.name)
                else:
                    logger.warning("Pixiv Mobile API Login Token Not Found")
            except PlaywrightError as exc:
                if "Executable doesn't exist" in exc.message:
                    logger.error("Looks like Playwright was just installed or updated.")
                    logger.error("Please run the following command to download new browsers:")
                    logger.error("playwright install")
                else:
                    raise exc
            except KeyError:
                pass
            except Exception as exc:
                logger.error("Pixiv Login with Password Error", exc_info=exc)
            else:
                await self.cache.set_login_token(self.client.refresh_token)
        else:
            try:
                user = await self.client.login_with_token(login_token)
                await self.cache.set_login_token(self.client.refresh_token)
                logger.info("Pixiv Login with Token Success, Login User [%s]%s", user.id, user.name)
            except LoginError:
                logger.error("Pixiv Login Error")
            except PixivError as exc:
                logger.error("Pixiv Login Error", exc_info=exc)


class PixivWebAPI(BaseApi):
    def __init__(self):
        with open("config/pixiv.toml", "r", encoding="utf-8") as f:
            self.config = toml.load(f)
        login = self.config.get("login")
        cookie = SimpleCookie()
        cookie.load(login.get("cookies"))
        cookies = {key: morsel.value for key, morsel in cookie.items()}
        self.client = WebClient(cookies=cookies, lang="zh")

    async def initialize(self) -> None:
        try:
            result = await self.client.get_user_status()
            if result["is_logged_in"]:
                logger.info(
                    "Pixiv Web API Login with Cookies Success, Login User [%s]%s",
                    result["user_id"],
                    result["user_name"],
                )
            else:
                logger.warning("Pixiv Web API Cookies Expire")
        except PixNetBadRequest as exc:
            logger.error("Pixiv Web API Login Error", exc_info=exc)
