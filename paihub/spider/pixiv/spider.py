import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from async_pixiv.error import ApiError, NotExistError

from paihub.base import BaseSpider
from paihub.log import Logger, logger
from paihub.sites.pixiv.api import PixivMobileApi, PixivWebAPI
from paihub.sites.pixiv.cache import PixivCache
from paihub.sites.pixiv.entities import Pixiv as _Pixiv
from paihub.sites.pixiv.repositories import PixivRepository
from paihub.spider.pixiv.document import PixivSpiderDocument
from paihub.system.review.repositories import ReviewRepository

if TYPE_CHECKING:
    from async_pixiv.model.illust import Illust

_logger = Logger("Pixiv Spider", filename="pixiv_spider.log")


class PixivSpider(BaseSpider):
    def __init__(
        self,
        cache: PixivCache,
        repository: PixivRepository,
        mobile_api: PixivMobileApi,
        review_repository: ReviewRepository,
        spider_document: PixivSpiderDocument,
        web_api: PixivWebAPI,
    ):
        self.cache = cache
        self.repository = repository
        self.mobile_api = mobile_api
        self.review_repository = review_repository
        self.spider_document = spider_document
        self.web_api = web_api

    def add_jobs(self) -> None:
        self.application.scheduler.add_job(
            self.search_job, IntervalTrigger(hours=12), next_run_time=datetime.now() + timedelta(hours=12)
        )
        self.application.scheduler.add_job(
            self.follow_job, IntervalTrigger(hours=1), next_run_time=datetime.now() + timedelta(hours=1)
        )
        self.application.scheduler.add_job(
            self.follow_user_job, CronTrigger(hour=4, minute=0), next_run_time=datetime.now()
        )
        self.application.scheduler.add_job(
            self.fetch_artwork, CronTrigger(day=1, hour=0, minute=0), next_run_time=datetime.now()
        )
        # 调试使用 asyncio.create_task(self.fetch_artwork)

    async def search_job(self):
        logger.info("正在进行 Pixiv 搜索爬虫任务")
        await self.web_search()
        await self.mobile_search()

    async def follow_user_job(self):
        logger.info("正在进行 Pixiv 关注用户爬虫任务")
        await self.follow_user()

    async def follow_job(self):
        logger.info("正在进行 Pixiv 关注作品爬虫任务")
        await self.get_web_follow()
        await self.get_mobile_follow()

    async def fetch_artwork(self):
        logger.info("正在进行 Pixiv 关注作品同步任务")
        await self.fetch_user_artwork()

    async def mobile_search(self):
        current_time = datetime.now()
        start_date = current_time.date()
        end_date = (current_time - timedelta(days=7)).date()
        offset: int = 0
        add_count: int = 0
        client = self.mobile_api.illust
        while True:
            search_result = await client.search("原神", offset=offset, start_date=start_date, end_date=end_date)
            count = len(search_result.previews)
            if count == 0:
                logger.info("Pixiv Mobile Search 结束任务")
                break
            offset += count
            for illust in search_result.previews:
                if self.filter_artwork(illust):
                    web_search_tags = await self.spider_document.get_web_search_tags(illust.id)
                    if web_search_tags is None:
                        continue
                    tags = web_search_tags.get("tags")
                    if tags is None:
                        continue
                    _logger.info(
                        "Pixiv Search Artwork 正在保存作品 IllustId[%s] Bookmarks[%s]",
                        illust.id,
                        illust.total_bookmarks,
                    )
                    instance = _Pixiv(
                        id=illust.id,
                        title=illust.title,
                        tags=web_search_tags.get("tags"),
                        love_count=illust.total_bookmarks,
                        like_count=illust.total_bookmarks,
                        view_count=illust.total_view,
                        author_id=illust.user.id,
                        create_time=illust.create_date,
                    )
                    await self.repository.merge(instance)
                    add_count += 1
            logger.info("当前已经搜索到 %s 张作品 已经添加数据库 %s 张作品", offset, add_count)
            if offset > 5000:
                logger.info("Pixiv Mobile Search 结束任务")
                break
            await asyncio.sleep(random.randint(10, 30))  # noqa: S311

    async def web_search(self):
        current_time = datetime.now()
        start_date = current_time.date()
        end_date = (current_time - timedelta(days=7)).date()
        count: int = 0
        page: int = 1
        while True:
            web_search_result = await self.web_api.client.search_illusts(
                word="原神", start_date=start_date, end_date=end_date, page=page
            )
            total = web_search_result.get("total")
            illusts: list[dict] = web_search_result.get("illusts")
            for illust in illusts:
                if illust.get("ai_type") == 2:
                    continue
                await self.spider_document.set_web_search_data(illust)
            illusts_count = len(illusts)
            count += illusts_count
            if count >= total:
                logger.info("Pixiv Web Search 结束任务")
                break
            if illusts_count < 35:
                logger.info("Pixiv Web Search 结束任务")
                break
            logger.info(
                "Pixiv Web Search 正在进行搜索，当前搜索页数为 %s，当前已经获取到 %s, 还剩下 %s",
                page,
                count,
                total - count,
            )
            await asyncio.sleep(random.randint(10, 30))  # noqa: S311
            page += 1

    async def follow_user(self):
        logger.info("正在获取关注列表")
        user_status = await self.web_api.client.get_user_status()
        offset: int = 0
        user_follows: set[int] = set()
        while True:
            user_following = await self.web_api.client.get_user_following(user_status["user_id"], offset=offset)
            user_list = {int(user["userId"]) for user in user_following["users"]}
            user_follows.update(user_list)
            offset += len(user_list)
            logger.info("已经获取到关注列表第 %s 个", offset)
            if len(user_list) < 24:
                break
            await asyncio.sleep(random.randint(10, 30))  # noqa: S311
        authors_id = await self.review_repository.get_filtered_status_counts("pixiv", 10, 0.8)
        need_follows = authors_id.difference(user_follows)
        logger.info("目前需要新添关注 %s 个", len(need_follows))
        for user_id in need_follows:
            if await self.spider_document.if_user_not_exist(user_id):
                continue
            try:
                await self.mobile_api.user_follow_add(user_id)
                logger.info("Pixiv Spider Follow 添加关注列表 %s", user_id)
            except NotExistError:
                logger.info("添加 %s 关注列表失败 用户不存在", user_id)
                await self.spider_document.set_not_exist_user(user_id)
            except ApiError as exc:
                logger.info("添加 %s 关注列表失败 %s", user_id, str(exc.message))
                await self.spider_document.set_not_exist_user(user_id)
            await asyncio.sleep(30)

    async def fetch_user_artwork(self):
        authors_id = await self.review_repository.get_filtered_status_counts("pixiv", 10, 0.8)
        fetch_user = await self.spider_document.get_all_artwork_fetch_user()
        need_fetch_users = authors_id.difference(fetch_user)
        for user_id in list(need_fetch_users)[:2]:
            offset = 0
            while True:
                try:
                    user_illusts = await self.mobile_api.user_illusts(user_id, offset=offset)
                    # Original code : await self.mobile_api.user.illusts(user_id, type="illust", offset=offset)
                except NotExistError:
                    await self.spider_document.set_not_exist_user(user_id)
                    await asyncio.sleep(3)
                    break
                except ApiError as exc:
                    _logger.error("获取作者作品列表失败", exc_info=exc)
                    await self.spider_document.set_not_exist_user(user_id)
                    await asyncio.sleep(3)
                    break
                count = len(user_illusts.illusts)
                if count == 0:
                    break
                for illust in user_illusts.illusts:
                    await self.repository.merge(self.parse_mobile_details_to_database(illust))
                    _logger.info("Pixiv Fetch Artwork 正在保存作品 Id[%s]", illust.id)
                offset += count
                _logger.info("Pixiv Fetch Artwork 正在搜索用户 UserId[%s] 当前搜索 Offset[%s]", user_id, offset)
                if user_illusts.next_url is None:
                    break
                await asyncio.sleep(random.randint(10, 30))  # noqa: S311
            await self.spider_document.set_artwork_fetch_status(user_id)

    async def get_web_follow(self):
        current_time = datetime.now()
        end_date = current_time - timedelta(days=2)
        count: int = 0
        page: int = 1
        while True:
            web_search_result = await self.web_api.client.get_follow_latest(page=page)
            illusts: list[dict] = web_search_result.get("thumbnails").get("illust")
            for illust in illusts:
                create_date = datetime.fromisoformat(illust["createDate"]).replace(tzinfo=None)
                if create_date < end_date:
                    logger.info("Pixiv Spider User Follow 结束任务")
                    return
                await self.spider_document.set_web_follow_data(illust)
            illusts_count = len(illusts)
            count += illusts_count
            if illusts_count < 60:
                logger.info("Pixiv Spider User Follow 结束任务")
                break
            logger.info("Pixiv Spider User Follow 正在获取列表，当前列表页数为 %s，当前已经获取到 %s", page, count)
            await asyncio.sleep(random.randint(10, 30))  # noqa: S311
            page += 1

    async def get_mobile_follow(self):
        end_date = datetime.now() - timedelta(days=1)
        offset: int = 0
        add_count: int = 0
        client = self.mobile_api
        # Original code : client = self.mobile_api.illust
        while True:
            search_result = await client.illust_follow()
            # Original code : search_result = await client.follow()
            count = len(search_result.illusts)
            if count == 0:
                break
            offset += count
            for illust in search_result.illusts:
                if illust.create_date.replace(tzinfo=None) < end_date:
                    logger.info("Pixiv Spider Mobile Follow 结束任务 已经添加 %s 张作品到数据库", add_count)
                    return
                web_follow_tags = await self.spider_document.get_web_follow_tags(illust.id)
                if web_follow_tags is None:
                    continue
                tags: list[str] | None = web_follow_tags.get("tags")
                if tags is None:
                    logger.warning("作品 Pixiv[%s] Tags 为空", illust.id)
                    continue
                instance = _Pixiv(
                    id=illust.id,
                    title=illust.title,
                    tags=web_follow_tags.get("tags"),
                    love_count=illust.total_bookmarks,
                    like_count=illust.total_bookmarks,
                    view_count=illust.total_view,
                    author_id=illust.user.id,
                    create_time=illust.create_date,
                )
                await self.repository.merge(instance)
                add_count += 1
            logger.info("当前已经获取到 %s 张作品 已经添加 %s 张作品到数据库", offset, add_count)
            if offset > 1000:
                break
            await asyncio.sleep(random.randint(10, 30))  # noqa: S311

    @staticmethod
    def parse_mobile_details_to_database(illust: "Illust"):
        return _Pixiv(
            id=illust.id,
            title=illust.title,
            tags=[tag.name for tag in illust.tags],
            love_count=illust.total_bookmarks,
            like_count=illust.total_bookmarks,
            view_count=illust.total_view,
            author_id=illust.user.id,
            create_time=illust.create_date,
        )

    @staticmethod
    def parse_web_details_to_database(data: dict[str, Any]):
        illust_details: dict[str, Any] = data["illust_details"]
        tags: list[str] = illust_details.get("tags")
        alt: str = illust_details.get("alt")
        artwork_id = int(illust_details.get("id"))
        user_id = int(illust_details.get("user_id"))
        rating_view = illust_details.get("rating_view", 0)
        rating_count = illust_details.get("rating_count", 0)
        bookmark_user_total = illust_details.get("bookmark_user_total", 0)
        upload_timestamp = illust_details.get("upload_timestamp")
        return _Pixiv(
            id=artwork_id,
            title=alt,
            tags=tags,
            love_count=bookmark_user_total,
            like_count=rating_count,
            view_count=rating_view,
            author_id=user_id,
            create_time=datetime.fromtimestamp(upload_timestamp),
        )

    @staticmethod
    def filter_artwork(illust: "Illust"):
        if illust.ai_type == 2:  # 移除 AI 作品
            return False
        tags = [tag.name for tag in illust.tags]
        if "R-18" in tags:
            return False
        if illust.total_bookmarks >= 1000:
            return True
        days_hundred_fold = (time.time() - illust.create_date.timestamp()) / 24 / 60 / 60 * 100
        return 50 < days_hundred_fold < 1000 and illust.total_bookmarks > days_hundred_fold

    @staticmethod
    def filter_mobile_artwork(data: dict[str, Any]):
        illust_details: dict[str, Any] = data["illust_details"]
        upload_timestamp = illust_details.get("upload_timestamp")
        bookmark_user_total = illust_details.get("bookmark_user_total", 0)
        ai_type = illust_details.get("ai_type", 0)
        if ai_type == 2:
            return False
        days_hundred_fold = (time.time() - upload_timestamp.timestamp()) / 24 / 60 / 60 * 100
        if 10 <= days_hundred_fold <= 300 and bookmark_user_total >= 700:
            if bookmark_user_total < 1000 - days_hundred_fold:
                return False
        elif bookmark_user_total < 1000:
            return False
        return True
