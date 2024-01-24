import asyncio
import platform
import signal
from typing import Sequence, Optional, NoReturn

import pytz
from telegram.ext import ApplicationBuilder as BotApplicationBuilder, Defaults

from paihub.base import BaseDependence, BaseService, BaseCommand
from paihub.config import Settings
from paihub.log import logger
from persica import Factor


class Application:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.settings = Settings()
        self.factor = Factor(
            paths=["paihub.dependence", "paihub.system", "paihub.command"],
            kwargs=[self.settings, self.settings.database, self.settings.redis],
        )
        self.bot = (
            BotApplicationBuilder()
            .defaults(Defaults(tzinfo=pytz.timezone("Asia/Shanghai")))
            .token(self.settings.bot.token)
            .build()
        )

    def run(self, stop_signals: Optional[Sequence[int]] = None):
        logger.info("正在初始化 Factor")
        self.factor.install()
        logger.info("Component 构造完毕")
        if platform.system() != "Windows":
            stop_signals = (signal.SIGINT, signal.SIGTERM, signal.SIGABRT)
        if stop_signals is not None:
            for sig in stop_signals or []:
                self.loop.add_signal_handler(sig, self._raise_system_exit)
        try:
            self.loop.run_until_complete(self.initialize())
            self.loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Application received stop signal. Shutting down.")
        except Exception as exc:
            logger.error("Application received exception. Shutting down.")
            raise exc
        finally:
            self.loop.run_until_complete(self.shutdown())

    async def initialize(self) -> None:
        for d in self.factor.get_components(BaseDependence):
            try:
                await d.initialize()
            except Exception as exc:
                logger.error("%s 初始化失败", d.__class__.__name__)
                raise exc
        for s in self.factor.get_components(BaseService):
            try:
                s.set_application(self)
                await s.initialize()
            except Exception as exc:
                logger.error("%s 初始化失败", s.__class__.__name__)
                raise exc
        for c in self.factor.get_components(BaseCommand):
            try:
                c.set_application(self)
                await c.initialize()
                c.add_handlers()
            except Exception as exc:
                logger.error("%s 初始化失败", c.__class__.__name__)
                raise exc

        def error_callback(error) -> None:
            self.bot.create_task(self.bot.process_error(error=error, update=None))

        try:
            await self.bot.initialize()
            if self.bot.post_init:
                await self.bot.post_init(self.bot)
            await self.bot.updater.start_polling(error_callback=error_callback)
            await self.bot.start()
        except Exception as exc:
            logger.error("初始化Bot失败")
            raise exc

    async def shutdown(self) -> None:
        logger.info("PaiHub Application 正在退出")
        try:
            if self.bot.updater.running:
                await self.bot.updater.stop()
            if self.bot.running:
                await self.bot.stop()
            if self.bot.post_stop:
                await self.bot.post_stop(self.bot)
            await self.bot.shutdown()
            if self.bot.post_shutdown:
                await self.bot.post_shutdown(self.bot)
        except Exception as exc:
            logger.error("关闭Bot时出现错误", exc_info=exc)

    @staticmethod
    def _raise_system_exit() -> NoReturn:
        raise SystemExit