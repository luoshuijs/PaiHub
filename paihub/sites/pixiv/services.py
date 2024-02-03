import asyncio
from typing import Optional, List

from async_pixiv.error import PixivError
from async_pixiv.model.illust import IllustType

from paihub.base import BaseSiteService
from paihub.entities.artwork import ImageType
from paihub.error import BadRequest
from paihub.log import logger
from paihub.sites.pixiv.api import PixivApi
from paihub.sites.pixiv.cache import PixivReviewCache, PixivCache
from paihub.sites.pixiv.entities import PixivArtWork, PixivAuthor
from paihub.sites.pixiv.repositories import PixivRepository
from paihub.sites.pixiv.utils import compiled_patterns
from paihub.system.review.repositories import ReviewRepository


class PixivSitesService(BaseSiteService):
    site_name = "Pixiv"
    site_key = "pixiv"

    def __init__(
        self,
        repository: PixivRepository,
        review_cache: PixivReviewCache,
        review_repository: ReviewRepository,
        cache: PixivCache,
        api: PixivApi,
    ):
        self.repository = repository
        self.review_cache = review_cache
        self.review_repository = review_repository
        self.cache = cache
        self.api = api
        self.loop = asyncio.get_event_loop()

    async def initialize_review(
        self,
        work_id: int,
        search_text: str,
        is_pattern: bool,
        lines_per_page: int = 10000,
        create_by: Optional[int] = None,
    ) -> int:
        count = 0
        page_number = 1
        while True:
            start_time = self.loop.time()
            artworks_id = await self.repository.get_artworks_by_tags(
                search_text, is_pattern, page_number, lines_per_page
            )
            logger.info("从Pixiv数据库获取匹配内容使用了 %s 秒", self.loop.time() - start_time)
            start_time = self.loop.time()
            if len(artworks_id) == 0:
                break
            count += await self.review_cache.set_database_artwork_ids(artworks_id)
            page_number += 1
            logger.info("从存储到Redis中使用了 %s 秒", self.loop.time() - start_time)
        page_number = 1
        start_time = self.loop.time()
        while True:
            artworks_id = await self.review_repository.get_artwork_id_by_work_and_web(
                work_id, site_key=self.site_key, page_number=page_number, lines_per_page=lines_per_page
            )
            if len(artworks_id) == 0:
                break
            count += await self.review_cache.set_already_review_artwork_ids(artworks_id)
            page_number += 1
        logger.info("从审核库获取匹配内容使用了 %s 秒", self.loop.time() - start_time)
        difference = await self.review_cache.get_ready_review_artwork_ids()
        for artwork_id in difference:
            await self.repository.add_review_form_pixiv(
                work_id=work_id, artwork_id=int(artwork_id), create_by=create_by
            )
        return len(difference)

    async def get_artwork(self, artwork_id: int) -> PixivArtWork:
        try:
            illust_detail = await self.api.illust.detail(artwork_id)
        except PixivError as exc:
            raise BadRequest from exc
        auther = PixivAuthor(auther_id=illust_detail.illust.user.id, name=illust_detail.illust.user.name)
        art_work = PixivArtWork(
            artwork_id=artwork_id,
            title=illust_detail.illust.title,
            create_time=illust_detail.illust.create_date,
            author=auther,
            tags=[i.name for i in illust_detail.illust.tags],
            image_type=ImageType.DYNAMIC if illust_detail.illust.type == IllustType.ugoira else ImageType.STATIC,
        )
        return art_work

    async def get_artwork_images(self, artwork_id: int) -> List[bytes]:
        # 对于动态图片作品需要 ffmpeg 转换
        artwork = (await self.api.illust.detail(artwork_id)).illust
        if artwork.type == IllustType.ugoira:
            return await self.api.illust.download_ugoira(artwork_id, type="mp4")
        if not artwork.meta_pages:
            return [await self.api.client.download(str(artwork.image_urls.large))]
        else:
            result: List[bytes] = []
            for meta_page in artwork.meta_pages:
                result.append(await self.api.client.download(str(meta_page.image_urls.large)))
            return result

    @staticmethod
    def extract(text: str) -> Optional[int]:
        for pattern in compiled_patterns:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None
