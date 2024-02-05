import html
from typing import TYPE_CHECKING, List, Tuple

from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest as BotBadRequest, NetworkError as BotNetworkError
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.entities.artwork import ImageType
from paihub.error import BadRequest, ArtWorkNotFoundError
from paihub.log import logger
from paihub.system.review.entities import ReviewStatus
from paihub.system.review.services import ReviewService
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

GET_WORK, START_REVIEW, SET_REVIEW, _ = range(4)


class ReviewCommand(BaseCommand):
    def __init__(self, work_service: WorkService, review_service: ReviewService):
        self.work_service = work_service
        self.review_service = review_service

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("review", self.start, block=False), self.application)],
            states={
                GET_WORK: [CallbackQueryHandler(self.get_work, pattern=r"^set_review_work\|", block=False)],
                START_REVIEW: [CallbackQueryHandler(self.start_review, pattern=r"^start_review_work\|", block=False)],
                SET_REVIEW: [CallbackQueryHandler(self.set_review, pattern=r"^set_review_status\|", block=False)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CallbackQueryHandler(self.cancel, pattern=r"^exit")],
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
        await message.edit_text("正在初始化 Review 队列")
        count = await self.review_service.initialize_site_review(
            work_id=work_id, create_by=user.id, lines_per_page=10000
        )
        await message.reply_chat_action(ChatAction.TYPING)
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

        await message.edit_text(
            f"初始化 Review 队列完毕，当前一共有 {count} 作品需要 Review", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return START_REVIEW

    async def start_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            return _work_id

        await message.edit_text("正在获取图片")
        await message.reply_chat_action(ChatAction.TYPING)
        while True:
            work_id = get_callback_query(callback_query.data)
            count = await self.review_service.get_review_count(work_id)
            if count == 0:
                await message.reply_text("当前 Review 队列无任务\n退出 Review")
                return ConversationHandler.END
            review_context = await self.review_service.review_next(work_id=work_id)
            if review_context is None:
                await message.reply_text("当前 Review 队列无任务\n退出 Review")
                return ConversationHandler.END
            try:
                artwork = await review_context.get_artwork()
                artwork_images = await review_context.get_artwork_images()
                caption = (
                    f"Title {html.escape(artwork.title)}\n"
                    f"Tag {html.escape(artwork.format_tags(filter_character_tags=True))}\n"
                    f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
                    f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>\n"
                    f"At {artwork.create_time.strftime('%Y-%m-%d %H:%M')}"
                )
                if len(artwork_images) > 1:
                    media = [InputMediaPhoto(media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML)]
                    for data in artwork_images[1:]:
                        media.append(InputMediaPhoto(media=data))
                    media = media[:10]
                    await message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
                    await message.reply_media_group(
                        media,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                elif len(artwork_images) == 1:
                    if artwork.image_type == ImageType.STATIC:
                        await message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
                        await message.reply_photo(
                            photo=artwork_images[0],
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            connect_timeout=10,
                            read_timeout=10,
                            write_timeout=30,
                        )
                    elif artwork.image_type == ImageType.DYNAMIC:
                        await message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
                        await message.reply_video(
                            video=artwork_images[0],
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            connect_timeout=10,
                            read_timeout=10,
                            write_timeout=30,
                        )
                else:
                    raise RuntimeError
                auto_review = await review_context.try_auto_review()
                if auto_review is not None:
                    if auto_review.status:
                        await review_context.set_review_status(ReviewStatus.PASS, auto=True, update_by=user.id)
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    text="撤销该修改", callback_data=f"reset_review|{review_context.review_id}"
                                ),
                            ],
                        ]
                        await message.reply_text("当前作品已经自动通过\n正在获取下一个作品", reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    text="撤销该修改", callback_data=f"reset_review|{review_context.review_id}"
                                ),
                            ],
                        ]
                        await review_context.set_review_status(ReviewStatus.REJECT, auto=True, update_by=user.id)
                        await message.reply_text("当前作品已经自动拒绝\n正在获取下一个作品", reply_markup=InlineKeyboardMarkup(keyboard))
                    continue
                keyboard = [
                    [
                        InlineKeyboardButton(
                            text="通过", callback_data=f"set_review_status|{review_context.review_id}|1"
                        ),
                        InlineKeyboardButton(
                            text="拒绝", callback_data=f"set_review_status|{review_context.review_id}|0"
                        ),
                    ],
                    [
                        InlineKeyboardButton(text="退出", callback_data="exit"),
                    ],
                ]
                await message.reply_text("选择你要的操作", reply_markup=InlineKeyboardMarkup(keyboard))
                await message.delete()
                return SET_REVIEW
            except ArtWorkNotFoundError:
                await review_context.set_review_status(ReviewStatus.NOT_FOUND, update_by=user.id)
                await message.reply_text(f"[{review_context.site_key}]{review_context.artwork_id} 作品不存在 自动跳过")
                logger.warning("[%s]%s 作品不存在", review_context.site_key, review_context.artwork_id)
                continue
            except BadRequest as exc:
                await message.reply_text(f"Review 时发生错误：\n{exc.message}")
                await review_context.set_review_status(ReviewStatus.ERROR, update_by=user.id)
                logger.warning("Review时发生致命错误", exc_info=exc)
                continue
            except BotBadRequest as exc:
                await message.reply_text("Review时发生致命错误，详情请查看日志")
                logger.error("Review时发生致命错误", exc_info=exc)
                break
            except BotNetworkError as exc:
                await message.reply_text("Review时发生致命错误，详情请查看日志")
                logger.error("Review时发生致命错误", exc_info=exc)
                break
            except Exception as exc:
                await message.reply_text("Review时发生致命错误，详情请查看日志")
                logger.error("Review时发生致命错误", exc_info=exc)
                break

        return ConversationHandler.END

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
        if status == 1:
            review_info.set_pass(user.id)
            await message.edit_text("你选择了通过")
        else:
            review_info.set_reject(user.id)
            await message.edit_text("你选择了拒绝")
        await self.review_service.update_review(review_info)
        count = await self.review_service.get_review_count(review_info.work_id)
        keyboard = [
            [
                InlineKeyboardButton(text="继续", callback_data=f"start_review_work|{review_info.work_id}"),
            ],
            [
                InlineKeyboardButton(text="撤销修改", callback_data=f"cancel_review|{review_info.work_id}"),
                InlineKeyboardButton(text="退出", callback_data="exit"),
            ],
        ]
        await message.reply_text(f"当前还有{count}个作品未审核\n选择你要的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        return START_REVIEW

    async def cancel_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            return _review_id

        review_id = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        review_info.set_wait(user.id)
        review_info = await self.review_service.update_review(review_info)
        await message.edit_text("已经撤回修改")

        keyboard = [
            [
                InlineKeyboardButton(text="通过", callback_data=f"set_review_status|{review_info.id}|1"),
                InlineKeyboardButton(text="拒绝", callback_data=f"set_review_status|{review_info.id}|0"),
            ],
            [
                InlineKeyboardButton(text="退出", callback_data="exit"),
            ],
        ]

        await message.reply_text("选择你要的重写的操作", reply_markup=InlineKeyboardMarkup(keyboard))
        return SET_REVIEW

    @staticmethod
    async def cancel(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        if callback_query is None:
            await message.reply_text("退出命令", reply_markup=ReplyKeyboardRemove())
        else:
            await message.edit_text("退出命令")
        return ConversationHandler.END
