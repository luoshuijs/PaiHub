from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Repository
from paihub.system.push.auto_push_entities import AutoPushConfig, AutoPushStatus


class AutoPushConfigRepository(Repository[AutoPushConfig]):
    """自动推送配置Repository"""

    async def get_by_work_id(self, work_id: int) -> list[AutoPushConfig]:
        """根据work_id获取所有配置
        :param work_id: 工作ID
        :return: 配置列表
        """
        async with AsyncSession(self.engine) as session:
            statement = select(AutoPushConfig).where(AutoPushConfig.work_id == work_id)
            results = await session.exec(statement)
            return list(results.all())

    async def get_enabled_configs(self) -> list[AutoPushConfig]:
        """获取所有启用状态的配置
        :return: 配置列表
        """
        async with AsyncSession(self.engine) as session:
            statement = select(AutoPushConfig).where(AutoPushConfig.status == AutoPushStatus.ENABLED)
            results = await session.exec(statement)
            return list(results.all())

    async def get_by_work_and_name(self, work_id: int, name: str) -> AutoPushConfig | None:
        """根据work_id和name获取配置
        :param work_id: 工作ID
        :param name: 配置名称
        :return: 配置对象或None
        """
        async with AsyncSession(self.engine) as session:
            statement = select(AutoPushConfig).where(AutoPushConfig.work_id == work_id, AutoPushConfig.name == name)
            results = await session.exec(statement)
            return results.first()
