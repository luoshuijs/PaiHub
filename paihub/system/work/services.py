from typing import List, Optional

from paihub.base import BaseService
from paihub.system.work.entities import Work, WorkRule, WorkChannel
from paihub.system.work.repositories import WorkRepository, WorkRuleRepository, WorkChannelRepository


class WorkService(BaseService):
    def __init__(
        self,
        work_repository: WorkRepository,
        work_rule_repository: WorkRuleRepository,
        work_channel_repository: WorkChannelRepository,
    ):
        self.work_repository = work_repository
        self.work_rule_repository = work_rule_repository
        self.work_channel_repository = work_channel_repository

    async def get_all(self) -> List[Work]:
        return await self.work_repository.get_all()

    async def get_work_rule_by_work_id(self, work_id: int) -> Optional[WorkRule]:
        return await self.work_rule_repository.get_by_work_id(work_id)

    async def get_by_work_id(self, work_id: int) -> Optional[Work]:
        return await self.work_repository.get_by_work_id(work_id)

    async def get_work_channel_by_work_id(self, work_id: int) -> Optional[WorkChannel]:
        return await self.work_channel_repository.get_by_work_id(work_id)
