import html
from typing import TYPE_CHECKING, List, Tuple

from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.log import logger
from paihub.system.review.services import ReviewService
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

GET_WORK, START_REVIEW, SET_REVIEW, BIO = range(4)


class Review(BaseCommand):
    def __init__(self, work_service: WorkService, review_service: ReviewService):
        self.work_service = work_service
        self.review_service = review_service

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("review", self.start), self.application)],
            states={
                GET_WORK: [CallbackQueryHandler(self.get_work, pattern=r"^set_review_work\|")],
                START_REVIEW: [CallbackQueryHandler(self.start_review, pattern=r"^start_review_work\|")],
                SET_REVIEW: [CallbackQueryHandler(self.set_review, pattern=r"^set_review_status\|")],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CallbackQueryHandler(self.cancel, pattern=r"^cancel")],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 review 命令", user.full_name, user.id)
        works = await self.work_service.get_all()
        keyboard: List[List[InlineKeyboardButton]] = []
        row: List[InlineKeyboardButton] = []
        for index, work in enumerate(works):
            row.append(InlineKeyboardButton(text=work.name, callback_data=f"set_review_work|{work.id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        await message.reply_html(f"你好 {user.mention_html()} ！\n请选择你要进行的工作", reply_markup=InlineKeyboardMarkup(keyboard))
        return GET_WORK

    async def get_work(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            return _work_id

        work_id = get_callback_query(callback_query.data)
        await message.edit_text("正在初始化 Review 模块")
        count = await self.review_service.initialize_site_review(work_id=work_id, create_by=user.id)
        logger.info("Site review 已经初始化完毕，目前加入的作品有 %s", count)
        count = await self.review_service.get_review(work_id=work_id)
        logger.info("review 队列已经初始化完毕， 刚刚加入的作品有 %s", count)
        count = await self.review_service.get_review_count(work_id)
        logger.info("review 队列已经初始化完毕， 一共需要 Review %s", count)
        keyboard = [
            [
                InlineKeyboardButton(text="启动！", callback_data=f"start_review_work|{work_id}"),
                InlineKeyboardButton(text="取消", callback_data="cancel"),
            ],
        ]

        await message.edit_text(f"初始化 Review 完毕，当前一共有 {count} 作品需要 Review", reply_markup=InlineKeyboardMarkup(keyboard))
        return START_REVIEW

    async def start_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            return _work_id

        work_id = get_callback_query(callback_query.data)
        count = await self.review_service.get_review_count(work_id)
        if count == 0:
            await message.edit_text("当前 Review 队列无任务\n退出 Review")
            return ConversationHandler.END
        review = await self.review_service.review_next(work_id=work_id)
        if review is None:
            await message.edit_text("当前 Review 队列无任务\n退出 Review")
            return ConversationHandler.END
        await message.edit_text("正在获取图片")
        artwork = await review.get_artwork()
        artwork_images = await review.get_artwork_images()
        caption = f"Title {html.escape(artwork.title)}"
        if len(artwork_images) > 1:
            media = [InputMediaPhoto(media=data) for data in artwork_images]
            media = media[:10]
            media[0].caption = media
            media[0].parse_mode = ParseMode.MARKDOWN_V2
            await message.reply_media_group(media, write_timeout=30)
        elif len(artwork_images) == 1:
            await message.reply_photo(
                photo=artwork_images[0],
                caption=caption,
                parse_mode=ParseMode.MARKDOWN_V2,
                write_timeout=30,
            )
        else:
            raise RuntimeError
        keyboard = [
            [
                InlineKeyboardButton(text="通过", callback_data=f"set_review_status|{review.review_id}|1"),
                InlineKeyboardButton(text="拒绝", callback_data=f"set_review_status|{review.review_id}|0"),
            ],
        ]
        await message.reply_text("选择你要的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        await message.delete()
        return SET_REVIEW

    async def set_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
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
        review_info.status = status
        review_info.update_by = user.id
        await self.review_service.update_review(review_info)
        if status == 1:
            await message.edit_text("你选择了通过")
        else:
            await message.edit_text("你选择了拒绝")
        count = await self.review_service.get_review_count(review_info.work_id)
        keyboard = [
            [
                InlineKeyboardButton(text="继续", callback_data=f"start_review_work|{review_info.work_id}"),
                InlineKeyboardButton(text="取消", callback_data="cancel"),
            ],
        ]
        await message.reply_text(f"当前还有{count}个作品未审核\n选择你要的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        return START_REVIEW

    @staticmethod
    async def cancel(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        if callback_query is None:
            await message.reply_text("退出命令", reply_markup=ReplyKeyboardRemove())
        else:
            await message.edit_text("退出命令")
        return ConversationHandler.END
