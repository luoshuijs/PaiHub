from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from hashlib import sha256
from http.cookies import SimpleCookie
from secrets import token_urlsafe
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse

from apscheduler.triggers.interval import IntervalTrigger
from async_pixiv import PixivClient
from async_pixiv.const import APP_API_HOST
from async_pixiv.error import LoginError, PixivError
from async_pixiv.model import Illust, PixivModel, User
from async_pixiv.model.other.result import PageResult
from async_pixiv.utils.context import set_pixiv_client
from async_pixiv.utils.rate_limiter import RateLimiter
from pydantic import Field

from paihub.base import ApiService
from paihub.entities.config import TomlConfig
from paihub.log import logger
from paihub.sites.pixiv.cache import PixivCache
from pixnet.client.web import WebClient
from pixnet.errors import BadRequest as PixNetBadRequest

try:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None
    PlaywrightError = Exception

if TYPE_CHECKING:
    from async_pixiv.client.api._illust import IllustAPI
    from async_pixiv.client.api._novel import NovelAPI
    from async_pixiv.client.api._user import UserAPI, UserPreview
else:
    from async_pixiv.client.api._user import UserPreview

_REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
_LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
_LOGIN_VERIFY = "https://accounts.pixiv.net/ajax/login"
_AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"  # noqa: S105
PIXIV_APP_CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
PIXIV_APP_CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"  # noqa: S105


class UserIllustsResult(PageResult[Illust]):
    illusts: list[Illust]


class UserRelatedResult(PixivModel):
    users: list[UserPreview] = Field(alias="user_previews")


class IllustSearchResult(UserIllustsResult):
    pass


class PixivMobileApi(ApiService):
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
        self.illust: IllustAPI = self.client.ILLUST
        self.user: UserAPI = self.client.USER
        self.novel: NovelAPI = self.client.NOVEL

    async def initialize(self) -> None:
        await self.login()
        self.application.scheduler.add_job(
            self.login, IntervalTrigger(minutes=30), next_run_time=datetime.now() + timedelta(minutes=30)
        )

    async def login(self):
        login_token = await self.cache.get_login_token()
        if login_token is None:
            try:
                login: dict = self.config.get("login")
                username = login.get("username")
                password = login.get("password")
                headless = login.get("headless", True)
                proxy = login.get("proxy") if login.get("proxy") != "" else None
                if password != "" or username != "":
                    user = await self.login_with_pwd(username, password, proxy=proxy, headless=headless)
                    logger.info("Pixiv Mobile API Login with Password Success, Login User [%s]%s", user.id, user.name)
                else:
                    logger.warning("Pixiv Mobile API Login Token Not Found")
            except PlaywrightError as exc:
                if "Executable doesn't exist" in exc.message:
                    logger.error("Looks like Playwright was just installed or updated.")
                    logger.error("Please run the following command to download new browsers:")
                    logger.error("playwright install")
                else:
                    raise
            except Exception as exc:
                logger.error("Pixiv Login with Password Error", exc_info=exc)
            else:
                await self.cache.set_login_token(self.client.refresh_token)
        else:
            try:
                user = await self.client.login_with_token(login_token)
                await self.cache.set_login_token(self.client.refresh_token)
                logger.success("[blue]Pixiv[/blue] Login with Token Success, Login User [%s]%s", user.id, user.name)
            except LoginError:
                logger.error("[blue]Pixiv[/blue] Login Error")
            except PixivError as exc:
                logger.error("[blue]Pixiv[/blue] Login Error", exc_info=exc)

    async def user_follow_add(self, user_id: int | str, restrict: str = "public") -> dict[str, Any]:
        url = APP_API_HOST / "v1/user/follow/add"
        data = {"user_id": user_id, "restrict": restrict}
        response = await self.client.request("POST", url, data=data)
        return response.json()

    async def user_illusts(
        self,
        account_id: int | None = None,
        offset: int | None = None,
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

    async def illust_follow(self, offset: int | None = None) -> IllustSearchResult:
        response = await self.client.request_get(
            APP_API_HOST / "v2/illust/follow",
            params={"restrict": "public", "offset": offset},
        )
        data = response.json()
        illusts = [i for i in data.get("illusts", []) if i.get("title") is not None]
        if len(illusts) != 0:
            data["illusts"] = illusts
        with set_pixiv_client(self.client):
            return IllustSearchResult.model_validate(data)

    @staticmethod
    def oauth_pkce() -> tuple[str, str]:
        verifier = token_urlsafe(32)
        challenge = urlsafe_b64encode(sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
        return verifier, challenge

    async def login_with_pwd(
        self, username: str, password: str, proxy: str | None = None, headless: bool | None = None
    ) -> User:
        if async_playwright is None:
            raise RuntimeError("Please install 'playwright'.")

        async with async_playwright() as playwright:
            if proxy is not None:
                browser = await playwright.chromium.launch(proxy={"server": proxy}, headless=headless)
            else:
                browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context()
            api_request_context = context.request
            page = await context.new_page()

            # 访问登录页面
            code_verifier, code_challenge = self.oauth_pkce()
            await page.goto(
                urlparse(_LOGIN_URL)
                ._replace(
                    query=urlencode(
                        {
                            "code_challenge": code_challenge,
                            "code_challenge_method": "S256",
                            "client": "pixiv-android",
                        }
                    )
                )
                .geturl(),
                timeout=0,
            )

            # 输入用户名与密码
            await page.locator('input[autocomplete="username"]').fill(username)
            password_input = page.locator('input[type="password"]')
            await password_input.fill(password)

            # 点击登录按钮
            login_form = password_input.locator("xpath=ancestor::form")  # 从密码输入框导航到外层的 form 元素
            login_button = login_form.locator('button, input[type="submit"]')  # 从 form 元素内部定位到登录按钮

            # 验证登录
            async with page.expect_response(f"{_LOGIN_VERIFY}*") as future:
                await login_button.click()
                value = await future.value
                await value.finished()
                if value.ok:
                    logger.info("登录成功")
                else:
                    response_json = value.json()
                    logger.info("登录错误 %s", response_json["body"]["errors"])

            # 获取code
            async with page.expect_request(f"{_REDIRECT_URI}*") as request:
                url = urlparse((await request.value).url)
            code = parse_qs(url.query)["code"][0]

            # 获取token
            response = await api_request_context.post(
                _AUTH_TOKEN_URL,
                form={
                    "client_id": PIXIV_APP_CLIENT_ID,
                    "client_secret": PIXIV_APP_CLIENT_SECRET,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "include_policy": "true",
                    "redirect_uri": _REDIRECT_URI,
                },
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Host": "oauth.secure.pixiv.net",
                },
                timeout=0,
            )
            data = await response.json()
            await browser.close()
        self.client.access_token = data["access_token"]
        self.client.refresh_token = data["refresh_token"]
        with set_pixiv_client(self):
            self.client.account = User.model_validate(data["user"])
        return self.client.account


class PixivWebAPI(ApiService):
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
