import asyncio
import html
from typing import TYPE_CHECKING, List

from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import BadRequest as BotBadRequest, NetworkError as BotNetworkError
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.entities.artwork import ImageType
from paihub.error import BadRequest, ArtWorkNotFoundError
from paihub.log import logger
from paihub.system.push.services import PushService
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

GET_WORK, START_PUSH, _, _ = range(4)


class PushCommand(BaseCommand):
    def __init__(self, work_service: WorkService, push_service: PushService):
        self.work_service = work_service
        self.push_service = push_service

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("push", self.start, block=False), self.application)],
            states={
                GET_WORK: [CallbackQueryHandler(self.get_pust, pattern=r"^set_push_work\|", block=False)],
                START_PUSH: [CallbackQueryHandler(self.start_push, pattern=r"^start_push_work\|", block=False)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CallbackQueryHandler(self.cancel, pattern=r"^exit")],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 push 命令", user.full_name, user.id)
        works = await self.work_service.get_all()
        keyboard: List[List[InlineKeyboardButton]] = []
        for work in works:
            keyboard.append([InlineKeyboardButton(text=work.name, callback_data=f"set_push_work|{work.id}")])
        keyboard.append([InlineKeyboardButton(text="退出", callback_data="exit")])
        await message.reply_html(f"你好 {user.mention_html()} ！\n请选择你要进行的工作", reply_markup=InlineKeyboardMarkup(keyboard))
        return GET_WORK

    async def get_pust(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            return _work_id

        work_id = get_callback_query(callback_query.data)
        await message.edit_text("正在初始化 Push 队列")
        count = await self.push_service.get_push(work_id)
        logger.info("Push 队列已经初始化完毕 刚刚加入的作品有 %s", count)
        count = await self.push_service.get_push_count(work_id)
        logger.info("Push 队列已经初始化完毕 一共有 %s 个作品需要推送", count)
        keyboard = [
            [
                InlineKeyboardButton(text="启动！", callback_data=f"start_push_work|{work_id}"),
                InlineKeyboardButton(text="退出", callback_data="exit"),
            ],
        ]

        await message.edit_text(f"初始化 Push 完毕，当前一共有 {count} 作品需要 Push", reply_markup=InlineKeyboardMarkup(keyboard))
        return START_PUSH

    async def start_push(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        callback_query = update.callback_query
        bot = context.bot

        def get_callback_query(callback_query_data: str) -> int:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            return _work_id

        work_id = get_callback_query(callback_query.data)
        await message.edit_text("正在推送")

        while True:
            count = await self.push_service.get_push_count(work_id)
            if count == 0:
                await message.edit_text("当前 Push 队列无任务\n退出 Push")
                return ConversationHandler.END
            push_context = await self.push_service.get_next_push(work_id=work_id)
            if push_context is None:
                await message.edit_text("当前 Push 队列无任务\n退出 Push")
                return ConversationHandler.END
            await message.edit_text(f"当前有 {count} 个作品正在推送")
            try:
                artwork = await push_context.get_artwork()
                artwork_images = await push_context.get_artwork_images()
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
                    send_media_group_message = await bot.send_media_group(
                        chat_id=push_context.channel_id,
                        media=media,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                    await push_context.set_push(message_id=send_media_group_message[0].id, create_by=user.id)
                elif len(artwork_images) == 1:
                    if artwork.image_type == ImageType.STATIC:
                        send_photo_message = await bot.send_photo(
                            chat_id=push_context.channel_id,
                            photo=artwork_images[0],
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            connect_timeout=10,
                            read_timeout=10,
                            write_timeout=30,
                        )
                        await push_context.set_push(message_id=send_photo_message.id, create_by=user.id)
                    elif artwork.image_type == ImageType.DYNAMIC:
                        send_video_message = await bot.send_video(
                            chat_id=push_context.channel_id,
                            video=artwork_images[0],
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            connect_timeout=10,
                            read_timeout=10,
                            write_timeout=30,
                        )
                        await push_context.set_push(message_id=send_video_message.id, create_by=user.id)
                else:
                    raise RuntimeError
                count = await self.push_service.get_push_count(work_id)
                if count == 0:
                    await message.reply_text("推送完毕")
                    await message.delete()
                    return ConversationHandler.END
                await asyncio.sleep(len(artwork_images) * 3)
            except ArtWorkNotFoundError:
                await push_context.set_push(status=False, create_by=user.id)
                await message.reply_text(f"[Review]{push_context.review_id} 作品不存在")
                logger.warning("[Review]%s 作品不存在", push_context.review_id)
                continue
            except BadRequest as exc:
                await push_context.set_push(status=False, create_by=user.id)
                await message.reply_text(f"[Review]{push_context.review_id} 推送时发生错误：\n{exc.message}")
                logger.warning("推送时发生致命错误", exc_info=exc)
                continue
            except BotBadRequest as exc:
                await message.reply_text("推送时发生致命错误\n%s", exc.message)
                logger.error("推送时发生致命错误", exc_info=exc)
                break
            except BotNetworkError as exc:
                await message.reply_text("推送时发生致命错误\n%s", exc.message)
                logger.error("推送时发生致命错误", exc_info=exc)
                break
            except Exception as exc:
                await message.reply_text("推送时发生致命错误，详情请查看日志")
                logger.error("推送时发生致命错误", exc_info=exc)
                break

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
