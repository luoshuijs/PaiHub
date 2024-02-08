import html
from typing import TYPE_CHECKING, List, Tuple, Optional

from telegram import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest as BotBadRequest, NetworkError as BotNetworkError
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.entities.artwork import ImageType
from paihub.error import BadRequest, ArtWorkNotFoundError
from paihub.log import logger
from paihub.system.push.services import PushService
from paihub.system.review.services import ReviewService
from paihub.system.sites.manager import SitesManager
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update, Message
    from telegram.ext import ContextTypes

GET_INFO, GET_WORK, SEND, _ = range(4)

URL_REGEX = r"(http|https):\/\/([\w\-\.]+)(:[0-9]+)?(\/[\w\-\.\/]*)?(\?[a-zA-Z0-9&%_\./-~-]*)?"


class SendCommand(BaseCommand):
    def __init__(
        self,
        sites_manager: SitesManager,
        work_service: WorkService,
        push_service: PushService,
        review_service: ReviewService,
    ):
        self.work_service = work_service
        self.push_service = push_service
        self.review_service = review_service
        self.sites_manager = sites_manager

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("send", self.start_command, block=False), self.application)],
            states={
                GET_INFO: [
                    MessageHandler(
                        filters=filters.ChatType.PRIVATE & filters.Regex(URL_REGEX), callback=self.get_info, block=False
                    )
                ],
                GET_WORK: [CallbackQueryHandler(self.get_work, pattern=r"^send_work\|", block=False)],
                SEND: [CallbackQueryHandler(self.send_artwork, pattern=r"^send_artwork\|", block=False)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), CallbackQueryHandler(self.cancel, pattern=r"^exit")],
        )
        self.bot.add_handler(conv_handler)

    @staticmethod
    async def start_command(update: "Update", _: "ContextTypes.DEFAULT_TYPE") -> int:
        message = update.effective_message
        await message.reply_text("请发送要推送作品的链接")
        return GET_INFO

    async def get_info(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        for match in context.matches:
            url = match.group()
            for site in self.sites_manager.get_all_sites():
                artwork_id = site.extract(url)
                if artwork_id is not None:
                    await message.reply_chat_action(ChatAction.TYPING)
                    try:
                        artwork = await site.get_artwork(artwork_id)
                        artwork_images = await site.get_artwork_images(artwork_id)
                        caption = (
                            f"Title {html.escape(artwork.title)}\n"
                            f"Tag {html.escape(artwork.format_tags(filter_character_tags=True))}\n"
                            f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
                            f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>\n"
                            f"At {artwork.create_time.strftime('%Y-%m-%d %H:%M')}"
                        )
                        if len(artwork_images) > 1:
                            media = [
                                InputMediaPhoto(media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML)
                            ]
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
                        works = await self.work_service.get_all()
                        keyboard: List[List[InlineKeyboardButton]] = []
                        for work in works:
                            keyboard.append(
                                [
                                    InlineKeyboardButton(
                                        text=work.name,
                                        callback_data=f"send_work|{work.id}|{site.site_key}|{artwork_id}",
                                    )
                                ]
                            )
                        keyboard.append([InlineKeyboardButton(text="退出", callback_data="exit")])
                        await message.reply_text("请选择要推送的 Work", reply_markup=InlineKeyboardMarkup(keyboard))
                        return GET_WORK
                    except ArtWorkNotFoundError:
                        await message.reply_text("作品不存在")
                    except BadRequest as exc:
                        await message.reply_text(f"获取图片详细信息时发生错误：\n{exc.message}")
                        logger.error("获取图片详细信息时发生致命错误", exc_info=exc)
                    except BotBadRequest as exc:
                        await message.reply_text("获取图片详细信息时发生致命错误，详情请查看日志")
                        logger.error("获取图片详细信息时发生致命错误", exc_info=exc)
                    except BotNetworkError as exc:
                        await message.reply_text("获取图片详细信息时发生致命错误，详情请查看日志")
                        logger.error("获取图片详细信息时发生致命错误", exc_info=exc)
                    except Exception as exc:
                        await message.reply_text("获取图片详细信息时发生致命错误，详情请查看日志")
                        logger.error("获取图片详细信息时发生致命错误", exc_info=exc)

        await message.reply_text("找不到 URL 或 Review 信息")
        return ConversationHandler.END

    async def get_work(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        bot = context.bot

        def get_callback_query(callback_query_data: str) -> Tuple[int, str, int]:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            _site_key = _data[2]
            _artwork_id = int(_data[3])
            return _work_id, _site_key, _artwork_id

        work_id, site_key, artwork_id = get_callback_query(callback_query.data)
        review_info = await self.review_service.repository.get_review(work_id, site_key, artwork_id)
        if review_info is not None:
            await message.reply_text("警告！当前 Work 中审核已经存在该作品，继续会覆盖该审核信息！")
        work = await self.work_service.get_by_work_id(work_id)
        if work is None:
            await message.delete()
            return ConversationHandler.END
        work_channel = await self.work_service.get_work_channel_by_work_id(work_id)
        if work_channel is None:
            await message.delete()
            return ConversationHandler.END
        channel_info = await bot.get_chat(work_channel.channel_id)
        text = (
            f"工作名称:{work.name}\n"
            f"作品ID:{artwork_id}\n"
            f"推送的频道:[{channel_info.id}]{channel_info.full_name}\n"
            f"请确认推送信息"
        )
        keyboard = [
            [
                InlineKeyboardButton(text="确认", callback_data=f"send_artwork|{work.id}|{site_key}|{artwork_id}"),
            ],
            [
                InlineKeyboardButton(text="退出", callback_data="exit"),
            ],
        ]
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return SEND

    async def send_artwork(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        callback_query = update.callback_query
        bot = context.bot

        def get_callback_query(callback_query_data: str) -> Tuple[int, str, int]:
            _data = callback_query_data.split("|")
            _work_id = int(_data[1])
            _site_key = _data[2]
            _artwork_id = int(_data[3])
            return _work_id, _site_key, _artwork_id

        work_id, site_key, artwork_id = get_callback_query(callback_query.data)
        site = self.sites_manager.get_site_by_site_key(site_key)
        work = await self.work_service.get_by_work_id(work_id)

        if work is None:
            await message.delete()
            return ConversationHandler.END
        work_channel = await self.work_service.get_work_channel_by_work_id(work_id)
        if work_channel is None:
            await message.delete()
            return ConversationHandler.END
        send_message: Optional["Message"] = None

        try:
            artwork = await site.get_artwork(artwork_id)
            artwork_images = await site.get_artwork_images(artwork_id)
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
                send_message = await bot.send_media_group(
                    chat_id=work_channel.channel_id,
                    media=media,
                    connect_timeout=10,
                    read_timeout=10,
                    write_timeout=30,
                )
            elif len(artwork_images) == 1:
                if artwork.image_type == ImageType.STATIC:
                    send_message = await bot.send_photo(
                        chat_id=work_channel.channel_id,
                        photo=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                elif artwork.image_type == ImageType.DYNAMIC:
                    send_message = await bot.send_video(
                        chat_id=work_channel.channel_id,
                        video=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
            else:
                raise RuntimeError
        except ArtWorkNotFoundError:
            await message.reply_text("作品不存在")
            return ConversationHandler.END
        except BadRequest as exc:
            await message.edit_text(f"推送时发生错误：\n{exc.message}")
            logger.warning("推送时发生致命错误", exc_info=exc)
            return ConversationHandler.END
        except BotBadRequest as exc:
            await message.edit_text("推送时发生致命错误，详情请查看日志")
            logger.error("推送时发生致命错误", exc_info=exc)
            return ConversationHandler.END
        except BotNetworkError as exc:
            await message.edit_text("推送时发生致命错误，详情请查看日志")
            logger.error("推送时发生致命错误", exc_info=exc)
            return ConversationHandler.END
        except Exception as exc:
            await message.edit_text("推送时发生致命错误，详情请查看日志")
            logger.error("推送时发生致命错误", exc_info=exc)
            return ConversationHandler.END

        review_info = await self.review_service.set_send_review(work_id, site_key, artwork_id, user.id)
        await self.push_service.set_send_push(review_info.id, send_message.chat_id, send_message.id, True, user.id)
        await message.edit_text("推送完成")

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
