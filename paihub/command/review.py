import html
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardRemove
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest as BotBadRequest
from telegram.error import NetworkError as BotNetworkError
from telegram.error import RetryAfter as BotRetryAfter
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.entities.artwork import ImageType
from paihub.error import ArtWorkNotFoundError, BadRequest, RetryAfter
from paihub.log import logger
from paihub.system.review.entities import AutoReviewResult, ReviewAuthorRuleAction, ReviewStatus
from paihub.system.review.services import ReviewService
from paihub.system.work.error import WorkRuleNotFound
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

GET_WORK, START_REVIEW, SET_REVIEW, _ = range(4)


class ReviewCommand(Command):
    def __init__(self, work_service: WorkService, review_service: ReviewService):
        self.work_service = work_service
        self.review_service = review_service

    @staticmethod
    def build_review_keyboard(review_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton(text="通过", callback_data=f"set_review_status|{review_id}|1"),
                InlineKeyboardButton(text="拒绝", callback_data=f"set_review_status|{review_id}|0"),
            ],
            [
                InlineKeyboardButton(text="加白并通过", callback_data=f"set_review_author_rule|{review_id}|1"),
                InlineKeyboardButton(text="加黑并拒绝", callback_data=f"set_review_author_rule|{review_id}|0"),
            ],
            [InlineKeyboardButton(text="退出", callback_data="review_exit")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_review_result_keyboard(
        work_id: int,
        review_id: int,
        undo_callback: str = "revert_review_change",
        undo_text: str = "撤销修改",
    ) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(text="继续", callback_data=f"start_review_work|{work_id}")],
            [
                InlineKeyboardButton(text=undo_text, callback_data=f"{undo_callback}|{review_id}"),
                InlineKeyboardButton(text="退出", callback_data="review_exit"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_auto_review_keyboard(review_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(text="撤销该修改", callback_data=f"reset_review_form_command|{review_id}")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def format_auto_review_text(auto_review: AutoReviewResult) -> str:
        if auto_review.description == "author_whitelist":
            return "命中作者白名单，当前作品已自动通过"
        if auto_review.description == "author_blacklist":
            return "命中作者黑名单，当前作品已自动拒绝"
        if auto_review.description == "history_pass_ratio":
            return "根据历史审核记录，当前作品已自动通过"
        if auto_review.description == "history_reject_ratio":
            return "根据历史审核记录，当前作品已自动拒绝"
        if auto_review.status:
            return "当前作品已自动通过"
        return "当前作品已自动拒绝"

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("review", self.start, block=False), self.application)],
            states={
                GET_WORK: [CallbackQueryHandler(self.get_work, pattern=r"^set_review_work\|", block=False)],
                START_REVIEW: [
                    CallbackQueryHandler(self.start_review, pattern=r"^start_review_work\|", block=False),
                    CallbackQueryHandler(self.revert_review_change, pattern=r"^revert_review_change\|", block=False),
                    CallbackQueryHandler(
                        self.revert_review_author_rule,
                        pattern=r"^revert_review_author_rule\|",
                        block=False,
                    ),
                ],
                SET_REVIEW: [
                    CallbackQueryHandler(self.set_review, pattern=r"^set_review_status\|", block=False),
                    CallbackQueryHandler(
                        self.set_review_author_rule,
                        pattern=r"^set_review_author_rule\|",
                        block=False,
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^review_exit"),
            ],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 review 命令", user.full_name, user.id)
        works = await self.work_service.get_all()
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=work.name, callback_data=f"set_review_work|{work.id}")] for work in works
        ]
        keyboard.append([InlineKeyboardButton(text="退出", callback_data="review_exit")])
        await message.reply_html(
            f"你好 {user.mention_html()} ！\n请选择你要进行的工作", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GET_WORK

    async def get_work(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            return int(_data[1])

        work_id = get_callback_query(callback_query.data)
        await message.edit_text("正在初始化 Review 队列")
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            count = await self.review_service.initialize_review_form_sites(
                work_id=work_id, create_by=user.id, lines_per_page=10000
            )
        except WorkRuleNotFound:
            await message.edit_text("当前 Work 未配置规则 退出任务")
            return ConversationHandler.END
        logger.info("Site review 已经初始化完毕，目前加入的作品有 %s", count)
        count = await self.review_service.initialize_review_queue(work_id=work_id)
        logger.info("review 队列已经初始化完毕， 刚刚加入的作品有 %s", count)
        count = await self.review_service.get_review_count(work_id)
        logger.info("review 队列已经初始化完毕， 一共需要 Review %s", count)
        keyboard = [
            [
                InlineKeyboardButton(text="启动！", callback_data=f"start_review_work|{work_id}"),
                InlineKeyboardButton(text="取消", callback_data="review_exit"),
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
            return int(_data[1])

        await message.edit_text("正在处理作品")
        await message.reply_chat_action(ChatAction.TYPING)
        while True:
            work_id = get_callback_query(callback_query.data)
            count = await self.review_service.get_review_count(work_id)
            if count == 0:
                await message.reply_text("当前 Review 队列无任务\n退出 Review")
                return ConversationHandler.END
            review_context = await self.review_service.retrieve_next_for_review(work_id=work_id)
            if review_context is None:
                await message.reply_text("当前 Review 队列无任务\n退出 Review")
                return ConversationHandler.END
            try:
                auto_review = await review_context.try_auto_review()
                if auto_review is not None:
                    review_status = ReviewStatus.PASS if auto_review.status else ReviewStatus.REJECT
                    await review_context.set_review_status(
                        review_status,
                        auto=True,
                        update_by=user.id,
                        auto_reason=auto_review.description,
                    )
                    await message.reply_text(
                        f"{self.format_auto_review_text(auto_review)}\n正在获取下一个作品",
                        reply_markup=self.build_auto_review_keyboard(review_context.review_id),
                    )
                    continue
                artwork = await review_context.get_artwork()
                artwork_images = await review_context.get_artwork_images()
                formatted_tags = await review_context.format_artwork_tags(artwork, filter_character_tags=True)
                caption = (
                    f"Title {html.escape(artwork.title)}\n"
                    f"Tag {html.escape(formatted_tags)}\n"
                    f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
                    f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>\n"
                    f"At {artwork.create_time.strftime('%Y-%m-%d %H:%M')}"
                )
                if len(artwork_images) > 1:
                    media = [InputMediaPhoto(media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML)]
                    media.extend(InputMediaPhoto(media=data) for data in artwork_images[1:])
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
                    raise RuntimeError  # noqa: TRY301
                await message.reply_text(
                    "选择你要的操作", reply_markup=self.build_review_keyboard(review_context.review_id)
                )
                await message.delete()
            except ArtWorkNotFoundError:
                await review_context.set_review_status(ReviewStatus.NOT_FOUND, update_by=user.id)
                await message.reply_text(f"[{review_context.site_key}]{review_context.artwork_id} 作品不存在 自动跳过")
                logger.warning("[%s]%s 作品不存在", review_context.site_key, review_context.artwork_id)
                continue
            except RetryAfter as exc:
                await message.reply_text(f"触发速率限制 请等待{exc.retry_after}秒")
                logger.warning(f"触发速率限制 请等待{exc.retry_after}秒", exc_info=exc)
                break
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
            except BotRetryAfter as exc:
                await message.reply_text(f"太快啦！\n等待{exc.retry_after}秒后重试")
                logger.warning("超出洪水控制限制 等待%s秒后重试", exc.retry_after)
                break
            except Exception as exc:
                await review_context.set_review_status(ReviewStatus.ERROR, update_by=user.id)
                await message.reply_text("Review时发生致命错误，退出Review")
                await self.application.bot.process_error(update, exc)
                logger.error("Review时发生致命错误", exc_info=exc)
                break
            else:
                return SET_REVIEW

        return ConversationHandler.END

    async def set_review(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
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
        if review_info is None:
            await message.edit_text("该 Review 不存在")
            return ConversationHandler.END
        if status == 1:
            review_info.set_pass(user.id)
            await message.edit_text("你选择了通过")
        else:
            review_info.set_reject(user.id)
            await message.edit_text("你选择了拒绝")
        await self.review_service.update_review(review_info)
        count = await self.review_service.get_review_count(review_info.work_id)
        await message.reply_text(
            f"当前还有{count}个作品未审核\n选择你要的操作",
            reply_markup=self.build_review_result_keyboard(review_info.work_id, review_info.id),
        )
        return START_REVIEW

    async def set_review_author_rule(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> tuple[int, int]:
            _data = callback_query_data.split("|")
            _review_id = int(_data[1])
            _action = int(_data[2])
            return _review_id, _action

        review_id, action = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if review_info is None:
            await message.edit_text("该 Review 不存在")
            return ConversationHandler.END
        if review_info.author_id is None:
            await message.edit_text(
                "当前 Review 缺少作者信息，无法设置作者规则", reply_markup=self.build_review_keyboard(review_id)
            )
            return SET_REVIEW

        author_rule_action = ReviewAuthorRuleAction.AUTO_PASS if action == 1 else ReviewAuthorRuleAction.AUTO_REJECT
        await self.review_service.set_author_rule(
            work_id=review_info.work_id,
            site_key=review_info.site_key,
            author_id=review_info.author_id,
            action=author_rule_action,
            update_by=user.id,
        )

        if action == 1:
            review_info.set_pass(user.id)
            await message.edit_text("已加入当前 Work 的作者白名单，并设置为通过")
        else:
            review_info.set_reject(user.id)
            await message.edit_text("已加入当前 Work 的作者黑名单，并设置为拒绝")

        await self.review_service.update_review(review_info)
        count = await self.review_service.get_review_count(review_info.work_id)
        await message.reply_text(
            f"当前还有{count}个作品未审核\n选择你要的操作",
            reply_markup=self.build_review_result_keyboard(
                review_info.work_id,
                review_info.id,
                undo_callback="revert_review_author_rule",
                undo_text="撤销规则",
            ),
        )
        return START_REVIEW

    async def revert_review_change(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            return int(_data[1])

        review_id = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if review_info is None:
            await message.edit_text("该 Review 不存在")
            return ConversationHandler.END
        review_info.set_wait(user.id)
        review_info = await self.review_service.update_review(review_info)
        logger.info("用户 %s[%s] 尝试对 Review[%s] 发出 Reset 命令", user.full_name, user.id, review_id)

        await message.edit_text("选择你要的重写的操作", reply_markup=self.build_review_keyboard(review_info.id))
        return SET_REVIEW

    async def revert_review_author_rule(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            return int(_data[1])

        review_id = get_callback_query(callback_query.data)
        review_info = await self.review_service.get_by_review_id(review_id=review_id)
        if review_info is None:
            await message.edit_text("该 Review 不存在")
            return ConversationHandler.END
        if review_info.author_id is None:
            await message.edit_text("当前 Review 缺少作者信息，无法撤销作者规则")
            return ConversationHandler.END

        await self.review_service.remove_author_rule(
            work_id=review_info.work_id,
            site_key=review_info.site_key,
            author_id=review_info.author_id,
        )
        review_info.set_wait(user.id)
        review_info = await self.review_service.update_review(review_info)
        await message.edit_text(
            "已撤销作者规则，并恢复当前 Review", reply_markup=self.build_review_keyboard(review_info.id)
        )
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
