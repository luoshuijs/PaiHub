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
        self, search_text: str, is_pattern: bool, page_number: int, lines_per_page: int = 1000
    ) -> List[int]:
        async with _AsyncSession(self.engine) as session:
            offset = (page_number - 1) * lines_per_page
            if is_pattern:
                statement = text("SELECT id FROM pixiv WHERE tags REGEXP :regex_pattern LIMIT :limit OFFSET :offset")
            else:
                statement = text("SELECT id FROM pixiv WHERE tags LIKE :search_text LIMIT :limit OFFSET :offset")
                search_text = f"%{search_text}%"
            result = await session.execute(
                statement, {"search_text": search_text, "limit": lines_per_page, "offset": offset}
            )
            return result.scalars().all()

    async def get(self, artwork_id: int) -> Optional[Pixiv]:
        async with AsyncSession(self.engine) as session:
            statement = select(Pixiv).where(Pixiv.id == artwork_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, user: Pixiv):
        async with AsyncSession(self.engine) as session:
            session.add(user)
            await session.commit()

    async def update(self, user: Pixiv) -> Pixiv:
        async with AsyncSession(self.engine) as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def remove(self, user: Pixiv):
        async with AsyncSession(self.engine) as session:
            await session.delete(user)
            await session.commit()
