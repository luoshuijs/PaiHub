from typing import Optional, List

from paihub.base import BaseService
from paihub.system.review.cache import ReviewCache
from paihub.system.review.entities import Review, ReviewStatus, AutoReviewResult
from paihub.system.review.ext import ReviewCallbackContext
from paihub.system.review.repositories import ReviewRepository
from paihub.system.sites.manager import SitesManager
from paihub.system.work.error import WorkRuleNotFound
from paihub.system.work.repositories import WorkRepository, WorkRuleRepository


class ReviewService(BaseService):
    def __init__(
        self,
        work_repository: WorkRepository,
        work_rule_repository: WorkRuleRepository,
        sites_manager: SitesManager,
        review_repository: ReviewRepository,
        review_cache: ReviewCache,
    ):
        self.review_repository = review_repository
        self.work_repository = work_repository
        self.sites_manager = sites_manager
        self.work_rule_repository = work_rule_repository
        self.review_cache = review_cache
        # todo : 这里的全部操作都属于线程不安全 后期需要加锁运行

    @property
    def repository(self):
        return self.review_repository

    async def initialize_site_review(
        self, work_id: int, lines_per_page: int = 10000, create_by: Optional[int] = None
    ) -> int:
        count = 0
        work_rule = await self.work_rule_repository.get_by_work_id(work_id)
        if work_rule is None:
            raise WorkRuleNotFound
        for s in self.sites_manager.get_all_sites():
            count += await s.initialize_review(
                work_id,
                search_text=work_rule.search_text,
                is_pattern=work_rule.is_pattern,
                lines_per_page=lines_per_page,
                create_by=create_by,
            )
        return count

    async def get_review(self, work_id: int) -> int:
        count = 0
        page_number = 1
        while True:
            reviews_id = await self.review_repository.get_by_status(
                work_id, status=ReviewStatus.WAIT, page_number=page_number
            )
            if len(reviews_id) == 0:
                break
            count += await self.review_cache.set_pending_review(reviews_id, work_id)
            page_number += 1
        return count

    async def review_next(self, work_id: int) -> Optional[ReviewCallbackContext]:
        review_id = await self.review_cache.get_pending_review(work_id)
        if review_id is None:
            return None
        review_data = await self.review_repository.get(int(review_id))
        site_service = self.sites_manager.get_site_by_site_key(review_data.site_key)
        return ReviewCallbackContext(review=review_data, site_service=site_service, review_service=self)

    async def get_review_count(self, work_id: int) -> int:
        return await self.review_cache.get_review_count(work_id)

    async def get_by_review_id(self, review_id: int) -> Optional[Review]:
        return await self.review_repository.get(review_id)

    async def update_review(self, review: Review) -> Review:
        return await self.review_repository.update(review)

    async def remove_review(self, review: Review) -> Review:
        return await self.review_repository.remove(review)

    async def move_review(self, review: Review, target_work_id: int, update_by: int):
        review.set_move(update_by, target_work_id)
        review = await self.review_repository.update(review)
        move = review.copy()
        move.work_id = target_work_id
        move.id = None
        move.create_by = update_by
        move.create_time = None
        move.update_by = None
        move.update_time = None
        await self.review_repository.add(move)
        await self.review_repository.update(review)

    async def try_auto_review(self, work_id: int, site_key: str, author_id: int) -> Optional[AutoReviewResult]:
        statistics = await self.review_repository.get_by_status_statistics(
            work_id, site_key=site_key, author_id=author_id
        )
        if statistics.already >= 3:
            if statistics.pass_count / statistics.already >= 0.5:
                return AutoReviewResult(status=True, statistics=statistics)
            return AutoReviewResult(status=False, statistics=statistics)
        return None

    async def get_review_by_artwork_id(self, artwork_id: int) -> List[Review]:
        return await self.review_repository.get_review_by_artwork_id(artwork_id)

    async def set_send_review(
        self, work_id: int, site_key: str, artwork_id: int, create_by: int, status: ReviewStatus = ReviewStatus.PASS
    ):
        review_info = await self.review_repository.get_review(work_id, site_key, artwork_id)
        if review_info is None:
            instance = Review(
                work_id=work_id, site_key=site_key, artwork_id=artwork_id, status=status, create_by=create_by
            )
            await self.review_repository.add(instance)
            return await self.review_repository.get_review(work_id, site_key, artwork_id, status)
        review_info.status = status
        review_info.update_by = create_by
        return await self.review_repository.update(review_info)
