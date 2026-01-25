import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from watchfiles import awatch

from paihub.base import Component
from paihub.log import logger
from paihub.system.name_map.factory import NameMapFactory


class WatchNameMap(Component):
    """监听 NameMap 配置文件变化并自动重载

    监听 metadata/name_map/ 目录下的所有 JSON 文件，当文件变化时清理 NameMapFactory 缓存
    """

    executor = ThreadPoolExecutor()
    stop_event: asyncio.Event = asyncio.Event()
    waiter_task: asyncio.Task = None
    loop: asyncio.AbstractEventLoop

    def __init__(self, name_map_factory: NameMapFactory):
        """初始化监听器"""
        self.name_map_factory = name_map_factory

    async def initialize(self):
        self.loop = asyncio.get_event_loop()
        self.waiter_task = asyncio.create_task(self.watch_name())

    async def shutdown(self):
        self.stop_event.set()
        if self.waiter_task:
            await self.waiter_task

    async def watch_name(self):
        """监听 metadata/name_map/ 目录下的所有 JSON 文件"""
        name_map_dir = Path("metadata") / "name_map"

        if not name_map_dir.exists():
            logger.warning(f"NameMap directory not found: {name_map_dir}")
            return

        logger.success(f"Successfully added Watch NameMap. Watching: {name_map_dir}")

        try:
            async for changes in awatch(name_map_dir, stop_event=self.stop_event):
                for change, path in changes:
                    # 只处理 JSON 文件
                    if not str(path).endswith(".json"):
                        continue

                    logger.debug("Detected NameMap change: Path=%s, Event=%s", path, change.name)

                    try:
                        # 清理工厂缓存，让它在下次使用时重新加载
                        await self.loop.run_in_executor(self.executor, self.name_map_factory.clear_cache)
                        logger.success(f"NameMap cache cleared due to file change: {path}")
                    except Exception as e:
                        logger.error(f"Failed to clear NameMap cache: {e}", exc_info=True)

        except Exception as exc:
            logger.error("Watch NameMap error", exc_info=exc)
