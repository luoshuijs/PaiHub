from typing import Optional, List, Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component
from paihub.dependence.database import DataBase
from paihub.system.review.entities import Review


class ReviewRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get(self, key_id: int) -> Optional[Review]:
        async with AsyncSession(self.engine) as session:
            statement = select(Review).where(Review.id == key_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, key: Review):
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()

    async def update(self, key: Review) -> Review:
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()
            await session.refresh(key)
            return key

    async def remove(self, key: Review):
        async with AsyncSession(self.engine) as session:
            await session.delete(key)
            await session.commit()

    async def get_artwork_id_by_work_and_web(
        self, work_id: int, web_id: int, page_number: int, lines_per_page: int = 1000
    ) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            statement = text(
                "SELECT artwork_id "
                "FROM review "
                "WHERE work_id = :work_id and web_id = :web_id "
                "LIMIT :limit OFFSET :offset"
            )
            params = {"work_id": work_id, "web_id": web_id, "limit": lines_per_page, "offset": offset}
            result = await session.execute(statement, params)
            return result.scalars().all()

    async def get_by_status_is_null(self, work_id: int, page_number: int, lines_per_page: int = 1000) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            statement = text(
                "SELECT id " "FROM review " "WHERE work_id = :work_id and status IS NULL " "LIMIT :limit OFFSET :offset"
            )
            params = {"work_id": work_id, "limit": lines_per_page, "offset": offset}
            result = await session.execute(statement, params)
            return result.scalars().all()

    async def set_reviews_id(
        self, work_id: int, web_id: int, reviews_id: Iterable[int], create_by: Optional[int] = None, **kwargs
    ):
        async with AsyncSession(self.engine) as session:
            instances = [
                Review(work_id=work_id, web_id=web_id, artwork_id=i, create_by=create_by, **kwargs) for i in reviews_id
            ]
            session.add_all(instances)
            await session.commit()
