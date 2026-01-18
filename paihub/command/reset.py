from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MessageEntityType
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.log import logger
from paihub.system.push.cache import PushCache
from paihub.system.review.services import ReviewService
from paihub.system.sites.manager import SitesManager
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

GET_REVIEW, GET_STATUS, SET_STATUS, MOVE_REVIEW = range(4)


class ResetCommand(Command):
    def __init__(
        self,
        work_service: WorkService,
        review_service: ReviewService,
        sites_manager: SitesManager,
        push_cache: PushCache,
    ):
        self.sites_manager = sites_manager
        self.work_service = work_service
        self.review_service = review_service
        self.push_cache = push_cache

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[
                AdminHandler(
                    CallbackQueryHandler(
                        self.start_callback_query, pattern=r"^reset_review_form_command\|", block=False
                    ),
                    self.application,
                ),
                AdminHandler(
                    CommandHandler("reset", self.start_command, filters=filters.ChatType.PRIVATE, block=False),
                    self.application,
                ),
            ],
            states={
                GET_REVIEW: [MessageHandler(~filters.COMMAND, self.get_review_info, block=False)],
                GET_STATUS: [CallbackQueryHandler(self.start_callback_query, pattern=r"^reset_review\|", block=False)],
                SET_STATUS: [CallbackQueryHandler(self.set_status, pattern=r"^reset_review_status\|", block=False)],
                MOVE_REVIEW: [CallbackQueryHandler(self.move_review, pattern=r"^reset_review_move\|", block=False)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^reset_exit"),
            ],
        )
        self.bot.add_handler(conv_handler)

    async def start_command(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int:
        message = update.effective_message
        reply_to_message = message.reply_to_message
        if reply_to_message is not None:
            return await self.get_review_info(update, context)
        await message.reply_text("请发送要修改作品的链接")
        return GET_REVIEW

    async def get_review_info(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE") -> int:
        message = update.effective_message
        reply_to_message = message.reply_to_message

        text: str | None = None

        if reply_to_message is not None:
            for caption_entities in reply_to_message.caption_entities:
                if caption_entities.type == MessageEntityType.TEXT_LINK:
                    text += caption_entities.url
            if text is None:
                text = reply_to_message.text
            else:
                text += reply_to_message.text
        else:
            text = message.text

        rows: list[InlineKeyboardButton] = []

        reply_text = "请选择你要修改的 Review\n"

        for site in self.sites_manager.get_all_sites():
            artwork_id = site.extract(text)
            if artwork_id is not None:
                reviews = await self.review_service.get_review_by_artwork_id(artwork_id)
                if len(reviews) == 0:
                    continue
                for review in reviews:
                    work = await self.work_service.get_work_by_id(review.work_id)
                    if work is None:
                        logger.warning("WorkId[%s] 不存在！", review.work_id)
                        continue
                    reply_text += (
                        f"工作名称：{work.name}\n"
                        f"网站：{review.site_key}\n"
                        f"审核ID：{review.id}\n"
                        f"作品ID：{artwork_id}\n"
                        f"当前状态：{review.status.name}\n"
                        f"\n"
                    )
                    rows.append(
                        InlineKeyboardButton(f"ReViewId[{review.id}]", callback_data=f"reset_review|{review.id}")
                    )

        if len(rows) == 0:
            await message.reply_text("找不到 URL 或 Review 信息")
            return ConversationHandler.END

        keyboard: list[list[InlineKeyboardButton]] = [rows[i : i + 2] for i in range(0, len(rows), 2)]

        await message.reply_text(reply_text, reply_markup=InlineKeyboardMarkup(keyboard))

        return GET_STATUS

    async def start_callback_query(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> tuple[int, bool]:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            _form_command = "form_command" in _data[0]
            return _review_id, _form_command

        review_id, form_command = get_callback_query(callback_query.data)
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
                InlineKeyboardButton(text="删除", callback_data=f"reset_review_status|{review_info.id}|-1"),
                InlineKeyboardButton(text="移动", callback_data=f"reset_review_status|{review_info.id}|-2"),
            ],
            [
                InlineKeyboardButton(text="退出", callback_data="reset_exit"),
            ],
        ]

        if form_command:
            await message.reply_text("选择你要的重写的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message.edit_text("选择你要的重写的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        return SET_STATUS

    async def set_status(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> tuple[int, int]:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            _status = int(_data[2])
            return _review_id, _status

        review_id, status = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if status == 1:
            review_info.set_pass(user.id)
            await self.review_service.update_review(review_info)
            await message.edit_text("已经修改为通过")
        elif status == 0:
            review_info.set_reject(user.id)
            await self.review_service.update_review(review_info)
            # 从推送队列中移除
            if await self.push_cache.remove_from_push_queue(review_info.work_id, review_info.id):
                logger.info("已从推送队列中移除 Review ID: %s", review_info.id)
                await message.edit_text("已经修改为拒绝，并从推送队列中移除")
            else:
                await message.edit_text("已经修改为拒绝")
        elif status == -1:
            # 从推送队列中移除
            await self.push_cache.remove_from_push_queue(review_info.work_id, review_info.id)
            await self.review_service.remove_review(review_info)
            await message.edit_text("已经删除该审核信息")
        elif status == -2:
            works = await self.work_service.get_all()
            keyboard: list[list[InlineKeyboardButton]] = [
                [InlineKeyboardButton(text=work.name, callback_data=f"reset_review_move|{work.id}")] for work in works
            ]
            keyboard.append([InlineKeyboardButton(text="退出", callback_data="reset_exit")])
            await message.edit_text("请选择要修改的 Work", reply_markup=InlineKeyboardMarkup(keyboard))
            return MOVE_REVIEW
        else:
            await message.edit_text("未知的 Callback Query Data")
        return ConversationHandler.END

    async def move_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> tuple[int, int]:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            _work_id = int(_data[2])
            return _review_id, _work_id

        review_id, work_id = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        await self.review_service.move_review(review_info, work_id, user.id)
        await message.edit_text(f"已经完成对 ReviewId[{review_id}] 移动")
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
