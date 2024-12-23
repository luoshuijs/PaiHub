from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Repository
from paihub.system.push.entities import Push


class PushRepository(Repository[Push]):
    async def get_push(self, review_id: int | None = None) -> Push | None:
        async with AsyncSession(self.engine) as session:
            statement = select(Push)
            if review_id is not None:
                statement = statement.where(Push.review_id == review_id)
            results = await session.exec(statement)
            return results.first()

    async def get_review_id_by_push(self, work_id: int) -> list[int]:
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
