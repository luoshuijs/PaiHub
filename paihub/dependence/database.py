from contextlib import asynccontextmanager
from asyncio import current_task

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, async_scoped_session, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import BaseDependence
from paihub.log import logger
from paihub.config import Database as DatabaseConfig


class DataBase(BaseDependence):
    def __init__(
        self,
        config: DatabaseConfig,
    ):
        self._url = URL.create(
            config.driver_name,
            username=config.username,
            password=config.password,
            host=config.host,
            port=config.port,
            database=config.database,
        )
        self._engine = create_async_engine(self._url)
        self._session = async_sessionmaker(bind=self._engine, class_=AsyncSession, autocommit=False, autoflush=False)
        self._session_factory = async_scoped_session(self._session, current_task)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def shutdown(self):
        await self._session_factory.close_all()

    @asynccontextmanager
    async def session(self):
        session: "AsyncSession" = self._session_factory()
        try:
            yield session
        except Exception as exc:
            logger.exception("Session rollback because of exception", exc_info=exc)
            await session.rollback()
            raise exc
        finally:
            await session.close()
