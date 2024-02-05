from typing import TypeVar, TYPE_CHECKING, Any, Optional

from telegram import Update
from telegram.ext import ApplicationHandlerStop, BaseHandler

from paihub.log import logger
from paihub.system.user.services import UserAdminService

if TYPE_CHECKING:
    from paihub.application import Application
    from telegram.ext import Application as TelegramApplication

RT = TypeVar("RT")
UT = TypeVar("UT")

CCT = TypeVar("CCT", bound="CallbackContext[Any, Any, Any, Any]")


class AdminHandler(BaseHandler[Update, CCT]):
    def __init__(self, handler: BaseHandler[Update, CCT], application: "Application") -> None:
        self.handler = handler
        self.application = application
        self.user_service: Optional["UserAdminService"] = None
        super().__init__(self.handler.callback, self.handler.block)

    def check_update(self, update: object) -> bool:
        if not isinstance(update, Update):
            return False
        return self.handler.check_update(update)

    async def _get_user_service(self) -> "UserAdminService":
        if self.user_service is not None:
            return self.user_service
        user_service = self.application.factor.get_component(UserAdminService)
        self.user_service = user_service
        return self.user_service

    async def handle_update(
        self,
        update: "UT",
        application: "TelegramApplication[Any, CCT, Any, Any, Any, Any]",
        check_result: Any,
        context: "CCT",
    ) -> RT:
        user_service = await self._get_user_service()
        user = update.effective_user
        if await user_service.is_admin(user.id):
            return await self.handler.handle_update(update, application, check_result, context)
        message = update.effective_message
        logger.warning("用户 %s[%s] 触发尝试调用Admin命令但权限不足", user.full_name, user.id)
        await message.reply_text("权限不足")
        raise ApplicationHandlerStop
