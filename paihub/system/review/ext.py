from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from paihub.base import SiteService
    from paihub.entities.artwork import ArtWork
    from paihub.system.name_map.service import WorkTagFormatterService
    from paihub.system.review.entities import AutoReviewResult, Review, ReviewStatus
    from paihub.system.review.services import ReviewService


class ReviewCallbackContext:
    __slots__ = (
        "site_service",
        "review_service",
        "review",
        "tag_formatter",
    )

    def __init__(
        self,
        review: "Review",
        site_service: "SiteService",
        review_service: "ReviewService",
        tag_formatter: "WorkTagFormatterService",
    ):
        self.review = review
        self.site_service = site_service
        self.review_service = review_service
        self.tag_formatter = tag_formatter

    async def get_artwork(self) -> "ArtWork":
        """获取作品"""
        return await self.site_service.get_artwork(self.review.artwork_id)

    async def get_artwork_images(self) -> list[bytes]:
        """获取作品图片"""
        return await self.site_service.get_artwork_images(self.review.artwork_id)

    async def format_artwork_tags(self, artwork: "ArtWork", filter_character_tags: bool = False) -> str:
        """格式化作品标签"""
        if self.tag_formatter:
            return await self.tag_formatter.format_tags(artwork, filter_character_tags, self.review.work_id)
        # 降级处理：返回基本标签
        return " ".join(f"#{tag}" for tag in artwork.tags)

    async def try_auto_review(self) -> Optional["AutoReviewResult"]:
        """尝试自动审核"""
        return await self.review_service.try_auto_review(
            work_id=self.review.work_id, site_key=self.review.site_key, author_id=self.review.author_id
        )

    async def set_review_status(
        self, status: "ReviewStatus", auto: bool = False, update_by: int | None = None
    ) -> "Review":
        """设置审核作品"""
        self.review.status = status
        self.review.auto = auto
        if update_by is not None:
            self.review.update_by = update_by
        review = await self.review_service.review_repository.update(self.review)
        self.review = review
        return review

    @property
    def artwork_id(self) -> int:
        return self.review.artwork_id

    @property
    def work_id(self) -> int:
        return self.review.work_id

    @property
    def site_key(self) -> str:
        return self.review.site_key

    @property
    def review_id(self) -> int:
        return self.review.id
