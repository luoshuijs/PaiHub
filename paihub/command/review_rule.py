from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.log import logger
from paihub.system.review.entities import ReviewAuthorRule, ReviewAuthorRuleAction
from paihub.system.review.services import ReviewService
from paihub.system.sites.manager import SitesManager
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


(
    SELECT_ACTION,
    SELECT_CREATE_WORK,
    SELECT_CREATE_SITE,
    SELECT_CREATE_ACTION,
    INPUT_AUTHOR_ID,
    INPUT_REASON,
    LIST_RULES,
) = range(7)


class ReviewRuleCommand(Command):
    def __init__(self, work_service: WorkService, review_service: ReviewService, sites_manager: SitesManager):
        self.work_service = work_service
        self.review_service = review_service
        self.sites_manager = sites_manager

    @staticmethod
    def format_action(action: ReviewAuthorRuleAction) -> str:
        if action == ReviewAuthorRuleAction.AUTO_PASS:
            return "白名单 / 自动通过"
        return "黑名单 / 自动拒绝"

    @staticmethod
    def build_main_keyboard() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(text="新增规则", callback_data="review_rule_create")],
            [InlineKeyboardButton(text="查看规则", callback_data="review_rule_list")],
            [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_post_save_keyboard(work_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(text="查看当前 Work 规则", callback_data=f"review_rule_list_work|{work_id}")],
            [InlineKeyboardButton(text="继续新增", callback_data="review_rule_create")],
            [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_work_keyboard(callback_prefix: str, works: list) -> InlineKeyboardMarkup:
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=work.name, callback_data=f"{callback_prefix}|{work.id}")] for work in works
        ]
        keyboard.append([InlineKeyboardButton(text="主菜单", callback_data="review_rule_menu")])
        keyboard.append([InlineKeyboardButton(text="退出", callback_data="review_rule_exit")])
        return InlineKeyboardMarkup(keyboard)

    def build_site_keyboard(self) -> InlineKeyboardMarkup:
        sites = sorted(self.sites_manager.get_all_sites(), key=lambda site: site.site_key)
        keyboard = [
            [InlineKeyboardButton(text=site.site_name, callback_data=f"review_rule_site|{site.site_key}")]
            for site in sites
        ]
        keyboard.append([InlineKeyboardButton(text="主菜单", callback_data="review_rule_menu")])
        keyboard.append([InlineKeyboardButton(text="退出", callback_data="review_rule_exit")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_action_keyboard() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton(text="白名单自动通过", callback_data="review_rule_action|1")],
            [InlineKeyboardButton(text="黑名单自动拒绝", callback_data="review_rule_action|0")],
            [InlineKeyboardButton(text="主菜单", callback_data="review_rule_menu")],
            [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_site_name(self, site_key: str) -> str:
        try:
            return self.sites_manager.get_site_by_site_key(site_key).site_name
        except KeyError:
            return site_key

    @staticmethod
    def clear_create_data(context: "ContextTypes.DEFAULT_TYPE") -> None:
        for key in ("review_rule_work_id", "review_rule_site_key", "review_rule_action", "review_rule_author_id"):
            context.user_data.pop(key, None)

    async def reply_or_edit(self, update: "Update", text: str, reply_markup: InlineKeyboardMarkup) -> None:
        message = update.effective_message
        if update.callback_query is None:
            await message.reply_text(text, reply_markup=reply_markup)
            return
        await message.edit_text(text, reply_markup=reply_markup)

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("review_rule", self.start, block=False), self.application)],
            states={
                SELECT_ACTION: [
                    CallbackQueryHandler(self.start, pattern=r"^review_rule_menu$", block=False),
                    CallbackQueryHandler(self.start_create, pattern=r"^review_rule_create$", block=False),
                    CallbackQueryHandler(self.start_list, pattern=r"^review_rule_list$", block=False),
                    CallbackQueryHandler(self.show_rule_list, pattern=r"^review_rule_list_work\|", block=False),
                ],
                SELECT_CREATE_WORK: [
                    CallbackQueryHandler(self.start, pattern=r"^review_rule_menu$", block=False),
                    CallbackQueryHandler(self.select_create_work, pattern=r"^review_rule_create_work\|", block=False),
                ],
                SELECT_CREATE_SITE: [
                    CallbackQueryHandler(self.start, pattern=r"^review_rule_menu$", block=False),
                    CallbackQueryHandler(self.select_site, pattern=r"^review_rule_site\|", block=False),
                ],
                SELECT_CREATE_ACTION: [
                    CallbackQueryHandler(self.start, pattern=r"^review_rule_menu$", block=False),
                    CallbackQueryHandler(self.select_action, pattern=r"^review_rule_action\|", block=False),
                ],
                INPUT_AUTHOR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_author_id, block=False)],
                INPUT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_reason, block=False)],
                LIST_RULES: [
                    CallbackQueryHandler(self.start, pattern=r"^review_rule_menu$", block=False),
                    CallbackQueryHandler(self.start_create, pattern=r"^review_rule_create$", block=False),
                    CallbackQueryHandler(self.start_list, pattern=r"^review_rule_list$", block=False),
                    CallbackQueryHandler(self.show_rule_list, pattern=r"^review_rule_list_work\|", block=False),
                    CallbackQueryHandler(self.show_rule_detail, pattern=r"^review_rule_detail\|", block=False),
                    CallbackQueryHandler(self.delete_rule, pattern=r"^review_rule_delete\|", block=False),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^review_rule_exit$"),
            ],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        user = update.effective_user
        logger.info("用户 %s[%s] 发出 review_rule 命令", user.full_name, user.id)
        await self.reply_or_edit(update, "作者规则管理\n请选择你要进行的操作", self.build_main_keyboard())
        return SELECT_ACTION

    async def start_create(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        works = await self.work_service.get_all()
        if not works:
            await self.reply_or_edit(update, "暂无可用 Work，无法创建作者规则", self.build_main_keyboard())
            return SELECT_ACTION
        self.clear_create_data(context)
        await self.reply_or_edit(
            update,
            "请选择要生效的 Work",
            self.build_work_keyboard("review_rule_create_work", works),
        )
        return SELECT_CREATE_WORK

    async def start_list(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        works = await self.work_service.get_all()
        if not works:
            await self.reply_or_edit(update, "暂无可用 Work，无法查看作者规则", self.build_main_keyboard())
            return SELECT_ACTION
        await self.reply_or_edit(
            update,
            "请选择要查看规则的 Work",
            self.build_work_keyboard("review_rule_list_work", works),
        )
        return LIST_RULES

    async def select_create_work(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        work_id = int(callback_query.data.split("|")[1])
        context.user_data["review_rule_work_id"] = work_id
        await message.edit_text("请选择站点", reply_markup=self.build_site_keyboard())
        return SELECT_CREATE_SITE

    async def select_site(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        site_key = callback_query.data.split("|")[1]
        context.user_data["review_rule_site_key"] = site_key
        await message.edit_text("请选择规则动作", reply_markup=self.build_action_keyboard())
        return SELECT_CREATE_ACTION

    async def select_action(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        action = int(callback_query.data.split("|")[1])
        context.user_data["review_rule_action"] = action
        await message.edit_text("请输入作者 ID")
        return INPUT_AUTHOR_ID

    async def input_author_id(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        author_id_text = message.text.strip()
        try:
            author_id = int(author_id_text)
        except ValueError:
            await message.reply_text("作者 ID 必须是数字，请重新输入")
            return INPUT_AUTHOR_ID
        if author_id <= 0:
            await message.reply_text("作者 ID 必须大于 0，请重新输入")
            return INPUT_AUTHOR_ID
        context.user_data["review_rule_author_id"] = author_id
        await message.reply_text("请输入规则说明，直接发送 `-` 跳过")
        return INPUT_REASON

    async def input_reason(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        reason_text = message.text.strip()
        if reason_text == "-":
            reason = None
        else:
            if len(reason_text) > 255:
                await message.reply_text("规则说明不能超过 255 个字符，请重新输入")
                return INPUT_REASON
            reason = reason_text

        work_id = context.user_data.get("review_rule_work_id")
        site_key = context.user_data.get("review_rule_site_key")
        action = context.user_data.get("review_rule_action")
        author_id = context.user_data.get("review_rule_author_id")
        if work_id is None or site_key is None or action is None or author_id is None:
            await message.reply_text("创建上下文已丢失，请重新执行 /review_rule")
            self.clear_create_data(context)
            return ConversationHandler.END

        rule_action = ReviewAuthorRuleAction.AUTO_PASS if action == 1 else ReviewAuthorRuleAction.AUTO_REJECT
        await self.review_service.set_author_rule(
            work_id=work_id,
            site_key=site_key,
            author_id=author_id,
            action=rule_action,
            update_by=update.effective_user.id,
            reason=reason,
        )
        self.clear_create_data(context)
        await message.reply_text(
            f"规则已保存\nWork ID: {work_id}\n站点: {self.get_site_name(site_key)}\n"
            f"作者 ID: {author_id}\n动作: {self.format_action(rule_action)}",
            reply_markup=self.build_post_save_keyboard(work_id),
        )
        return SELECT_ACTION

    def build_rule_list_keyboard(self, rules: list[ReviewAuthorRule]) -> InlineKeyboardMarkup:
        keyboard: list[list[InlineKeyboardButton]] = []
        for rule in rules:
            button_text = f"{rule.site_key}:{rule.author_id}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"review_rule_detail|{rule.id}")])
        keyboard.append([InlineKeyboardButton(text="新增规则", callback_data="review_rule_create")])
        keyboard.append([InlineKeyboardButton(text="主菜单", callback_data="review_rule_menu")])
        keyboard.append([InlineKeyboardButton(text="退出", callback_data="review_rule_exit")])
        return InlineKeyboardMarkup(keyboard)

    async def show_rule_list(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        callback_query = update.callback_query
        work_id = int(callback_query.data.split("|")[1])
        work = await self.work_service.get_work_by_id(work_id)
        if work is None:
            await self.reply_or_edit(update, "目标 Work 不存在", self.build_main_keyboard())
            return SELECT_ACTION

        rules = await self.review_service.get_author_rules_by_work(work_id)
        if not rules:
            keyboard = [
                [InlineKeyboardButton(text="新增规则", callback_data="review_rule_create")],
                [InlineKeyboardButton(text="返回 Work 列表", callback_data="review_rule_list")],
                [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
            ]
            await update.effective_message.edit_text(
                f"Work: {work.name}\n当前没有作者规则",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return LIST_RULES

        lines = [f"Work: {work.name}", f"规则数: {len(rules)}", ""]
        for index, rule in enumerate(rules, start=1):
            lines.append(f"{index}. [{rule.site_key}] {rule.author_id} - {self.format_action(rule.action)}")
        await update.effective_message.edit_text(
            "\n".join(lines),
            reply_markup=self.build_rule_list_keyboard(rules),
        )
        return LIST_RULES

    async def show_rule_detail(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        rule_id = int(callback_query.data.split("|")[1])
        rule = await self.review_service.get_author_rule_by_id(rule_id)
        if rule is None:
            await message.edit_text("规则不存在", reply_markup=self.build_main_keyboard())
            return SELECT_ACTION

        work = await self.work_service.get_work_by_id(rule.work_id)
        work_name = work.name if work is not None else f"WorkId[{rule.work_id}]"
        reason_text = rule.reason or "无"
        text = (
            f"Work: {work_name}\n"
            f"站点: {self.get_site_name(rule.site_key)} ({rule.site_key})\n"
            f"作者 ID: {rule.author_id}\n"
            f"动作: {self.format_action(rule.action)}\n"
            f"说明: {reason_text}"
        )
        keyboard = [
            [InlineKeyboardButton(text="删除规则", callback_data=f"review_rule_delete|{rule.id}")],
            [InlineKeyboardButton(text="返回列表", callback_data=f"review_rule_list_work|{rule.work_id}")],
            [InlineKeyboardButton(text="新增规则", callback_data="review_rule_create")],
            [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
        ]
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return LIST_RULES

    async def delete_rule(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        rule_id = int(callback_query.data.split("|")[1])
        rule = await self.review_service.get_author_rule_by_id(rule_id)
        if rule is None:
            await message.edit_text("规则不存在", reply_markup=self.build_main_keyboard())
            return SELECT_ACTION

        work_id = rule.work_id
        await self.review_service.remove_author_rule_by_id(rule_id)

        rules = await self.review_service.get_author_rules_by_work(work_id)
        work = await self.work_service.get_work_by_id(work_id)
        work_name = work.name if work is not None else f"WorkId[{work_id}]"
        if not rules:
            keyboard = [
                [InlineKeyboardButton(text="新增规则", callback_data="review_rule_create")],
                [InlineKeyboardButton(text="返回 Work 列表", callback_data="review_rule_list")],
                [InlineKeyboardButton(text="退出", callback_data="review_rule_exit")],
            ]
            await message.edit_text(
                f"规则已删除\n\nWork: {work_name}\n当前没有作者规则",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return LIST_RULES

        lines = ["规则已删除", "", f"Work: {work_name}", f"规则数: {len(rules)}", ""]
        for index, item in enumerate(rules, start=1):
            lines.append(f"{index}. [{item.site_key}] {item.author_id} - {self.format_action(item.action)}")
        await message.edit_text(
            "\n".join(lines),
            reply_markup=self.build_rule_list_keyboard(rules),
        )
        return LIST_RULES

    @staticmethod
    async def cancel(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        message = update.effective_message
        callback_query = update.callback_query
        if callback_query is None:
            await message.reply_text("退出命令", reply_markup=ReplyKeyboardRemove())
        else:
            await message.edit_text("退出命令")
        return ConversationHandler.END
