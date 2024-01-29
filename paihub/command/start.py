from typing import TYPE_CHECKING

from telegram.ext import CommandHandler
from telegram.helpers import escape_markdown

from paihub.base import BaseCommand
from paihub.log import logger

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class Start(BaseCommand):
    def add_handlers(self):
        self.bot.add_handler(CommandHandler("start", self.start, block=False))

    @staticmethod
    async def start(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        args = context.args
        args_text = " ".join(args) if args else ""
        logger.info("用户 %s[%s] 发出start命令 args[%s]", user.full_name, user.id, args_text)
        if args is not None and len(args) >= 1:
            return
        await message.reply_markdown_v2(f"你好 {user.mention_markdown_v2()} {escape_markdown('！')}")