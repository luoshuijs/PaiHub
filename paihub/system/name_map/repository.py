from sqlmodel import and_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from paihub.base import Repository
from paihub.system.name_map.entities import NameMapConfig


class NameMapConfigRepository(Repository[NameMapConfig]):
    """工作流 NameMap 配置仓储"""

    async def get_by_work_id(self, work_id: int | None) -> list[NameMapConfig]:
        """获取指定工作流的所有配置"""
        async with AsyncSession(self.engine) as session:
            statement = (
                select(NameMapConfig).where(NameMapConfig.work_id == work_id).order_by(NameMapConfig.priority.desc())
            )
            results = await session.exec(statement)
            return results.all()

    async def get_active_config(self, work_id: int | None) -> NameMapConfig | None:
        """获取指定工作流的激活配置（优先级最高的）"""
        async with AsyncSession(self.engine) as session:
            statement = (
                select(NameMapConfig)
                .where(and_(NameMapConfig.work_id == work_id, NameMapConfig.is_active))
                .order_by(NameMapConfig.priority.desc())
                .limit(1)
            )
            results = await session.exec(statement)
            return results.first()

    async def get_global_default(self) -> NameMapConfig | None:
        """获取全局默认配置

        优先返回标记为 is_global_default=True 的配置
        如果没有，则返回 work_id=None 且 is_active=True 的配置
        """
        async with AsyncSession(self.engine) as session:
            # 优先查找标记为全局默认的配置
            statement = (
                select(NameMapConfig)
                .where(and_(NameMapConfig.is_global_default, NameMapConfig.is_active))
                .order_by(NameMapConfig.priority.desc(), NameMapConfig.id.desc())
                .limit(1)
            )
            results = await session.exec(statement)
            config = results.first()

            if config:
                return config

            # 如果没有，回退到 work_id=None 的配置
            return await self.get_active_config(None)

    async def set_global_default(self, config_id: int) -> bool:
        """设置指定配置为全局默认

        会自动取消其他配置的全局默认标记

        Args:
            config_id: 要设置为全局默认的配置ID

        Returns:
            bool: 是否设置成功
        """
        async with AsyncSession(self.engine) as session:
            # 先取消所有全局默认标记
            statement = select(NameMapConfig).where(NameMapConfig.is_global_default)
            results = await session.exec(statement)
            for old_default in results.all():
                old_default.is_global_default = False
                session.add(old_default)

            # 设置新的全局默认
            statement = select(NameMapConfig).where(NameMapConfig.id == config_id)
            results = await session.exec(statement)
            config = results.first()

            if not config:
                return False

            config.is_global_default = True
            config.is_active = True  # 确保激活
            session.add(config)

            await session.commit()
            return True
