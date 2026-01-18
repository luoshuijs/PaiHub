from paihub.base import Service
from paihub.log import logger
from paihub.system.push.cache import PushCache
from paihub.system.push.entities import Push
from paihub.system.push.ext import PushCallbackContext
from paihub.system.push.repositories import PushRepository
from paihub.system.review.entities import ReviewStatus
from paihub.system.review.repositories import ReviewRepository
from paihub.system.sites.manager import SitesManager
from paihub.system.work.repositories import WorkChannelRepository


class PushService(Service):
    def __init__(
        self,
        sites_manager: SitesManager,
        push_repository: PushRepository,
        push_cache: PushCache,
        review_repository: ReviewRepository,
        work_channel_repository: WorkChannelRepository,
    ):
        self.push_repository = push_repository
        self.push_cache = push_cache
        self.sites_manager = sites_manager
        self.review_repository = review_repository
        self.work_channel_repository = work_channel_repository

    async def get_push(self, work_id: int) -> int:
        reviews_id = await self.push_repository.get_review_id_by_push(work_id)
        return await self.push_cache.set_pending_push(work_id, reviews_id)

    async def get_push_count(self, work_id: int) -> int:
        return await self.push_cache.get_push_count(work_id)

    async def get_next_push(self, work_id: int) -> PushCallbackContext | None:
        review_id = await self.push_cache.get_pending_push(work_id)
        if review_id is None:
            return None
        review_data = await self.review_repository.get_by_id(int(review_id))
        site_service = self.sites_manager.get_site_by_site_key(review_data.site_key)
        work_channel = await self.work_channel_repository.get_by_work_id(work_id)
        return PushCallbackContext(
            review_id=review_data.id,
            work_id=work_id,
            channel_id=work_channel.channel_id,
            artwork_id=review_data.artwork_id,
            site_service=site_service,
            push_service=self,
        )

    async def get_next_push_with_validation(self, work_id: int) -> PushCallbackContext | None:
        """从缓存队列获取下一个推送项，并验证其状态

        Args:
            work_id: 工作ID

        Returns:
            推送上下文，如果没有有效的推送项则返回 None
        """
        while True:
            review_id = await self.push_cache.get_pending_push(work_id)
            if review_id is None:
                return None

            # 验证 review 状态
            review_data = await self.review_repository.get_by_id(int(review_id))
            if review_data and review_data.status == ReviewStatus.PASS:
                # 状态仍为 PASS 可以推送
                site_service = self.sites_manager.get_site_by_site_key(review_data.site_key)
                work_channel = await self.work_channel_repository.get_by_work_id(work_id)
                return PushCallbackContext(
                    review_id=review_data.id,
                    work_id=work_id,
                    channel_id=work_channel.channel_id,
                    artwork_id=review_data.artwork_id,
                    site_service=site_service,
                    push_service=self,
                )
            # 状态已变更 记录日志并继续下一个
            logger.info(
                "Review %s 状态已变更为 %s，跳过推送",
                review_id,
                review_data.status.name if review_data else "NOT_FOUND",
            )
            continue

    async def add_push(self, review_id: int, channel_id: int, message_id: int, status: bool, create_by: int):
        instance = Push(
            review_id=review_id, channel_id=channel_id, message_id=message_id, status=status, create_by=create_by
        )
        await self.push_repository.add(instance)

    async def set_send_push(self, review_id: int, channel_id: int, message_id: int, status: bool, create_by: int):
        instance = await self.push_repository.get_push(review_id)
        if instance is None:
            instance = Push(
                review_id=review_id, channel_id=channel_id, message_id=message_id, status=status, create_by=create_by
            )
            await self.push_repository.add(instance)
            return
        instance.channel_id = channel_id
        instance.message_id = message_id
        instance.status = status
        instance.update_by = create_by
        await self.push_repository.update(instance)

    async def undo_push(self, work_id: int, review_id: int) -> int:
        return await self.push_cache.set_pending_push(work_id, [review_id])
