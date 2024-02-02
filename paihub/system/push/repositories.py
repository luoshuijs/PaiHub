from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component

from paihub.dependence.database import DataBase
from paihub.system.push.entities import Push


class PushRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get(self, key_id: int) -> Optional[Push]:
        async with AsyncSession(self.engine) as session:
            statement = select(Push).where(Push.id == key_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, key: Push):
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()

    async def update(self, key: Push) -> Push:
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()
            await session.refresh(key)
            return key

    async def remove(self, key: Push):
        async with AsyncSession(self.engine) as session:
            await session.delete(key)
            await session.commit()

    async def get_review_id_by_push(self, work_id: int) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            statement = text(
                "SELECT review.id "
                "FROM review "
                "WHERE review.status = 'PASS' AND review.work_id = :work_id "
                "AND review.id NOT IN (SELECT push.review_id FROM push)"
            )
            params = {"work_id": work_id}
            result = await session.execute(statement, params)
            return result.scalars().all()
