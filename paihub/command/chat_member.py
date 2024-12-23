from typing import TYPE_CHECKING

from telegram import Chat
from telegram.ext import ChatMemberHandler

from paihub.base import BaseCommand
from paihub.bot.utils import extract_status_change
from paihub.log import logger

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class ChatMember(BaseCommand):
    owner_id: int

    def add_handlers(self):
        self.bot.add_handler(
            ChatMemberHandler(self.track_chats, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER, block=False)
        )

    async def initialize(self) -> None:
        self.owner_id = self.application.settings.bot.owner

    async def track_chats(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        result = extract_status_change(update.my_chat_member)
        if result is None:
            return
        was_member, is_member = result
        user = update.effective_user
        chat = update.effective_chat
        if chat.type == Chat.PRIVATE:
            if not was_member and is_member:
                logger.info("用户 %s[%s] 启用了机器人", user.full_name, user.id)
            elif was_member and not is_member:
                logger.info("用户 %s[%s] 屏蔽了机器人", user.full_name, user.id)
        elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
            if not was_member and is_member:
                logger.info("用户 %s[%s] 邀请BOT进入群 %s[%s]", user.full_name, user.id, chat.title, chat.id)
                if user.id != self.owner_id:
                    await chat.leave()
            elif was_member and not is_member:
                logger.info("用户 %s[%s] 从 %s[%s] 群移除Bot", user.full_name, user.id, chat.title, chat.id)
        elif not was_member and is_member:
            logger.info("用户 %s[%s] 邀请BOT进入频道 %s[%s]", user.full_name, user.id, chat.title, chat.id)
        elif was_member and not is_member:
            logger.info("用户 %s[%s] 从 %s[%s] 频道移除Bot", user.full_name, user.id, chat.title, chat.id)
