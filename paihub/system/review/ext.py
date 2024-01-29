from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from paihub.entities.artwork import ArtWork
    from paihub.base import BaseSiteService
    from paihub.system.review.entities import Review


class ReviewCallbackContext:
    __slots__ = (
        "site_service",
        "review",
    )

    def __init__(self, review: "Review", site_service: "BaseSiteService"):
        self.review = review
        self.site_service = site_service

    async def get_artwork(self) -> "ArtWork":
        return await self.site_service.get_artwork(self.review.artwork_id)

    async def get_artwork_images(self) -> List[bytes]:
        return await self.site_service.get_artwork_images(self.review.artwork_id)

    @property
    def artwork_id(self) -> int:
        return self.review.artwork_id

    @property
    def work_id(self) -> int:
        return self.review.work_id

    @property
    def web_id(self) -> int:
        return self.review.web_id

    @property
    def review_id(self) -> int:
        return self.review.id
