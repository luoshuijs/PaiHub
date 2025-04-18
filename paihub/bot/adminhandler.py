from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ApplicationHandlerStop, BaseHandler

from paihub.log import logger
from paihub.system.user.services import UserAdminService

if TYPE_CHECKING:
    from telegram.ext import Application as TelegramApplication

    from paihub.application import Application


class AdminHandler(BaseHandler):
    def __init__(self, handler: BaseHandler, application: "Application", need_notify: bool = True) -> None:
        self.handler = handler
        self.application = application
        self._user_service: UserAdminService | None = None
        self.need_notify = need_notify
        super().__init__(self.handler.callback, self.handler.block)

    def check_update(self, update: object) -> bool:
        if not isinstance(update, Update):
            return False
        return self.handler.check_update(update)

    @property
    def user_service(self) -> "UserAdminService":
        # 考虑到只是对单一变量的读取后写入 并且获取的内容唯一 不考虑加锁
        if self._user_service is not None:
            return self._user_service
        user_service = self.application.factory.get_object(UserAdminService)
        if user_service is None:
            raise RuntimeError("UserAdmin service not found")
        self._user_service = user_service
        return user_service

    async def handle_update(
        self, update: "Update", application: "TelegramApplication", check_result, context
    ) -> object | None:
        user_service = self.user_service
        user = update.effective_user
        if await user_service.is_admin(user.id):
            return await self.handler.handle_update(update, application, check_result, context)
        logger.warning("用户 %s[%s] 触发尝试调用 Admin 命令但权限不足", user.full_name, user.id)
        if self.need_notify:
            message = update.effective_message
            callback_query = update.callback_query
            if callback_query is not None:
                await message.edit_text("权限不足")
            else:
                await message.reply_text("权限不足")
        raise ApplicationHandlerStop
