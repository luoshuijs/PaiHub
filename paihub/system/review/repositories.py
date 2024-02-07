from typing import Optional, List, Set

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component
from paihub.dependence.database import DataBase
from paihub.system.review.entities import Review, ReviewStatus, StatusStatistics


class ReviewRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get(self, key_id: int) -> Optional[Review]:
        async with AsyncSession(self.engine) as session:
            statement = select(Review).where(Review.id == key_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, instance: Review):
        async with AsyncSession(self.engine) as session:
            session.add(instance)
            await session.commit()

    async def update(self, instance: Review) -> Review:
        async with AsyncSession(self.engine) as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def remove(self, instance: Review):
        async with AsyncSession(self.engine) as session:
            await session.delete(instance)
            await session.commit()

    async def get_artwork_id_by_work_and_web(
        self, work_id: int, site_key: str, page_number: int, lines_per_page: int = 10000
    ) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            statement = text(
                "SELECT artwork_id "
                "FROM review "
                "WHERE work_id = :work_id and site_key = :site_key "
                "LIMIT :limit OFFSET :offset"
            )
            params = {"work_id": work_id, "site_key": site_key, "limit": lines_per_page, "offset": offset}
            result = await session.execute(statement, params)
            return result.scalars().all()

    async def get_by_status(
        self, work_id: int, status: ReviewStatus, page_number: int, lines_per_page: int = 1000
    ) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            statement = text(
                "SELECT id "
                "FROM review "
                "WHERE work_id = :work_id and status = :status "
                "LIMIT :limit OFFSET :offset"
            )
            params = {"work_id": work_id, "status": status.name, "limit": lines_per_page, "offset": offset}
            result = await session.execute(statement, params)
            return result.scalars().all()

    async def get_by_status_statistics(self, work_id: int, site_key: str, author_id: int) -> StatusStatistics:
        async with _AsyncSession(self.engine) as session:
            statement = text(
                "SELECT `status`, COUNT(*) AS count "
                "FROM review "
                "WHERE work_id = :work_id and author_id = :author_id and site_key = :site_key "
                "GROUP BY `status`"
            )
            params = {"work_id": work_id, "author_id": author_id, "site_key": site_key}
            result = await session.execute(statement, params)
            return StatusStatistics.parse_form_result(result)

    async def get_filtered_status_counts(
        self, site_key: str, min_total_count: int = 10, pass_ratio_threshold: float = 0.8
    ) -> Set[int]:
        async with _AsyncSession(self.engine) as session:
            statement = text(
                "SELECT "
                "author_id, "
                "SUM(IF(status = 'PASS', 1, 0)) AS pass_count, "
                "SUM(IF(status = 'REJECT', 1, 0)) AS reject_count, "
                "SUM(IF(status = 'PASS' OR status = 'REJECT', 1, 0)) AS total_count "
                "FROM review "
                "WHERE site_key = :site_key "
                "GROUP BY author_id "
                "HAVING total_count > :min_total_count AND (pass_count / total_count) >= :pass_ratio_threshold "
            )
            params = {
                "site_key": site_key,
                "min_total_count": min_total_count,
                "pass_ratio_threshold": pass_ratio_threshold,
            }
            result = await session.execute(statement, params)
            return {row[0] for row in result}

    async def get_review_by_artwork_id(self, artwork_id: int) -> List[Review]:
        async with AsyncSession(self.engine) as session:
            statement = select(Review).where(Review.artwork_id == artwork_id)
            results = await session.exec(statement)
            return results.all()

    async def get_review(
        self,
        work_id: Optional[int] = None,
        site_key: Optional[str] = None,
        artwork_id: Optional[int] = None,
        status: Optional[StatusStatistics] = None,
    ) -> Optional[Review]:
        async with AsyncSession(self.engine) as session:
            statement = select(Review)
            if work_id is not None:
                statement = statement.where(Review.work_id == work_id)
            if site_key is not None:
                statement = statement.where(Review.site_key == site_key)
            if artwork_id is not None:
                statement = statement.where(Review.artwork_id == artwork_id)
            if status is not None:
                statement = statement.where(Review.status == status)
            results = await session.exec(statement)
            return results.first()
