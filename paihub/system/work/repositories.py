from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Repository
from paihub.system.work.entities import Work, WorkChannel, WorkRule

__all__ = ("WorkRepository", "WorkRuleRepository", "WorkChannelRepository")


class WorkRepository(Repository[Work]):
    pass


class WorkRuleRepository(Repository[WorkRule]):
    async def get_by_work_id(self, work_id: int) -> WorkRule | None:
        async with AsyncSession(self.engine) as session:
            statement = select(WorkRule).where(WorkRule.work_id == work_id)
            results = await session.exec(statement)
            return results.first()


class WorkChannelRepository(Repository[WorkChannel]):
    async def get_by_work_id(self, work_id: int) -> WorkChannel | None:
        async with AsyncSession(self.engine) as session:
            statement = select(WorkChannel).where(WorkChannel.work_id == work_id)
            results = await session.exec(statement)
            return results.first()

    async def get_by_rule_id(self, work_id: int) -> WorkChannel | None:
        async with AsyncSession(self.engine) as session:
            statement = select(WorkChannel).where(WorkChannel.id == work_id)
            results = await session.exec(statement)
            return results.first()
