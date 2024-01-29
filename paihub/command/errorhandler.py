import os
import time
import traceback
from typing import cast, Optional

import aiofiles
from telegram import Update
from telegram.error import BadRequest, NetworkError
from telegram.ext import CallbackContext

from paihub.base import BaseCommand
from paihub.log import logger
from paihub.utils.pb import PbClient

try:
    import ujson as jsonlib

except ImportError:
    import json as jsonlib


class ErrorHandler(BaseCommand):
    error_chat_id: Optional[int] = None

    def __init__(self):
        current_dir = os.getcwd()
        self.report_dir = os.path.join(current_dir, "report")
        if not os.path.exists(self.report_dir):
            os.mkdir(self.report_dir)
        self.pb = PbClient()

    def add_handlers(self):
        self.bot.add_error_handler(self.error_handler)
        self.error_chat_id = self.application.settings.bot.owner

    async def error_handler(self, update: object, context: CallbackContext) -> None:
        """Log the error and send a message to notify the developer."""

        # Log the error before we do anything else, so we can see it even if something breaks.
        logger.error("Exception while handling an update:", exc_info=context.error)

        if self.error_chat_id is None:
            return

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, cast(Exception, context.error).__traceback__)
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)

        error_text = (
            f"-----Exception while handling an update-----\n"
            f"update = {jsonlib.dumps(update_str, indent=2, ensure_ascii=False)}\n"
            f"context.chat_data = {str(context.chat_data)}\n"
            f"context.user_data = {str(context.user_data)}\n"
            "\n"
            "-----Traceback info-----\n"
            f"{tb_string}"
        )

        file_name = f"error_{update.update_id if isinstance(update, Update) else int(time.time())}.txt"
        log_file = os.path.join(self.report_dir, file_name)

        try:
            async with aiofiles.open(log_file, mode="w+", encoding="utf-8") as f:
                await f.write(error_text)
        except Exception as exc:  # pylint: disable=W0703
            logger.error("保存日记失败", exc_info=exc)

        try:
            await context.bot.send_document(
                chat_id=self.error_chat_id,
                document=open(log_file, "rb"),
                caption=f'Error: "{context.error.__class__.__name__}"',
            )
        except BadRequest as exc:
            logger.error("发送日记失败", exc_info=exc)
        except NetworkError as exc:
            logger.error("发送日记失败", exc_info=exc)
        except FileNotFoundError:
            logger.error("发送日记失败 文件不存在")
