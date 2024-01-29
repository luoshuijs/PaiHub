from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Component
from paihub.dependence.database import DataBase
from paihub.system.sites.entities import Site

__all__ = ("SitesRepository",)


class SitesRepository(Component):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    async def get(self, key_id: int) -> Optional[Site]:
        async with AsyncSession(self.engine) as session:
            statement = select(Site).where(Site.id == key_id)
            results = await session.exec(statement)
            return results.first()

    async def get_by_key_name(self, web_key: str) -> Optional[Site]:
        async with AsyncSession(self.engine) as session:
            statement = select(Site).where(Site.web_key == web_key)
            results = await session.exec(statement)
            return results.first()

    async def add(self, key: Site):
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()

    async def update(self, key: Site) -> Site:
        async with AsyncSession(self.engine) as session:
            session.add(key)
            await session.commit()
            await session.refresh(key)
            return key

    async def remove(self, key: Site):
        async with AsyncSession(self.engine) as session:
            await session.delete(key)
            await session.commit()
