from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component
from paihub.dependence.database import DataBase
from paihub.system.work.entities import Work, WorkChannel, WorkRule

__all__ = ("WorkRepository", "WorkRuleRepository", "WorkChannelRepository")


class WorkRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get_by_work_id(self, work_id: int) -> Work | None:
        async with AsyncSession(self.engine) as session:
            statement = select(Work).where(Work.id == work_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, work: Work):
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()

    async def update(self, work: Work) -> Work:
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()
            await session.refresh(work)
            return work

    async def remove(self, work: Work):
        async with AsyncSession(self.engine) as session:
            await session.delete(work)
            await session.commit()

    async def get_all(self) -> list[Work]:
        async with AsyncSession(self.engine) as session:
            statement = select(Work)
            results = await session.exec(statement)
            return results.all()


class WorkRuleRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get_by_work_id(self, work_id: int) -> WorkRule | None:
        async with AsyncSession(self.engine) as session:
            statement = select(WorkRule).where(WorkRule.work_id == work_id)
            results = await session.exec(statement)
            return results.first()

    async def get_by_rule_id(self, work_id: int) -> WorkRule | None:
        async with AsyncSession(self.engine) as session:
            statement = select(WorkRule).where(WorkRule.id == work_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, work: WorkRule):
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()

    async def update(self, work: WorkRule) -> WorkRule:
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()
            await session.refresh(work)
            return work

    async def remove(self, work: WorkRule):
        async with AsyncSession(self.engine) as session:
            await session.delete(work)
            await session.commit()

    async def get_all(self) -> list[WorkRule]:
        async with AsyncSession(self.engine) as session:
            statement = select(Work)
            results = await session.exec(statement)
            return results.all()


class WorkChannelRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

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

    async def add(self, work: WorkChannel):
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()

    async def update(self, work: WorkChannel) -> WorkChannel:
        async with AsyncSession(self.engine) as session:
            session.add(work)
            await session.commit()
            await session.refresh(work)
            return work

    async def remove(self, work: WorkChannel):
        async with AsyncSession(self.engine) as session:
            await session.delete(work)
            await session.commit()

    async def get_all(self) -> list[WorkChannel]:
        async with AsyncSession(self.engine) as session:
            statement = select(Work)
            results = await session.exec(statement)
            return results.all()
