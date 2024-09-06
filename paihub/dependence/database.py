from asyncio import current_task
from contextlib import asynccontextmanager
from typing import cast, TYPE_CHECKING

from sqlalchemy import URL, inspect
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
    AsyncEngine,
    AsyncConnection,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import BaseDependence
from paihub.config import DatabaseConfig
from paihub.log import logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection


class DataBase(BaseDependence):
    def __init__(self):
        config = DatabaseConfig()
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

    @staticmethod
    def _test_connection(subject: "Connection"):
        inspector = inspect(subject)
        table_names = inspector.get_table_names()
        dialect_name = subject.dialect.name
        logger.success("连接 [yellow]%s[/yellow] 数据库成功", dialect_name)
        logger.info("当前数据库表 %s", " ".join(f"[white][i]{table_name}[/i][/white]" for table_name in table_names))

    async def initialize(self) -> None:
        try:
            async with self._engine.begin() as _conn:
                conn = cast(AsyncConnection, _conn)
                await conn.run_sync(self._test_connection)
        except Exception as exc:
            logger.error("连接数据库失败")
            raise exc

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def shutdown(self):
        await self._session_factory.close_all()

    @asynccontextmanager
    async def session(self) -> "AsyncSession":
        session: "AsyncSession" = self._session_factory()
        try:
            yield session
        except Exception as exc:
            logger.exception("Session rollback because of exception", exc_info=exc)
            await session.rollback()
            raise exc
        finally:
            await session.close()
