import html
from typing import TYPE_CHECKING

from telegram import InputMediaPhoto
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest as BotBadRequest, NetworkError as BotNetworkError
from telegram.ext import MessageHandler, filters

from paihub.base import BaseCommand
from paihub.entities.artwork import ImageType
from paihub.error import ArtWorkNotFoundError, BadRequest
from paihub.log import logger
from paihub.system.sites.manager import SitesManager

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

URL_REGEX = r"(http|https):\/\/([\w\-\.]+)(:[0-9]+)?(\/[\w\-\.\/]*)?(\?[a-zA-Z0-9&%_\./-~-]*)?"


class URLCommand(BaseCommand):
    def __init__(self, sites_manager: SitesManager):
        self.sites_manager = sites_manager

    def add_handlers(self):
        self.bot.add_handler(
            MessageHandler(
                filters=filters.ChatType.PRIVATE & filters.Regex(URL_REGEX), callback=self.start, block=False
            )
        )

    async def start(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 尝试获取图片", user.full_name, user.id)
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
