from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paihub.base import SiteService
    from paihub.entities.artwork import ArtWork
    from paihub.system.push.services import PushService


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
        site_service: "SiteService",
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

    async def get_artwork_images(self) -> list[bytes]:
        return await self.site_service.get_artwork_images(self.artwork_id)

    async def set_push(self, message_id: int | None = None, create_by: int | None = None, status: bool = True):
        await self.push_service.add_push(
            review_id=self.review_id,
            channel_id=self.channel_id,
            message_id=message_id,
            status=status,
            create_by=create_by,
        )

    async def undo_push(self) -> int:
        return await self.push_service.undo_push(self.work_id, self.artwork_id)
