import asyncio
import time
from datetime import datetime, timedelta

from async_pixiv.model.illust import Illust

from paihub.base import BaseSpider
from paihub.sites.pixiv.api import PixivApi
from paihub.sites.pixiv.cache import PixivCache
from paihub.sites.pixiv.entities import Pixiv as _Pixiv
from paihub.sites.pixiv.repositories import PixivRepository
from paihub.system.review.repositories import ReviewRepository


class PixivSpider(BaseSpider):
    def __init__(
        self, cache: PixivCache, repository: PixivRepository, api: PixivApi, review_repository: ReviewRepository
    ):
        self.cache = cache
        self.repository = repository
        self.api = api
        self.review_repository = review_repository

    def add_jobs(self) -> None:
        self.application.scheduler.add_job(self.run, "cron", hour=3, minute=0)

    async def run(self):
        await self.search()

    async def search(self):
        current_time = datetime.now()
        start_date = current_time.date()
        end_date = (current_time - timedelta(days=30)).date()
        offset: int = 0
        client = self.api.illust
        while True:
            search_result = await client.search("原神", offset=offset, start_date=start_date, end_date=end_date)
            count = len(search_result.illusts)
            if count == 0:
                break
            offset += count
            for illust in search_result.illusts:
                if self.filter_artwork(illust):
                    await self.repository.add(self.get_database_form_illust(illust))

            await asyncio.sleep(count)

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
        if illust.ai_type != 0:
            return False
        days_hundred_fold = (time.time() - illust.create_date.timestamp()) / 24 / 60 / 60 * 100
        if 10 <= days_hundred_fold <= 300 and illust.total_bookmarks >= 700:
            if illust.total_bookmarks < 1000 - days_hundred_fold:
                return False
        else:
            if illust.total_bookmarks < 1000:
                return False
        return True
