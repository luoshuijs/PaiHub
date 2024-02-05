import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict

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
        self.application.scheduler.add_job(self.run, "cron", hour=3, minute=0)
        asyncio.create_task(self.run())

    async def run(self):
        logger.info("正在进行Pixiv爬虫任务")
        await self.web_search()
        await self.mobile_search()

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
                        tags=[tag for tag in web_search_tags.get("tags")],
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
                break
            if illusts_count == 0:
                break
            logger.info("Pixiv Web Search 正在进行搜索，当前搜索页数为 %s，当前已经获取到 %s, 还剩下 %s", page, count, total - count)
            await asyncio.sleep(random.randint(3, 10))
            page += 1

    async def set(self):
        authors_id = await self.review_repository.get_filtered_status_counts("pixiv", 10, 0.9)
        pass

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
