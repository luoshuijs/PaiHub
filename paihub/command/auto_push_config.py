import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from croniter import croniter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.jobs.auto_push import AutoPushJob
from paihub.log import logger
from paihub.system.push.auto_push_entities import AutoPushConfig, AutoPushMode, AutoPushStatus
from paihub.system.push.auto_push_repositories import AutoPushConfigRepository
from paihub.system.work.services import WorkService

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

(
    SELECT_ACTION,
    SELECT_WORK,
    INPUT_NAME,
    INPUT_DESCRIPTION,
    SELECT_MODE,
    INPUT_CRON,
    INPUT_COUNT,
    SELECT_PUSH_TO_OWNER,
    SELECT_RUN_ONCE,
    CONFIRM_CREATE,
    MANAGE_CONFIG,
) = range(11)


class AutoPushConfigCommand(Command):
    """自动推送配置管理命令"""

    def __init__(
        self,
        config_repository: AutoPushConfigRepository,
        work_service: WorkService,
        auto_push_job: AutoPushJob,
    ):
        self.config_repository = config_repository
        self.work_service = work_service
        self.auto_push_job = auto_push_job

    def add_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("auto_push_config", self.start, block=False), self.application)],
            states={
                SELECT_ACTION: [
                    CallbackQueryHandler(self.create_config, pattern=r"^auto_push_create$", block=False),
                    CallbackQueryHandler(self.list_configs, pattern=r"^auto_push_list$", block=False),
                ],
                SELECT_WORK: [CallbackQueryHandler(self.select_work, pattern=r"^auto_push_work\|", block=False)],
                INPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_name, block=False)],
                INPUT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_description, block=False)
                ],
                SELECT_MODE: [CallbackQueryHandler(self.select_mode, pattern=r"^auto_push_mode\|", block=False)],
                INPUT_CRON: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_cron, block=False)],
                INPUT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_count, block=False)],
                SELECT_PUSH_TO_OWNER: [
                    CallbackQueryHandler(self.select_push_to_owner, pattern=r"^auto_push_owner\|", block=False)
                ],
                SELECT_RUN_ONCE: [
                    CallbackQueryHandler(self.select_run_once, pattern=r"^auto_push_run_once\|", block=False)
                ],
                CONFIRM_CREATE: [
                    CallbackQueryHandler(self.confirm_create, pattern=r"^auto_push_confirm$", block=False),
                    CallbackQueryHandler(self.start, pattern=r"^auto_push_cancel$", block=False),
                ],
                MANAGE_CONFIG: [
                    CallbackQueryHandler(self.toggle_config, pattern=r"^auto_push_toggle\|", block=False),
                    CallbackQueryHandler(self.enable_config, pattern=r"^auto_push_enable\|", block=False),
                    CallbackQueryHandler(self.disable_config, pattern=r"^auto_push_disable\|", block=False),
                    CallbackQueryHandler(self.execute_now, pattern=r"^auto_push_execute\|", block=False),
                    CallbackQueryHandler(self.delete_config, pattern=r"^auto_push_delete\|", block=False),
                    CallbackQueryHandler(self.list_configs, pattern=r"^auto_push_back$", block=False),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^auto_push_exit$"),
            ],
        )
        self.bot.add_handler(conv_handler)

    async def start(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """开始配置管理"""
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 auto_push_config 命令", user.full_name, user.id)

        keyboard = [
            [InlineKeyboardButton(text="创建新配置", callback_data="auto_push_create")],
            [InlineKeyboardButton(text="查看配置列表", callback_data="auto_push_list")],
            [InlineKeyboardButton(text="退出", callback_data="auto_push_exit")],
        ]

        await message.reply_html(
            f"你好 {user.mention_html()} ！\n"
            "欢迎使用自动推送配置管理\n\n"
            "自动推送功能可以定时自动审核和推送作品\n"
            "请选择你要进行的操作：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_ACTION

    async def create_config(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """创建新配置 - 选择工作"""
        message = update.effective_message
        user = update.effective_user

        works = await self.work_service.get_all()
        if not works:
            await message.edit_text("暂无可用的工作，请先创建工作")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(text=work.name, callback_data=f"auto_push_work|{work.id}")] for work in works]
        keyboard.append([InlineKeyboardButton(text="返回", callback_data="auto_push_exit")])

        context.user_data["auto_push_create_by"] = user.id
        await message.edit_text("请选择要配置自动推送的工作：", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_WORK

    async def select_work(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """选择工作后，输入配置名称"""
        message = update.effective_message
        callback_query = update.callback_query

        work_id = int(callback_query.data.split("|")[1])
        context.user_data["auto_push_work_id"] = work_id

        await message.edit_text("请输入配置名称（例如：每日定时推送）：")
        return INPUT_NAME

    async def input_name(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """输入名称后，输入描述"""
        message = update.effective_message
        name = message.text.strip()

        if not name or len(name) > 255:
            await message.reply_text("名称不能为空且不超过255个字符，请重新输入：")
            return INPUT_NAME

        context.user_data["auto_push_name"] = name
        await message.reply_text("请输入配置描述（可选，直接发送 '-' 跳过）：")
        return INPUT_DESCRIPTION

    async def input_description(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """输入描述后，选择模式"""
        message = update.effective_message
        description = message.text.strip()

        if description != "-":
            if len(description) > 500:
                await message.reply_text("描述不超过500个字符，请重新输入：")
                return INPUT_DESCRIPTION
            context.user_data["auto_push_description"] = description
        else:
            context.user_data["auto_push_description"] = None

        keyboard = [
            [InlineKeyboardButton(text="批量模式（先审核后推送）", callback_data="auto_push_mode|0")],
            [InlineKeyboardButton(text="即时模式（边审核边推送）", callback_data="auto_push_mode|1")],
        ]

        await message.reply_text(
            "请选择推送模式：\n\n"
            "• 批量模式：先自动审核指定数量的作品，全部审核完成后统一推送\n"
            "• 即时模式：每审核通过一个作品，立即推送一个",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_MODE

    async def select_mode(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """选择模式后，输入cron表达式"""
        message = update.effective_message
        callback_query = update.callback_query

        mode = int(callback_query.data.split("|")[1])
        context.user_data["auto_push_mode"] = mode

        await message.edit_text(
            "请输入定时执行的Cron表达式：\n\n"
            "示例：\n"
            "• 每6小时执行：0 */6 * * *\n"
            "• 每天凌晨3点执行：0 3 * * *\n"
            "• 每周一早上8点执行：0 8 * * 1\n\n"
            "直接发送 '-' 使用默认值（每6小时）"
        )
        return INPUT_CRON

    async def input_cron(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """输入cron表达式后，输入审核数量"""
        message = update.effective_message
        cron_expr = message.text.strip()

        if cron_expr == "-":
            cron_expr = "0 */6 * * *"
        else:
            # 验证cron表达式
            try:
                croniter(cron_expr, datetime.now())
            except Exception:
                await message.reply_text("Cron表达式格式错误，请重新输入：")
                return INPUT_CRON

        context.user_data["auto_push_cron"] = cron_expr
        await message.reply_text("请输入每次自动审核的数量（直接发送 '-' 使用默认值10）：")
        return INPUT_COUNT

    async def input_count(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """输入审核数量后，选择是否同步到owner"""
        message = update.effective_message
        count_text = message.text.strip()

        if count_text == "-":
            count = 10
        else:
            try:
                count = int(count_text)
                if count <= 0 or count > 100:
                    await message.reply_text("数量必须在1-100之间，请重新输入：")
                    return INPUT_COUNT
            except ValueError:
                await message.reply_text("请输入有效的数字：")
                return INPUT_COUNT

        context.user_data["auto_push_count"] = count

        keyboard = [
            [InlineKeyboardButton(text="是（推荐）", callback_data="auto_push_owner|1")],
            [InlineKeyboardButton(text="否", callback_data="auto_push_owner|0")],
        ]

        await message.reply_text(
            "是否同步发送到BOT_OWNER？\n\n"
            "启用后，所有自动审核通过的作品都会同步发送给管理员，\n"
            "方便随时撤回或删除已推送的内容。",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_PUSH_TO_OWNER

    async def select_push_to_owner(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """选择是否同步到owner后，选择是否仅运行一次"""
        message = update.effective_message
        callback_query = update.callback_query

        push_to_owner = bool(int(callback_query.data.split("|")[1]))
        context.user_data["auto_push_to_owner"] = push_to_owner

        keyboard = [
            [InlineKeyboardButton(text="否（可重复执行）", callback_data="auto_push_run_once|0")],
            [InlineKeyboardButton(text="是（执行一次后自动禁用）", callback_data="auto_push_run_once|1")],
        ]

        await message.edit_text(
            "是否仅运行一次？\n\n• 否：按照Cron表达式定期执行\n• 是：执行一次后自动禁用配置（适合一次性任务或测试）",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_RUN_ONCE

    async def select_run_once(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """选择是否仅运行一次后，确认创建"""
        message = update.effective_message
        callback_query = update.callback_query

        run_once = bool(int(callback_query.data.split("|")[1]))
        context.user_data["auto_push_run_once"] = run_once

        # 显示配置摘要
        mode_text = "批量模式" if context.user_data["auto_push_mode"] == 0 else "即时模式"
        summary = (
            "请确认配置信息：\n\n"
            f"名称：{context.user_data['auto_push_name']}\n"
            f"描述：{context.user_data.get('auto_push_description', '无')}\n"
            f"模式：{mode_text}\n"
            f"定时执行：{context.user_data['auto_push_cron']}\n"
            f"审核数量：{context.user_data['auto_push_count']}\n"
            f"同步到管理员：{'是' if context.user_data['auto_push_to_owner'] else '否'}\n"
            f"仅运行一次：{'是' if run_once else '否'}\n\n"
            "确认创建吗？"
        )

        keyboard = [
            [
                InlineKeyboardButton(text="确认创建", callback_data="auto_push_confirm"),
                InlineKeyboardButton(text="取消", callback_data="auto_push_cancel"),
            ]
        ]

        await message.edit_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_CREATE

    async def confirm_create(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """确认创建配置"""
        message = update.effective_message
        user = update.effective_user

        # 创建配置对象
        config = AutoPushConfig(
            work_id=context.user_data["auto_push_work_id"],
            name=context.user_data["auto_push_name"],
            description=context.user_data.get("auto_push_description"),
            mode=AutoPushMode(context.user_data["auto_push_mode"]),
            status=AutoPushStatus.DISABLED,  # 默认禁用，需要手动启用
            cron_expression=context.user_data["auto_push_cron"],
            review_count=context.user_data["auto_push_count"],
            push_to_owner=context.user_data["auto_push_to_owner"],
            run_once=context.user_data.get("auto_push_run_once", False),
            create_by=user.id,
        )

        # 计算下次运行时间
        config.next_run_time = self.auto_push_job._calculate_next_run_time(config.cron_expression)

        # 保存配置名称 在保存到数据库前获取避免 DetachedInstanceError
        config_name = config.name

        # 保存到数据库
        await self.config_repository.add(config)

        await message.edit_text(
            f"✅ 配置创建成功！\n\n"
            f"配置名称：{config_name}\n"
            f"当前状态：已禁用\n\n"
            f"请使用 /auto_push_config 命令查看配置列表并启用配置。"
        )

        # 清理用户数据
        for key in list(context.user_data.keys()):
            if key.startswith("auto_push_"):
                del context.user_data[key]

        return ConversationHandler.END

    async def list_configs(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """查看配置列表"""
        message = update.effective_message

        all_configs = await self.config_repository.get_all()

        if not all_configs:
            await message.edit_text("暂无配置，请先创建配置")
            return ConversationHandler.END

        text = "自动推送配置列表：\n\n"
        keyboard = []

        for config in all_configs:
            status_emoji = "✅" if config.status == AutoPushStatus.ENABLED else "❌"
            mode_text = "批量" if config.mode == AutoPushMode.BATCH else "即时"
            text += (
                f"{status_emoji} {config.name}\n"
                f"  模式：{mode_text} | 数量：{config.review_count}\n"
                f"  定时：{config.cron_expression}\n\n"
            )
            keyboard.append(
                [
                    InlineKeyboardButton(text=f"管理 - {config.name}", callback_data=f"auto_push_toggle|{config.id}"),
                ]
            )

        keyboard.append([InlineKeyboardButton(text="返回", callback_data="auto_push_exit")])

        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MANAGE_CONFIG

    async def toggle_config(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """管理单个配置"""
        message = update.effective_message
        callback_query = update.callback_query

        config_id = int(callback_query.data.split("|")[1])
        config = await self.config_repository.get_by_id(config_id)

        if not config:
            await message.edit_text("配置不存在")
            return ConversationHandler.END

        mode_text = "批量模式" if config.mode == AutoPushMode.BATCH else "即时模式"
        status_text = {
            AutoPushStatus.DISABLED: "已禁用",
            AutoPushStatus.ENABLED: "已启用",
            AutoPushStatus.RUNNING: "运行中",
            AutoPushStatus.PAUSED: "已暂停",
        }[config.status]

        text = (
            f"配置详情：\n\n"
            f"名称：{config.name}\n"
            f"描述：{config.description or '无'}\n"
            f"状态：{status_text}\n"
            f"模式：{mode_text}\n"
            f"定时执行：{config.cron_expression}\n"
            f"审核数量：{config.review_count}\n"
            f"同步到管理员：{'是' if config.push_to_owner else '否'}\n"
            f"仅运行一次：{'是' if config.run_once else '否'}\n"
            f"上次运行：{config.last_run_time.strftime('%Y-%m-%d %H:%M') if config.last_run_time else '未运行'}\n"
            f"下次运行：{config.next_run_time.strftime('%Y-%m-%d %H:%M') if config.next_run_time else '未设置'}\n"
        )

        keyboard = []
        if config.status == AutoPushStatus.ENABLED:
            keyboard.append([InlineKeyboardButton(text="禁用配置", callback_data=f"auto_push_disable|{config.id}")])
        else:
            keyboard.append([InlineKeyboardButton(text="启用配置", callback_data=f"auto_push_enable|{config.id}")])

        keyboard.append([InlineKeyboardButton(text="🚀 立即执行一次", callback_data=f"auto_push_execute|{config.id}")])
        keyboard.append([InlineKeyboardButton(text="删除配置", callback_data=f"auto_push_delete|{config.id}")])
        keyboard.append([InlineKeyboardButton(text="返回列表", callback_data="auto_push_back")])

        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MANAGE_CONFIG

    async def delete_config(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """删除配置"""
        message = update.effective_message
        callback_query = update.callback_query

        config_id = int(callback_query.data.split("|")[1])
        config = await self.config_repository.get_by_id(config_id)

        if config:
            await self.config_repository.remove(config)
            await message.edit_text(f"✅ 配置 '{config.name}' 已删除")
        else:
            await message.edit_text("配置不存在")

        return ConversationHandler.END

    async def enable_config(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """启用配置"""
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        config_id = int(callback_query.data.split("|")[1])
        config = await self.config_repository.get_by_id(config_id)

        if config:
            config.enable(user.id)
            # 如果没有下次运行时间，计算一个
            if not config.next_run_time:
                config.next_run_time = self.auto_push_job._calculate_next_run_time(config.cron_expression)
            await self.config_repository.update(config)
            await message.edit_text(f"✅ 配置 '{config.name}' 已启用")
            # 返回配置详情
            return await self.toggle_config(update, _)
        await message.edit_text("配置不存在")
        return ConversationHandler.END

    async def disable_config(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """禁用配置"""
        message = update.effective_message
        callback_query = update.callback_query
        user = update.effective_user

        config_id = int(callback_query.data.split("|")[1])
        config = await self.config_repository.get_by_id(config_id)

        if config:
            config.disable(user.id)
            await self.config_repository.update(config)
            await message.edit_text(f"✅ 配置 '{config.name}' 已禁用")
            # 返回配置详情
            return await self.toggle_config(update, _)
        await message.edit_text("配置不存在")
        return ConversationHandler.END

    async def execute_now(self, update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """立即执行一次配置"""
        message = update.effective_message
        callback_query = update.callback_query

        config_id = int(callback_query.data.split("|")[1])
        config = await self.config_repository.get_by_id(config_id)

        if not config:
            await message.edit_text("配置不存在")
            return ConversationHandler.END

        # 检查是否正在运行
        if config.status == AutoPushStatus.RUNNING:
            await message.edit_text("⚠️ 该配置正在运行中，请等待完成后再试")
            return await self.toggle_config(update, _)

        # 立即执行
        await message.edit_text(f"🚀 开始立即执行配置 '{config.name}'...")

        # 异步执行任务
        asyncio.create_task(self.auto_push_job.execute_auto_push_task(config))

        await message.edit_text(
            "✅ 任务已提交执行\n\n"
            "执行过程将在后台进行，可以通过日志查看执行情况。\n"
            "注意：此次执行不会影响原定的定时计划。"
        )

        # 返回配置详情
        return await self.toggle_config(update, _)

    @staticmethod
    async def cancel(update: "Update", _: "ContextTypes.DEFAULT_TYPE"):
        """取消操作"""
        message = update.effective_message
        callback_query = update.callback_query
        if callback_query is None:
            await message.reply_text("已退出配置管理", reply_markup=ReplyKeyboardRemove())
        else:
            await message.edit_text("已退出配置管理")
        return ConversationHandler.END
