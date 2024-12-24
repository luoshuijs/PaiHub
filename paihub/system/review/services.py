from paihub.base import Service
from paihub.system.review.cache import ReviewCache
from paihub.system.review.entities import AutoReviewResult, Review, ReviewStatus
from paihub.system.review.ext import ReviewCallbackContext
from paihub.system.review.repositories import ReviewRepository
from paihub.system.sites.manager import SitesManager
from paihub.system.work.error import WorkRuleNotFound
from paihub.system.work.repositories import WorkRepository, WorkRuleRepository


class ReviewService(Service):
    """审核服务"""

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

    async def initialize_review_form_sites(
        self, work_id: int, lines_per_page: int = 10000, create_by: int | None = None
    ) -> int:
        """通知网站初始化审核队列
        :param work_id: 工作OD
        :param lines_per_page: 每一页的操作数量
        :param create_by: 当前操作的用户ID
        :return: int 已经添加进队列的数量
        """
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

    async def initialize_review_queue(self, work_id: int) -> int:
        """初始化审核队列
        :param work_id: 工作ID
        :return: int 已经添加进队列的数量
        """
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

    async def retrieve_next_for_review(self, work_id: int) -> ReviewCallbackContext | None:
        """从审核队列获取下一个作品
        :param work_id: 工作ID
        :return: ReviewCallbackContext
        """
        review_id = await self.review_cache.get_pending_review(work_id)
        if review_id is None:
            return None
        review_data = await self.review_repository.get_by_id(int(review_id))
        site_service = self.sites_manager.get_site_by_site_key(review_data.site_key)
        return ReviewCallbackContext(review=review_data, site_service=site_service, review_service=self)

    async def get_review_count(self, work_id: int) -> int:
        """获取下一个审核的队列
        :param work_id:
        :return:
        """
        return await self.review_cache.get_review_count(work_id)

    async def get_by_review_id(self, review_id: int) -> Review | None:
        """通过 review_id 从数据库中获取 Review
        :param review_id: ReviewID
        :return: Review
        """
        return await self.review_repository.get_by_id(review_id)

    async def update_review(self, review: Review) -> Review:
        """更新审核信息到数据库并返回最新信息
        :param review: Review 实例
        :return: 更新后的 Review 实例
        """
        return await self.review_repository.update(review)

    async def remove_review(self, review: Review):
        """从数据库数据库中删除 Review
        :param review: Review 实例
        :return:
        """
        await self.review_repository.remove(review)

    async def move_review(self, review: Review, target_work_id: int, update_by: int):
        """移动审核信息到其他 Work 中
        :param review: 要移动的 Review 实例
        :param target_work_id: 移动的目标 Work id
        :param update_by: 当前操作的用户ID
        :return: None
        """
        review.set_move(update_by, target_work_id)
        review = await self.review_repository.update(review)
        move = review.model_copy()
        move.work_id = target_work_id
        move.id = None
        move.create_by = update_by
        move.create_time = None
        move.update_by = None
        move.update_time = None
        await self.review_repository.add(move)
        await self.review_repository.update(review)

    async def try_auto_review(self, work_id: int, site_key: str, author_id: int) -> AutoReviewResult | None:
        """尝试自动审核
        :param work_id: 当前 Work id
        :param site_key: 网站唯一标识符
        :param author_id: 作者ID
        :return: Optional[AutoReviewResult] 如果无法判断会返回 None 审核成功会返回 AutoReviewResult
        """
        statistics = await self.review_repository.get_by_status_statistics(
            work_id, site_key=site_key, author_id=author_id
        )
        if statistics.already >= 3:
            if statistics.pass_count / statistics.already >= 0.5:
                return AutoReviewResult(status=True, statistics=statistics)
            return AutoReviewResult(status=False, statistics=statistics)
        return None

    async def get_review_by_artwork_id(self, artwork_id: int) -> list[Review]:
        """从根据 artwork_id获取数据库中的审核信息
        :param artwork_id: 作品ID
        :return: List[Review] 审核信息列表
        """
        return await self.review_repository.get_review_by_artwork_id(artwork_id)

    async def set_send_review(
        self, work_id: int, site_key: str, artwork_id: int, create_by: int, status: ReviewStatus = ReviewStatus.PASS
    ):
        """设置发送 Review 信息
        :param work_id: 工作ID
        :param site_key: 网站唯一标识符
        :param artwork_id: 作品ID
        :param create_by: 当前操作的用户ID
        :param status: 需要更新的状态 默认为 ReviewStatus.PASS
        :return: None
        """
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
