from typing import TYPE_CHECKING

from telegram.ext import CommandHandler
from telegram.helpers import escape_markdown

from paihub.base import BaseCommand
from paihub.log import logger

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class StartCommand(BaseCommand):
    def add_handlers(self):
        self.bot.add_handler(CommandHandler("start", self.start, block=False))
        self.bot.add_handler(CommandHandler("ping", self.ping, block=False))

    @staticmethod
    async def start(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        aegs = context.args
        logger.info("用户 %s[%s] 发出start命令", user.full_name, user.id)
        if aegs is not None and len(aegs) >= 1:
            return
        await message.reply_markdown_v2(f"你好 {user.mention_markdown_v2()} {escape_markdown('！')}")

    @staticmethod
    async def ping(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        await update.effective_message.reply_text("online! ヾ(✿ﾟ▽ﾟ)ノ")
