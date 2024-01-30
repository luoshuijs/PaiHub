from typing import Optional

from paihub.base import BaseService

from paihub.system.review.cache import ReviewCache
from paihub.system.review.entities import Review, ReviewStatus
from paihub.system.review.ext import ReviewCallbackContext
from paihub.system.review.repositories import ReviewRepository
from paihub.system.sites.manager import SitesManager
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

    async def initialize_site_review(
        self, work_id: int, lines_per_page: int = 1000, create_by: Optional[int] = None
    ) -> int:
        count = 0
        work_rule = await self.work_rule_repository.get_by_work_id(work_id)
        if work_rule is None:
            raise RuntimeError
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
        site_service = self.sites_manager.get_site_by_site_id(review_data.web_id)
        return ReviewCallbackContext(review=review_data, site_service=site_service)

    async def get_review_count(self, work_id: int) -> int:
        return await self.review_cache.get_review_count(work_id)

    async def get_by_review_id(self, review_id: int) -> Review:
        return await self.review_repository.get(review_id)

    async def update_review(self, review: Review) -> Review:
        return await self.review_repository.update(review)
