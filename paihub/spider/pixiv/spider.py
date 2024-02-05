import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set

from apscheduler.triggers.interval import IntervalTrigger
from async_pixiv.model.illust import Illust

from paihub.base import BaseSpider
from paihub.log import logger
from paihub.sites.pixiv.api import PixivMobileApi, PixivWebAPI
from paihub.sites.pixiv.cache import PixivCache
from paihub.sites.pixiv.entities import Pixiv as _Pixiv
from paihub.sites.pixiv.repositories import PixivRepository
from paihub.spider.pixiv.document import PixivSpiderDocument
from paihub.system.review.repositories import ReviewRepository


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
            self.search_job, IntervalTrigger(hours=12), next_run_time=datetime.now() + timedelta(hours=1)
        )
        self.application.scheduler.add_job(
            self.follow_job, IntervalTrigger(hours=1), next_run_time=datetime.now() + timedelta(hours=1)
        )
        # asyncio.create_task(self.follow_job())

    async def search_job(self):
        logger.info("正在进行Pixiv搜索爬虫任务")
        await self.web_search()
        await self.mobile_search()

    async def follow_job(self):
        logger.info("正在进行Pixiv关注爬虫任务")
        await self.follow_user()
        await self.get_web_follow()
        await self.get_mobile_follow()

    async def mobile_search(self):
        current_time = datetime.now()
        start_date = current_time.date()
        end_date = (current_time - timedelta(days=7)).date()
        offset: int = 0
        add_count: int = 0
        client = self.mobile_api.illust
        while True:
            search_result = await client.search("原神", offset=offset, start_date=start_date, end_date=end_date)
            count = len(search_result.illusts)
            if count == 0:
                logger.info("Pixiv Mobile Search 结束任务")
                break
            offset += count
            for illust in search_result.illusts:
                if self.filter_artwork(illust):
                    web_search_tags = await self.spider_document.get_web_search_tags(illust.id)
                    if web_search_tags is None:
                        continue
                    tags = web_search_tags.get("tags")
                    if tags is None:
                        continue
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
                    add_count += add_count
            logger.info("当前已经在搜索到 %s 张作品", offset)
            if offset > 5000:
                logger.info("Pixiv Mobile Search 结束任务")
                break
            await asyncio.sleep(random.randint(3, 10))

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
            illusts: "List[Dict]" = web_search_result.get("illusts")
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
            logger.info("Pixiv Web Search 正在进行搜索，当前搜索页数为 %s，当前已经获取到 %s, 还剩下 %s", page, count, total - count)
            await asyncio.sleep(random.randint(3, 10))
            page += 1

    async def follow_user(self):
        user_status = await self.web_api.client.get_user_status()
        offset: int = 0
        user_follows: Set[int] = set()
        while True:
            user_following = await self.web_api.client.get_user_following(user_status["user_id"], offset=offset)
            user_list = {int(user["userId"]) for user in user_following["users"]}
            user_follows.update(user_list)
            if len(user_list) < 24:
                break
        authors_id = await self.review_repository.get_filtered_status_counts("pixiv", 10, 0.9)
        need_follows = authors_id.difference(user_follows)
        for user_id in need_follows:
            await self.web_api.client.add_bookmark_user(user_id)
            logger.info("Pixiv Web Search 添加关注列表 %s", user_id)
            await asyncio.sleep(random.randint(3, 10))

    async def get_web_follow(self):
        current_time = datetime.now()
        end_date = current_time - timedelta(days=7)
        count: int = 0
        page: int = 1
        while True:
            web_search_result = await self.web_api.client.get_follow_latest(page=page)
            total = web_search_result.get("total")
            illusts: "List[Dict]" = web_search_result.get("thumbnails").get("illust")
            for illust in illusts:
                create_date = datetime.fromisoformat(illust["createDate"])
                if create_date < end_date:
                    logger.info("Pixiv Web Follow 结束任务")
                    return
                await self.spider_document.set_web_follow_data(illust)
            illusts_count = len(illusts)
            count += illusts_count
            if count >= total:
                break
            if illusts_count < 60:
                break
            logger.info("Pixiv Web Follow 正在进行搜索，当前搜索页数为 %s，当前已经获取到 %s, 还剩下 %s", page, count, total - count)
            await asyncio.sleep(random.randint(3, 10))
            page += 1

    async def get_mobile_follow(self):
        end_date = datetime.now() - timedelta(days=7)
        offset: int = 0
        add_count: int = 0
        client = self.mobile_api.illust
        while True:
            search_result = await client.follow()
            count = len(search_result.illusts)
            if count == 0:
                break
            offset += count
            for illust in search_result.illusts:
                if illust.create_date < end_date:
                    logger.info("Pixiv Mobile Follow 结束任务")
                    return
                web_follow_tags = await self.spider_document.get_web_follow_tags(illust.id)
                if web_follow_tags is None:
                    continue
                tags = web_follow_tags.get("tags")
                if tags is None:
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
                add_count += add_count
            logger.info("当前已经在搜索到 %s 张作品", offset)
            if offset > 1000:
                break
            await asyncio.sleep(random.randint(3, 10))

    @staticmethod
    def get_database_form_illust(illust: "Illust"):
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
    def filter_artwork(illust: "Illust"):
        # 移除 AI 作品
        if illust.ai_type == 2:
            return False
        days_hundred_fold = (time.time() - illust.create_date.timestamp()) / 24 / 60 / 60 * 100
        if 10 <= days_hundred_fold <= 300 and illust.total_bookmarks >= 700:
            if illust.total_bookmarks < 1000 - days_hundred_fold:
                return False
        else:
            if illust.total_bookmarks < 1000:
                return False
        return True
