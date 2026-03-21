from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paihub.base import SiteService
    from paihub.entities.artwork import ArtWork
    from paihub.system.name_map.service import WorkTagFormatterService
    from paihub.system.push.services import PushService


class PushCallbackContext:
    __slots__ = (
        "site_service",
        "push_service",
        "artwork_id",
        "work_id",
        "channel_id",
        "review_id",
        "tag_formatter",
    )

    def __init__(
        self,
        work_id: int,
        channel_id: int,
        artwork_id: int,
        review_id: int,
        site_service: "SiteService",
        push_service: "PushService",
        tag_formatter: "WorkTagFormatterService",
    ):
        self.artwork_id = artwork_id
        self.site_service = site_service
        self.push_service = push_service
        self.work_id = work_id
        self.channel_id = channel_id
        self.review_id = review_id
        self.tag_formatter = tag_formatter

    async def get_artwork(self) -> "ArtWork":
        return await self.site_service.get_artwork(self.artwork_id)

    async def get_artwork_images(self) -> list[bytes]:
        return await self.site_service.get_artwork_images(self.artwork_id)

    async def format_artwork_tags(self, artwork: "ArtWork", filter_character_tags: bool = False) -> str:
        """格式化作品标签"""
        if self.tag_formatter:
            return await self.tag_formatter.format_tags(artwork, filter_character_tags, self.work_id)
        # 降级处理：返回基本标签
        return " ".join(f"#{tag}" for tag in artwork.tags)

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
