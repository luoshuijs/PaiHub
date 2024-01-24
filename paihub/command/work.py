from typing import TYPE_CHECKING

from telegram.ext import CommandHandler

from paihub.base import BaseCommand
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class Work(BaseCommand):
    def __init__(self, work_service: WorkService):
        self.work_service = work_service

    def add_handlers(self):
        self.bot.add_handler(CommandHandler("work", self.work, block=False))

    async def work(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        works = await self.work_service.get_all()
        work = works[-1]
        work_channels = work.work_channels
        print(work_channels)
