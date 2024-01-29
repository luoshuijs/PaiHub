from typing import Optional, List

import toml
from async_pixiv import PixivClient
from async_pixiv.error import LoginError, PixivError
from playwright.async_api import Error as PlaywrightError

from paihub.base import BaseSiteService
from paihub.entities.artwork import ArtWork
from paihub.entities.author import Auther
from paihub.error import BadRequest
from paihub.log import logger
from paihub.sites.pixiv.cache import PixivReviewCache, PixivCache
from paihub.sites.pixiv.repositories import PixivRepository
from paihub.sites.pixiv.utils import compiled_patterns
from paihub.system.review.repositories import ReviewRepository
from paihub.system.sites.repositories import SitesRepository


class PixivSitesService(BaseSiteService):
    site_name = "pixiv"

    def __init__(
        self,
        repository: PixivRepository,
        review_cache: PixivReviewCache,
        sites_repository: SitesRepository,
        review_repository: ReviewRepository,
        cache: PixivCache,
    ):
        self.repository = repository
        self.review_cache = review_cache
        self.sites_repository = sites_repository
        self.review_repository = review_repository
        self.web_id: Optional[int] = None
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

    async def initialize(self) -> None:
        login_token = await self.cache.get_login_token()
        if login_token is None:
            try:
                username = self.config["login"]["username"]
                password = self.config["login"]["password"]
                proxy = self.config["login"]["proxy"] if self.config["login"]["proxy"] != "" else None
                if password != "" or username != "":
                    user = await self.client.login_with_pwd(username, password, proxy=proxy)
                    logger.info("Pixiv Login with Password Success, Login User [%s]%s", user.id, user.name)
                else:
                    logger.warning("Pixiv Login Token Not Found")
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
        web_info = await self.sites_repository.get_by_key_name(self.site_name)
        self.web_id = web_info.id

    async def initialize_review(
        self,
        work_id: int,
        search_text: str,
        is_pattern: bool,
        lines_per_page: int = 1000,
        create_by: Optional[int] = None,
    ) -> int:
        # todo: 初始化 Review 从数据库放进 Redis 中进行比较
        count = 0
        page_number = 1
        while True:
            artworks_id = await self.repository.get_artworks_by_tags(
                search_text, is_pattern, page_number, lines_per_page
            )
            if len(artworks_id) == 0:
                break
            count += await self.review_cache.set_database_artwork_ids(artworks_id)
            page_number += 1
        page_number = 1
        while True:
            artworks_id = await self.review_repository.get_artwork_id_by_work_and_web(
                work_id, self.web_id, page_number=page_number
            )
            if len(artworks_id) == 0:
                break
            count += await self.review_cache.set_already_review_artwork_ids(artworks_id)
            page_number += 1
        difference = await self.review_cache.get_ready_review_artwork_ids()
        await self.review_repository.set_reviews_id(
            work_id=work_id, web_id=self.web_id, reviews_id=difference, create_by=create_by
        )
        return len(difference)

    async def get_artwork(self, artwork_id: int) -> ArtWork:
        try:
            illust_detail = await self.client.ILLUST.detail(artwork_id)
        except PixivError as exc:
            raise BadRequest from exc
        auther = Auther(auther_id=illust_detail.illust.user.id, name=illust_detail.illust.user.name)
        art_work = ArtWork(
            artwork_id=artwork_id,
            title=illust_detail.illust.title,
            create_time=illust_detail.illust.create_date,
            auther=auther,
        )
        return art_work

    async def get_artwork_images(self, artwork_id: int) -> List[bytes]:
        # todo : 对于动态图片作品需要 ffmpeg 转换
        return await self.client.ILLUST.download(artwork_id)

    @staticmethod
    def extract(text: str) -> Optional[int]:
        for pattern in compiled_patterns:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None
