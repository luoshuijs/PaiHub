from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Repository
from paihub.system.user.entities import User

__all__ = ("UserRepository",)


class UserRepository(Repository[User]):
    async def get_by_user_id(self, user_id: int) -> User | None:
        async with AsyncSession(self.engine) as session:
            statement = select(User).where(User.user_id == user_id)
            results = await session.exec(statement)
            return results.first()
