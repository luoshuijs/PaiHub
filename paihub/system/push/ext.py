from typing import TYPE_CHECKING, List, Optional


if TYPE_CHECKING:
    from paihub.system.push.services import PushService
    from paihub.entities.artwork import ArtWork
    from paihub.base import BaseSiteService


class PushCallbackContext:
    __slots__ = (
        "site_service",
        "push_service",
        "artwork_id",
        "work_id",
        "channel_id",
        "review_id",
    )

    def __init__(
        self,
        work_id: int,
        channel_id: int,
        artwork_id: int,
        review_id: int,
        site_service: "BaseSiteService",
        push_service: "PushService",
    ):
        self.artwork_id = artwork_id
        self.site_service = site_service
        self.push_service = push_service
        self.work_id = work_id
        self.channel_id = channel_id
        self.review_id = review_id

    async def get_artwork(self) -> "ArtWork":
        return await self.site_service.get_artwork(self.artwork_id)

    async def get_artwork_images(self) -> List[bytes]:
        return await self.site_service.get_artwork_images(self.artwork_id)

    async def set_push(self, message_id: Optional[int] = None, create_by: Optional[int] = None, status: bool = True):
        await self.push_service.add_push(
            review_id=self.review_id,
            channel_id=self.channel_id,
            message_id=message_id,
            status=status,
            create_by=create_by,
        )
