from typing import TYPE_CHECKING, Tuple

from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.log import logger
from paihub.system.review.services import ReviewService
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

SET_STATUS, _, _, _ = range(4)


class SetCommand(BaseCommand):
    def __init__(self, work_service: WorkService, review_service: ReviewService):
        self.work_service = work_service
        self.review_service = review_service

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[
                AdminHandler(
                    CallbackQueryHandler(self.start, pattern=r"^reset_review\|", block=False), self.application
                )
            ],
            states={
                SET_STATUS: [CallbackQueryHandler(self.set_status, pattern=r"^reset_review_status\|", block=False)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CallbackQueryHandler(self.cancel, pattern=r"^cancel")],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            return _review_id

        review_id = get_callback_query(callback_query.data)
        logger.info("用户 %s[%s] 尝试对 Review[%s] 发出 Reset 命令", user.full_name, user.id, review_id)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if review_info is None:
            await message.reply_text("该 Review 不存在")
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(text="通过", callback_data=f"reset_review_status|{review_info.id}|1"),
                InlineKeyboardButton(text="拒绝", callback_data=f"reset_review_status|{review_info.id}|0"),
            ],
            [
                InlineKeyboardButton(text="退出", callback_data="exit"),
            ],
        ]

        await message.reply_text("选择你要的重写的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        return SET_STATUS

    async def set_status(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> Tuple[int, int]:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            _status = int(_data[2])
            return _review_id, _status

        review_id, status = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if status == 1:
            review_info.set_pass(user.id)
            await message.edit_text("已经修改为通过")
        else:
            review_info.set_reject(user.id)
            await message.edit_text("已经修改为拒绝")
        await self.review_service.update_review(review_info)
        return ConversationHandler.END

    @staticmethod
    async def cancel(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        if callback_query is None:
            await message.reply_text("退出命令", reply_markup=ReplyKeyboardRemove())
        else:
            await message.edit_text("退出命令")
        return ConversationHandler.END
