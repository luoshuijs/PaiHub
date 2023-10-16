import asyncio

import dotenv
import pydantic
from sqlalchemy.sql import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine import URL

from paihub.services.artwork.models import PixivTable as Pixiv
from paihub.sqlmodel.session import AsyncSession
from test.dev.config import Settings


async def main():
    dotenv.load_dotenv()
    config = Settings()
    conn_str = URL.create(
        config.driver_name,
        **(lambda driver_name, **kw: kw)(**config.dict()),
    )
    async_engine = create_async_engine(conn_str)
    async with AsyncSession(bind=async_engine) as session:
        statement = select(Pixiv).where(1 == Pixiv.id)
        results = await session.execute(statement)
    breakpoint()
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
