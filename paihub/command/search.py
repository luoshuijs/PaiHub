import html
from io import BytesIO
from typing import TYPE_CHECKING

from PicImageSearch import Network, SauceNAO
from telegram import InputMediaPhoto
from telegram.error import BadRequest as BotBadRequest, NetworkError as BotNetworkError
from telegram.constants import ChatAction, ParseMode
from telegram.ext import MessageHandler, filters

from paihub.base import BaseCommand
from paihub.bot.handlers.adminhandler import AdminHandler
from paihub.entities.artwork import ImageType
from paihub.entities.config import TomlConfig
from paihub.error import ArtWorkNotFoundError, BadRequest
from paihub.system.sites.manager import SitesManager
from paihub.log import logger

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class Search(BaseCommand):
    def __init__(self, sites_manager: SitesManager):
        self.config: dict = {}
        self.config = TomlConfig(
            "config/search.toml",
        )
        self.network = Network()
        saucenao_config = self.config.get("saucenao", {})
        self.saucenao = SauceNAO(
            client=self.network, api_key=saucenao_config.get("api_key"), hide=saucenao_config.get("hide", 3)
        )
        self.sites_manager = sites_manager

    def add_handlers(self):
        self.bot.add_handler(
            AdminHandler(
                MessageHandler(filters=filters.PHOTO & filters.ChatType.PRIVATE, callback=self.photo, block=False),
                self.application,
                need_notify=False,
            )
        )

    async def shutdown(self) -> None:
        await self.network.close()

    async def photo(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        user = update.effective_user
        logger.info("用户 %s[%s] 尝试搜索图片", user.full_name, user.id)
        reply_message = await message.reply_text("正在搜索")
        await message.reply_chat_action(ChatAction.TYPING)
        photo_file = await message.photo[-1].get_file()
        out = BytesIO()
        try:
            await photo_file.download_to_memory(out, read_timeout=10)
            result = await self.saucenao.search(file=out.getvalue())
        finally:
            out.close()
        if result.status_code != 200:
            await reply_message.edit_text(f"请求错误 [status_code]{result.status_code}")
            return
        if result.status != 0:
            await reply_message.edit_text(f"请求错误 [status]{result.status}")
            return
        await reply_message.edit_text("正在获取图片信息")
        for raw in result.raw:
            if raw.similarity >= 50:
                if raw.url:
                    url = raw.url
                    logger.info("图片搜索结果 [title]%s [url]%s", raw.title, url)
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
                                    f"By <a href='{artwork.author.url if not artwork.is_sourced else artwork.source}'>"
                                    f"{artwork.author.name if not artwork.is_sourced else 'Source'}</a>\n"
                                    f"At {artwork.create_time.strftime('%Y-%m-%d %H:%M')}"
                                )
                                if len(artwork_images) > 1:
                                    media = [
                                        InputMediaPhoto(
                                            media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML
                                        )
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
                                await message.reply_text(
                                    f"搜索结果 [{site.site_name}]{artwork_id} [title]{raw.title} 作品不存在"
                                )
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
        await message.reply_text("搜索完成")
        await reply_message.delete()
