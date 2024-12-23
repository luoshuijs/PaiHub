from typing import TYPE_CHECKING

from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import CommandHandler

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.log import logger

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class SetBotCommand(Command):
    user = [
        BotCommand("start", "Start！"),
    ]

    admin = [
        BotCommand("review", "开始审核"),
        BotCommand("push", "开始推送"),
        BotCommand("reset", "重设审核"),
        BotCommand("update", "更新代码"),
        BotCommand("send", "快速发送"),
        BotCommand("ping", "Ping！"),
        BotCommand("cancel", "取消操作"),
    ]

    def add_handlers(self):
        self.bot.add_handler(
            AdminHandler(CommandHandler("set_admin_command", self.set_command, block=False), self.application)
        )
        self.bot.add_handler(
            AdminHandler(CommandHandler("start", self.start_set, block=False), self.application, need_notify=False),
            group=10,
        )

    async def set_command(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 set_command 命令", user.full_name, user.id)

        await context.bot.set_my_commands(commands=self.user + self.admin, scope=BotCommandScopeChat(chat.id))
        await message.reply_text("设置命令成功")

    async def start_set(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        chat = update.effective_chat
        await context.bot.set_my_commands(commands=self.user + self.admin, scope=BotCommandScopeChat(chat.id))
