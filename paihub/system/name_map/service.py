from typing import TYPE_CHECKING

from paihub.base import Service
from paihub.log import logger
from paihub.system.name_map.entities import NameMapConfig
from paihub.system.name_map.factory import NameMapFactory
from paihub.system.name_map.repository import NameMapConfigRepository
from paihub.system.name_map.utils import NameMap

if TYPE_CHECKING:
    from paihub.entities.artwork import ArtWork


class WorkTagFormatterService(Service):
    """工作流标签格式化服务

    整合了 NameMap 配置管理和 ArtWork 标签格式化功能
    """

    def __init__(self, config_repo: NameMapConfigRepository, name_map_factory: NameMapFactory):
        self.config_repo = config_repo
        self.name_map_factory = name_map_factory

    async def format_tags(
        self, artwork: "ArtWork", filter_character_tags: bool = False, work_id: int | None = None
    ) -> str:
        """格式化 ArtWork 标签

        降级策略：
        1. 如果不需要过滤角色标签，直接返回所有标签
        2. 如果找不到 NameMap 配置，返回所有标签（不过滤）
        3. 如果 NameMap 加载失败，返回所有标签（不过滤）

        Args:
            artwork: ArtWork 实例
            filter_character_tags: 是否过滤角色标签
            work_id: 工作流ID（可选），用于获取对应的 NameMap 配置

        Returns:
            格式化后的标签字符串
        """
        # 默认格式：返回所有标签
        default_tags = " ".join(f"#{tag}" for tag in artwork.tags)

        if not filter_character_tags:
            return default_tags

        try:
            # 根据 work_id 获取对应的 NameMap 实例
            name_map = await self.name_map_factory.get_instance_for_work(work_id)

            # 如果没有找到 NameMap 配置，返回原始标签
            if name_map is None:
                logger.debug(
                    f"No NameMap config for work_id={work_id}, returning raw tags. "
                    f"Use /name_map_bind to configure NameMap."
                )
                return default_tags

            # 使用 NameMap 过滤角色标签
            return name_map.filter_character_tags(artwork.tags)

        except Exception as e:
            logger.warning(
                f"Failed to format tags with NameMap (work_id={work_id}): {e}, returning raw tags", exc_info=True
            )
            return default_tags

    async def create_config(
        self,
        work_id: int | None,
        name_map_key: str,
        file_path: str | None = None,
        description: str | None = None,
        priority: int = 0,
        is_global_default: bool = False,
    ) -> NameMapConfig:
        """创建新的 NameMap 配置

        Args:
            work_id: 工作流ID，None 表示全局配置
            name_map_key: NameMap 配置键
            file_path: 自定义文件路径（可选）
            description: 配置描述
            priority: 优先级（数字越大优先级越高）
            is_global_default: 是否设置为全局默认配置

        Returns:
            创建的 NameMapConfig 实例
        """
        config = NameMapConfig(
            work_id=work_id,
            name_map_key=name_map_key,
            file_path=file_path,
            description=description,
            priority=priority,
            is_global_default=is_global_default,
        )

        await self.config_repo.add(config)

        # 清理缓存，确保新配置生效
        self.name_map_factory.clear_cache()

        return config

    async def set_global_default(self, config_id: int) -> bool:
        """设置指定配置为全局默认

        Args:
            config_id: 配置ID

        Returns:
            是否设置成功
        """
        success = await self.config_repo.set_global_default(config_id)
        if success:
            # 清理缓存，确保新的全局默认生效
            self.name_map_factory.clear_cache()
        return success

    async def update_config_status(self, config_id: int, is_active: bool) -> bool:
        """更新配置状态"""
        config = await self.config_repo.get_by_id(config_id)
        if not config:
            return False

        config.is_active = is_active
        await self.config_repo.update(config)

        # 清理相关缓存
        self.name_map_factory.clear_cache()

        return True

    async def get_name_map_for_work(self, work_id: int | None) -> NameMap:
        """获取工作流对应的 NameMap 实例"""
        return await self.name_map_factory.get_instance_for_work(work_id)

    async def get_all_configs(self, work_id: int | None = None) -> list[NameMapConfig]:
        """获取指定工作流的所有配置，如果 work_id 为 None 则获取全局配置"""
        return await self.config_repo.get_by_work_id(work_id)

    async def get_active_config(self, work_id: int | None) -> NameMapConfig | None:
        """获取指定工作流的激活配置"""
        return await self.config_repo.get_active_config(work_id)

    async def delete_config(self, config_id: int) -> bool:
        """删除配置"""
        config = await self.config_repo.get_by_id(config_id)
        if not config:
            return False

        await self.config_repo.remove(config)

        # 清理缓存
        self.name_map_factory.clear_cache()

        return True

    async def list_available_name_maps(self) -> list[str]:
        """列出所有可用的 NameMap 配置文件（从文件系统）"""
        return self.name_map_factory.list_available_keys()
