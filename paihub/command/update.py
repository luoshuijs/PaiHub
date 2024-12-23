import asyncio
import os
from typing import TYPE_CHECKING

import anyio
from telegram import Message
from telegram.error import NetworkError
from telegram.ext import CommandHandler

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.log import logger
from paihub.utils.execute import execute

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

try:
    import orjson as jsonlib

except ImportError:
    import json as jsonlib

UPDATE_DATA = os.path.join(os.getcwd(), "update.json")


class UpdateCommand(BaseCommand):
    lock = asyncio.Lock()

    def add_handlers(self):
        self.bot.add_handler(AdminHandler(CommandHandler("update", self.update, block=False), self.application))

    async def initialize(self) -> None:
        if os.path.exists(UPDATE_DATA):
            async with await anyio.open_file(UPDATE_DATA) as file:
                data = jsonlib.loads(await file.read())
            try:
                reply_text = Message.de_json(data, self.application.bot.bot)
                await reply_text.edit_text("重启成功")
            except NetworkError as exc:
                logger.error("编辑消息出现错误 %s", exc.message)
            except jsonlib.JSONDecodeError:
                logger.error("JSONDecodeError")
            except KeyError as exc:
                logger.error("编辑消息出现错误", exc_info=exc)
            os.remove(UPDATE_DATA)

    async def update(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] update命令请求", user.full_name, user.id)
        if self.lock.locked():
            await message.reply_text("程序正在更新 请勿重复操作")
            return
        async with self.lock:
            reply_text = await message.reply_text("正在更新")
            logger.info("正在更新代码")
            await execute("git fetch --all")
            if context.args is not None and len(context.args) > 0:
                await execute("git reset --hard origin/main")
            await execute("git pull --all")
            logger.info("更新成功 正在重启")
            await reply_text.edit_text("更新成功 正在重启")
            async with anyio.open_file(UPDATE_DATA, mode="w", encoding="utf-8") as file:
                await file.write(reply_text.to_json())
        raise SystemExit
