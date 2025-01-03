import asyncio
import warnings

import pytz
from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from persica.application import Application as _Application
from telegram.ext import ApplicationBuilder as BotApplicationBuilder
from telegram.ext import Defaults
from telegram.warnings import PTBUserWarning

from paihub.config import Settings
from paihub.log import logger

warnings.filterwarnings("ignore", category=PTBUserWarning)


__all__ = ("Application",)


class Application(_Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = Settings()
        build_bot = BotApplicationBuilder()
        build_bot.defaults(Defaults(tzinfo=pytz.timezone("Asia/Shanghai")))
        build_bot.token(self.settings.bot.token)
        if self.settings.bot.base_url is not None:
            build_bot.base_url(self.settings.bot.base_url)
        if self.settings.bot.base_file_url is not None:
            build_bot.base_file_url(self.settings.bot.base_file_url)
        self.bot = build_bot.build()
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Shanghai"))
        self.scheduler.add_listener(self.scheduler_error_listener, EVENT_JOB_ERROR)

    def scheduler_error_listener(self, event: JobExecutionEvent):
        if isinstance(event.exception, asyncio.CancelledError):
            logger.warning("Cancelling scheduler error", exc_info=event.exception)
            return
        asyncio.create_task(self.bot.process_error(update=None, error=event.exception))

    async def initialize(self) -> None:
        await self.context.initialize()
        try:
            self.scheduler.start()
        except Exception:
            logger.error("Scheduler 初始化时出现错误")
            raise

        def error_callback(error) -> None:
            self.bot.create_task(self.bot.process_error(error=error, update=None))

        try:
            await self.bot.initialize()
            if self.bot.post_init:
                await self.bot.post_init(self.bot)
            await self.bot.updater.start_polling(error_callback=error_callback)
            await self.bot.start()
        except Exception:
            logger.error("初始化Bot失败")
            raise

    async def shutdown(self) -> None:
        logger.info("PaiHub Application 正在退出")
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
        except Exception as exc:
            logger.error("关闭 Scheduler 时出现错误", exc_info=exc)
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
        await self.context.shutdown()
