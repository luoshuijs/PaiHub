import asyncio
from pathlib import Path
from weakref import WeakValueDictionary

from paihub.base import Service
from paihub.log import logger
from paihub.system.name_map.repository import NameMapConfigRepository
from paihub.system.name_map.utils import NameMap


class NameMapFactory(Service):
    """NameMap 工厂类，支持创建和管理多个 NameMap 实例"""

    def __init__(self, repository: NameMapConfigRepository):
        # 使用弱引用字典，自动清理未使用的实例
        self._instances: WeakValueDictionary[str, NameMap] = WeakValueDictionary()
        self.repository = repository
        self._base_path = Path("metadata")
        self._name_map_dir = self._base_path / "name_map"

        # 读写锁实现
        self._write_lock = asyncio.Lock()  # 写锁（写操作时独占）
        self._read_lock = asyncio.Lock()  # 读锁（保护读计数器）
        self._readers = 0  # 当前读取者数量

        self._global_default_cache: NameMap | None = None  # 全局默认缓存

    async def _acquire_read(self):
        """获取读锁"""
        async with self._read_lock:
            self._readers += 1
            if self._readers == 1:
                # 第一个读者需要获取写锁，阻止写入
                await self._write_lock.acquire()

    async def _release_read(self):
        """释放读锁"""
        async with self._read_lock:
            self._readers -= 1
            if self._readers == 0:
                # 最后一个读者释放写锁，允许写入
                self._write_lock.release()

    async def _acquire_write(self):
        """获取写锁（独占）"""
        await self._write_lock.acquire()

    async def _release_write(self):
        """释放写锁"""
        self._write_lock.release()

    async def get_global_default_instance(self) -> NameMap | None:
        """获取全局默认 NameMap 实例（带缓存）

        用于没有 work_id 的场景（如 search、url 命令）

        Returns:
            NameMap | None: 全局默认的 NameMap 实例，如果没有配置则返回 None
        """
        # 快速路径：如果已有缓存，直接返回（无需加锁）
        if self._global_default_cache is not None:
            return self._global_default_cache

        # 慢速路径：需要创建实例，使用写锁
        await self._acquire_write()
        try:
            # 双重检查锁定模式
            if self._global_default_cache is not None:
                return self._global_default_cache

            config = await self.repository.get_global_default()
            if not config:
                logger.debug("No global default NameMap config found, will return raw tags")
                return None

            # 确定文件路径
            if config.file_path:
                file_path = self._base_path / config.file_path
            else:
                file_path = self._name_map_dir / f"{config.name_map_key}.json"

            if not file_path.exists():
                logger.warning(
                    f"NameMap file not found: {file_path} (key: {config.name_map_key}), will return raw tags"
                )
                return None

            # 创建实例并缓存
            try:
                self._global_default_cache = NameMap(file_path)
                logger.info(f"Loaded global default NameMap: {config.name_map_key} (file: {file_path.name})")
                return self._global_default_cache
            except Exception as e:
                logger.error(f"Failed to load global default NameMap: {e}", exc_info=True)
                return None
        finally:
            await self._release_write()

    async def get_instance_for_work(self, work_id: int | None = None) -> NameMap | None:
        """获取指定工作流的 NameMap 实例

        降级策略：
        1. 优先使用 work_id 特定配置
        2. 回退到全局默认配置
        3. 如果都没有，返回 None（调用方应返回原始标签）

        Args:
            work_id: 工作流ID。如果为 None，返回全局默认配置

        Returns:
            NameMap | None: 对应的 NameMap 实例，如果没有配置则返回 None
        """
        # 特殊处理：work_id 为 None 时，使用全局默认（带缓存）
        if work_id is None:
            return await self.get_global_default_instance()

        # 先尝试读取缓存（使用读锁）
        cache_key_prefix = f"work_{work_id}_"

        await self._acquire_read()
        try:
            # 在读锁保护下检查缓存
            for key, instance in self._instances.items():
                if key.startswith(cache_key_prefix):
                    logger.debug(f"Cache hit: {key}")
                    return instance
        finally:
            await self._release_read()

        # 缓存未命中，需要创建实例（使用写锁）
        await self._acquire_write()
        try:
            # 双重检查：可能在等待写锁期间其他协程已创建
            for key, instance in self._instances.items():
                if key.startswith(cache_key_prefix):
                    logger.debug(f"Cache hit after waiting: {key}")
                    return instance

            # 尝试获取 work 特定配置
            config = await self.repository.get_active_config(work_id)

            # 如果 work 没有特定配置，回退到全局默认
            if not config:
                logger.debug(f"Work {work_id} has no specific config, falling back to global default")
                return await self.get_global_default_instance()

            # 确定缓存键和文件路径
            cache_key = f"work_{work_id}_{config.name_map_key}"

            # 确定文件路径
            if config.file_path:
                file_path = self._base_path / config.file_path
            else:
                file_path = self._name_map_dir / f"{config.name_map_key}.json"

            # 验证文件存在
            if not file_path.exists():
                logger.warning(
                    f"NameMap file not found: {file_path} (work_id={work_id}, key={config.name_map_key}), "
                    f"falling back to global default"
                )
                return await self.get_global_default_instance()

            # 创建新实例
            try:
                instance = NameMap(file_path)
                self._instances[cache_key] = instance

                logger.info(
                    f"Created NameMap instance for work {work_id}: {config.name_map_key} (file: {file_path.name})"
                )
                return instance
            except Exception as e:
                logger.error(
                    f"Failed to create NameMap instance for work {work_id}: {e}, falling back to global default",
                    exc_info=True,
                )
                return await self.get_global_default_instance()
        finally:
            await self._release_write()

    def get_instance_by_key(self, key: str) -> NameMap:
        """根据键直接获取 NameMap 实例（同步方法）

        注意：这个方法不使用数据库配置，直接从文件系统加载
        主要用于测试或特殊场景

        Args:
            key: NameMap 配置键（例如 "genshin", "arknights"）

        Returns:
            NameMap: 对应的 NameMap 实例

        Raises:
            FileNotFoundError: 如果找不到对应的配置文件
        """
        cache_key = f"key_{key}"

        if cache_key in self._instances:
            return self._instances[cache_key]

        # 只支持 name_map/ 目录下的文件
        file_path = self._name_map_dir / f"{key}.json"

        if not file_path.exists():
            raise FileNotFoundError(
                f"NameMap file not found: {file_path}\nAvailable configs: {', '.join(self.list_available_keys())}"
            )

        instance = NameMap(file_path)
        self._instances[cache_key] = instance

        logger.debug(f"Created NameMap instance with key={key}, file={file_path}")
        return instance

    def list_available_keys(self) -> list[str]:
        """列出所有可用的 NameMap 配置键"""
        if not self._name_map_dir.exists():
            logger.warning(f"NameMap directory not found: {self._name_map_dir}")
            return []

        return [f.stem for f in self._name_map_dir.glob("*.json")]

    def clear_cache(self):
        """清空实例缓存（包括全局默认缓存）"""
        self._instances.clear()
        self._global_default_cache = None
        logger.info("NameMap instance cache cleared (including global default)")

    def get_cached_instances_info(self) -> dict[str, str]:
        """获取缓存实例信息（用于调试）"""
        info = {key: str(instance.data_file) for key, instance in self._instances.items()}
        if self._global_default_cache:
            info["_global_default"] = str(self._global_default_cache.data_file)
        return info

    async def initialize(self):
        """初始化工厂"""
        available_keys = self.list_available_keys()
        logger.info(f"NameMapFactory initialized. Available configs: {available_keys}")

        try:
            default_instance = await self.get_global_default_instance()
            if default_instance:
                logger.info("Global default NameMap preloaded successfully")
            else:
                logger.info(
                    "No global default NameMap configured. "
                    "Tags will be returned as-is unless configured via /name_map_bind"
                )
        except Exception as exc:
            logger.warning("Failed to preload global default NameMap", exc_info=exc)

    async def shutdown(self):
        """关闭工厂（BaseDependence 接口）"""
        self.clear_cache()
        logger.info("NameMapFactory shutdown")
