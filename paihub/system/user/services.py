from typing import List

from paihub.base import BaseService
from paihub.config import Settings
from paihub.log import logger
from paihub.system.user.cache import UserAdminCache
from paihub.system.user.entities import PermissionsEnum, User
from paihub.system.user.repositories import UserRepository


class UserAdminService(BaseService):
    def __init__(self, user_repository: UserRepository, cache: UserAdminCache, config: Settings):
        self.user_repository = user_repository
        self._cache = cache
        self.config = config

    async def initialize(self):
        owner = self.config.bot.owner
        if owner:
            user = await self.user_repository.get_by_user_id(owner)
            if user:
                if user.permissions != PermissionsEnum.OWNER:
                    user.permissions = PermissionsEnum.OWNER
                    await self._cache.set(user.user_id)
                    await self.user_repository.update(user)
            else:
                user = User(user_id=owner, permissions=PermissionsEnum.OWNER)
                await self._cache.set(user.user_id)
                await self.user_repository.add(user)
        else:
            logger.warning("检测到未配置Bot所有者 会导无法正常使用管理员权限")
        users = await self.user_repository.get_all()
        for user in users:
            await self._cache.set(user.user_id)

    async def is_admin(self, user_id: int) -> bool:
        return await self._cache.ismember(user_id)

    async def get_admin_list(self) -> List[int]:
        return await self._cache.get_all()

    async def add_admin(self, user_id: int) -> bool:
        user = await self.user_repository.get_by_user_id(user_id)
        if user:
            if user.permissions == PermissionsEnum.OWNER:
                return False
            if user.permissions != PermissionsEnum.ADMIN:
                user.permissions = PermissionsEnum.ADMIN
                await self.user_repository.update(user)
        else:
            user = User(user_id=user_id, permissions=PermissionsEnum.ADMIN)
            await self.user_repository.add(user)
        return await self._cache.set(user_id)

    async def delete_admin(self, user_id: int) -> bool:
        user = await self.user_repository.get_by_user_id(user_id)
        if user:
            if user.permissions == PermissionsEnum.OWNER:
                return True  # 假装移除成功
            user.permissions = PermissionsEnum.PUBLIC
            await self.user_repository.update(user)
            return await self._cache.remove(user.user_id)
        return False
