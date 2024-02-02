from datetime import datetime
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component
from paihub.dependence.database import DataBase
from paihub.sites.pixiv.entities import Pixiv

__all__ = ("PixivRepository",)


class PixivRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get_artworks_by_tags(
        self, search_text: str, is_pattern: bool, page_number: int, lines_per_page: int = 10000
    ) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            if is_pattern:
                statement = text("SELECT id FROM pixiv WHERE tags REGEXP :search_text LIMIT :limit OFFSET :offset")
            else:
                statement = text("SELECT id FROM pixiv WHERE tags LIKE :search_text LIMIT :limit OFFSET :offset")
                search_text = f"%{search_text}%"
            result = await session.execute(
                statement, {"search_text": search_text, "limit": lines_per_page, "offset": offset}
            )
            return result.scalars().all()

    async def add_review_form_pixiv(self, work_id: int, artwork_id: int, create_by: Optional[int] = None):
        create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with _AsyncSession(self.engine) as session:
            statement = text(
                "INSERT INTO review (work_id, site_key, artwork_id, author_id, status, create_by, create_time) "
                "SELECT :work_id, 'pixiv', pixiv.id, pixiv.author_id, 'WAIT' , :create_by , :create_time "
                "FROM pixiv "
                "WHERE pixiv.id = :artwork_id"
            )
            params = {
                "work_id": work_id,
                "artwork_id": artwork_id,
                "create_by": create_by,
                "create_time": create_time,
            }
            await session.execute(statement, params)
            await session.commit()


    async def get(self, artwork_id: int) -> Optional[Pixiv]:
        async with AsyncSession(self.engine) as session:
            statement = select(Pixiv).where(Pixiv.id == artwork_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, value: Pixiv):
        async with AsyncSession(self.engine) as session:
            session.add(value)
            await session.commit()

    async def merge(self, value: Pixiv):
        async with AsyncSession(self.engine) as session:
            await session.merge(value)

    async def update(self, value: Pixiv) -> Pixiv:
        async with AsyncSession(self.engine) as session:
            session.add(value)
            await session.commit()
            await session.refresh(value)
            return value

    async def remove(self, value: Pixiv):
        async with AsyncSession(self.engine) as session:
            await session.delete(value)
            await session.commit()
