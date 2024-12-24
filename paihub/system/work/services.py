from paihub.base import Service
from paihub.system.work.entities import Work, WorkChannel, WorkRule
from paihub.system.work.repositories import WorkChannelRepository, WorkRepository, WorkRuleRepository


class WorkService(Service):
    def __init__(
        self,
        work_repository: WorkRepository,
        work_rule_repository: WorkRuleRepository,
        work_channel_repository: WorkChannelRepository,
    ):
        self.work_repository = work_repository
        self.work_rule_repository = work_rule_repository
        self.work_channel_repository = work_channel_repository

    async def get_all(self) -> list[Work]:
        return await self.work_repository.get_all()

    async def get_work_rule_by_work_id(self, work_id: int) -> WorkRule | None:
        return await self.work_rule_repository.get_by_work_id(work_id)

    async def get_work_by_id(self, work_id: int) -> Work | None:
        return await self.work_repository.get_by_id(work_id)

    async def get_work_channel_by_work_id(self, work_id: int) -> WorkChannel | None:
        return await self.work_channel_repository.get_by_work_id(work_id)
