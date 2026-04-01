from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from paihub.base import Command
from paihub.bot.adminhandler import AdminHandler
from paihub.log import logger
from paihub.system.name_map.factory import NameMapFactory
from paihub.system.name_map.service import WorkTagFormatterService
from paihub.system.work.services import WorkService

# 会话状态
SELECT_WORK, SELECT_NAME_MAP, CONFIRM_CONFIG = range(3)
TOGGLE_SELECT_WORK, TOGGLE_SELECT_CONFIG = range(3, 5)
DELETE_SELECT_WORK, DELETE_SELECT_CONFIG, DELETE_CONFIRM = range(5, 8)
TEST_SELECT_WORK, TEST_INPUT_TAGS = range(8, 10)


class NameMapCommand(Command):
    """工作流 name_map 配置管理命令"""

    def __init__(
        self, work_service: WorkService, tag_formatter: WorkTagFormatterService, name_map_factory: NameMapFactory
    ):
        self.work_service = work_service
        self.tag_formatter = tag_formatter
        self.name_map_factory = name_map_factory

    def add_handlers(self):
        """注册命令处理器"""
        # 交互式配置会话
        config_conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("name_map_config", self.start_config), self.application)],
            states={
                SELECT_WORK: [CallbackQueryHandler(self.select_work, pattern=r"^nm_work\|", block=False)],
                SELECT_NAME_MAP: [CallbackQueryHandler(self.select_name_map, pattern=r"^nm_key\|", block=False)],
                CONFIRM_CONFIG: [
                    CallbackQueryHandler(self.set_priority, pattern=r"^nm_priority\|", block=False),
                    CallbackQueryHandler(self.set_global_default, pattern=r"^nm_global\|", block=False),
                    CallbackQueryHandler(self.confirm_create, pattern=r"^nm_confirm$", block=False),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^nm_cancel$"),
            ],
            name="name_map_config",
        )

        # Toggle 交互式会话
        toggle_conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("name_map_toggle", self.start_toggle), self.application)],
            states={
                TOGGLE_SELECT_WORK: [
                    CallbackQueryHandler(self.toggle_select_work, pattern=r"^toggle_work\|", block=False)
                ],
                TOGGLE_SELECT_CONFIG: [
                    CallbackQueryHandler(self.toggle_select_config, pattern=r"^toggle_config\|", block=False)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^nm_cancel$"),
            ],
            name="name_map_toggle",
        )

        # Delete 交互式会话
        delete_conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("name_map_delete", self.start_delete), self.application)],
            states={
                DELETE_SELECT_WORK: [
                    CallbackQueryHandler(self.delete_select_work, pattern=r"^delete_work\|", block=False)
                ],
                DELETE_SELECT_CONFIG: [
                    CallbackQueryHandler(self.delete_select_config, pattern=r"^delete_config\|", block=False)
                ],
                DELETE_CONFIRM: [CallbackQueryHandler(self.delete_confirm, pattern=r"^delete_confirm\|", block=False)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^nm_cancel$"),
            ],
            name="name_map_delete",
        )

        # Test 交互式会话
        test_conv_handler = ConversationHandler(
            entry_points=[AdminHandler(CommandHandler("name_map_test", self.start_test), self.application)],
            states={
                TEST_SELECT_WORK: [CallbackQueryHandler(self.test_select_work, pattern=r"^test_work\|", block=False)],
                TEST_INPUT_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.test_with_tags, block=False)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern=r"^nm_cancel$"),
            ],
            name="name_map_test",
        )

        # 添加所有会话处理器
        self.bot.add_handler(config_conv_handler)
        self.bot.add_handler(toggle_conv_handler)
        self.bot.add_handler(delete_conv_handler)
        self.bot.add_handler(test_conv_handler)

        # 其他直接命令
        handlers = [
            AdminHandler(CommandHandler("name_map_list", self.list_configs_handler), self.application),
        ]
        self.bot.add_handlers(handlers)

        logger.info("NameMapCommand handlers registered")

    async def start_config(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """开始交互式配置
        使用方法: /name_map_config
        """
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 name_map_config 命令", user.full_name, user.id)

        # 获取所有工作流
        works = await self.work_service.get_all()

        # 构建工作流选择键盘
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text="🌐 全局配置", callback_data="nm_work|global")]
        ]

        # 添加全局配置选项

        # 添加各个工作流
        for work in works:
            work_name = work.name or f"工作流 {work.id}"
            keyboard.append([InlineKeyboardButton(text=f"📁 {work_name}", callback_data=f"nm_work|{work.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.reply_text(
            f"你好 {user.mention_html()} ！\n请选择要配置 name_map 的工作流：",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_WORK

    async def select_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择工作流后，显示可用的 name_map 列表"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析选择的 work_id
        work_data = callback_query.data.split("|")[1]
        work_id = None if work_data == "global" else int(work_data)

        # 保存到 context
        context.user_data["nm_work_id"] = work_id

        # 获取工作流名称
        if work_id is None:
            work_name = "全局配置"
        else:
            work = await self.work_service.get_work_by_id(work_id)
            work_name = work.name if work and work.name else f"工作流 {work_id}"

        # 获取可用的 name_map 列表
        available_maps = self.name_map_factory.list_available_keys()

        if not available_maps:
            await message.edit_text("❌ 未找到可用的 name_map 配置文件")
            return ConversationHandler.END

        # 构建 name_map 选择键盘
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=f"🗺️ {map_key}", callback_data=f"nm_key|{map_key}")] for map_key in available_maps
        ]
        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.edit_text(
            f"已选择：{work_name}\n\n请选择要使用的 name_map：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return SELECT_NAME_MAP

    async def select_name_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择 name_map 后，显示配置选项"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析选择的 name_map_key
        name_map_key = callback_query.data.split("|")[1]

        # 保存到 context
        context.user_data["nm_key"] = name_map_key
        context.user_data["nm_priority"] = 0  # 默认优先级
        context.user_data["nm_is_global_default"] = False  # 默认不设置为全局默认

        # 构建配置选项键盘
        keyboard = [
            [
                InlineKeyboardButton(text="🔢 设置优先级 (当前: 0)", callback_data="nm_priority|set"),
            ],
            [
                InlineKeyboardButton(text="🌐 设为全局默认：否", callback_data="nm_global|toggle"),
            ],
            [
                InlineKeyboardButton(text="✅ 确认创建", callback_data="nm_confirm"),
                InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel"),
            ],
        ]

        work_id = context.user_data["nm_work_id"]
        work_name = "全局配置" if work_id is None else f"工作流 {work_id}"

        await message.edit_text(
            f"配置信息\n\n"
            f"工作流：{work_name}\n"
            f"name_map：{name_map_key}\n"
            f"优先级：0\n"
            f"全局默认：否\n\n"
            f"请调整配置选项或直接确认创建：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRM_CONFIG

    async def set_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """设置优先级（简化版：每次点击 +10）"""
        message = update.effective_message

        # 增加优先级
        current_priority = context.user_data.get("nm_priority", 0)
        new_priority = (current_priority + 10) % 110  # 0-100 循环
        context.user_data["nm_priority"] = new_priority

        # 重新构建键盘
        is_global_default = context.user_data.get("nm_is_global_default", False)
        keyboard = [
            [
                InlineKeyboardButton(text=f"🔢 设置优先级 (当前: {new_priority})", callback_data="nm_priority|set"),
            ],
            [
                InlineKeyboardButton(
                    text=f"🌐 设为全局默认：{'是' if is_global_default else '否'}",
                    callback_data="nm_global|toggle",
                ),
            ],
            [
                InlineKeyboardButton(text="✅ 确认创建", callback_data="nm_confirm"),
                InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel"),
            ],
        ]

        work_id = context.user_data["nm_work_id"]
        name_map_key = context.user_data["nm_key"]
        work_name = "全局配置" if work_id is None else f"工作流 {work_id}"

        await message.edit_text(
            f"配置信息\n\n"
            f"工作流：{work_name}\n"
            f"name_map：{name_map_key}\n"
            f"优先级：{new_priority}\n"
            f"全局默认：{'是' if is_global_default else '否'}\n\n"
            f"请调整配置选项或直接确认创建：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRM_CONFIG

    async def set_global_default(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """切换全局默认设置"""
        message = update.effective_message

        # 切换全局默认状态
        current_status = context.user_data.get("nm_is_global_default", False)
        new_status = not current_status
        context.user_data["nm_is_global_default"] = new_status

        # 重新构建键盘
        priority = context.user_data.get("nm_priority", 0)
        keyboard = [
            [
                InlineKeyboardButton(text=f"🔢 设置优先级 (当前: {priority})", callback_data="nm_priority|set"),
            ],
            [
                InlineKeyboardButton(
                    text=f"🌐 设为全局默认：{'是' if new_status else '否'}", callback_data="nm_global|toggle"
                ),
            ],
            [
                InlineKeyboardButton(text="✅ 确认创建", callback_data="nm_confirm"),
                InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel"),
            ],
        ]

        work_id = context.user_data["nm_work_id"]
        name_map_key = context.user_data["nm_key"]
        work_name = "全局配置" if work_id is None else f"工作流 {work_id}"

        await message.edit_text(
            f"配置信息\n\n"
            f"工作流：{work_name}\n"
            f"name_map：{name_map_key}\n"
            f"优先级：{priority}\n"
            f"全局默认：{'是' if new_status else '否'}\n\n"
            f"请调整配置选项或直接确认创建：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRM_CONFIG

    async def confirm_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """确认创建配置"""
        message = update.effective_message
        user = update.effective_user

        try:
            # 从 context 获取配置参数
            work_id = context.user_data["nm_work_id"]
            name_map_key = context.user_data["nm_key"]
            priority = context.user_data.get("nm_priority", 0)
            is_global_default = context.user_data.get("nm_is_global_default", False)

            # 检查工作流是否存在
            if work_id is not None:
                work = await self.work_service.get_work_by_id(work_id)
                if not work:
                    await message.edit_text(f"❌ 工作流 {work_id} 不存在")
                    return ConversationHandler.END

            # 创建配置
            config = await self.tag_formatter.create_config(
                work_id=work_id,
                name_map_key=name_map_key,
                priority=priority,
                is_global_default=is_global_default,
            )

            work_name = "全局配置" if work_id is None else f"工作流 {work_id}"

            await message.edit_text(
                f"✅ 配置创建成功\n\n"
                f"配置 ID：{config.id}\n"
                f"工作流：{work_name}\n"
                f"name_map：{name_map_key}\n"
                f"优先级：{priority}\n"
                f"全局默认：{'是' if is_global_default else '否'}\n"
                f"状态：已启用"
            )

            logger.info(
                "用户 %s[%s] 创建 name_map 配置: work_id=%s, key=%s, priority=%s, global_default=%s",
                user.full_name,
                user.id,
                work_id,
                name_map_key,
                priority,
                is_global_default,
            )

        except ValueError as e:
            await message.edit_text(f"❌ 创建配置失败: {e}")
        except Exception as e:
            logger.error("Error in confirm_create: %s", e, exc_info=True)
            await message.edit_text(f"❌ 创建配置失败: {str(e)}")

        return ConversationHandler.END

    @staticmethod
    async def cancel(update: Update, _: ContextTypes.DEFAULT_TYPE):
        """取消操作"""
        message = update.effective_message
        callback_query = update.callback_query

        if callback_query is None:
            await message.reply_text("❌ 已取消操作")
        else:
            await message.edit_text("❌ 已取消操作")

        return ConversationHandler.END

    async def list_configs_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """列出配置
        使用方法: /name_map_list [work_id]
        示例:
        - /name_map_list        # 列出所有配置
        - /name_map_list 1      # 列出工作流1的配置
        - /name_map_list global # 列出全局配置
        """
        args = context.args

        try:
            # 确定要查询的工作流
            if not args:
                # 获取所有工作流
                works = await self.work_service.get_all()
                message = "📋 **所有 name_map 配置**\n\n"

                # 全局配置
                global_configs = await self.tag_formatter.get_all_configs(None)
                if global_configs:
                    message += "🌐 **全局配置**:\n"
                    for config in global_configs:
                        status = "✅" if config.is_active else "❌"
                        global_mark = " 🌐[默认]" if config.is_global_default else ""
                        message += f"{status} {config.name_map_key} (优先级: {config.priority}){global_mark}\n"
                    message += "\n"

                # 各工作流配置
                for work in works:
                    configs = await self.tag_formatter.get_all_configs(work.id)
                    if configs:
                        message += f"📁 **{work.name or f'工作流{work.id}'}**:\n"
                        for config in configs:
                            status = "✅" if config.is_active else "❌"
                            global_mark = " 🌐[全局默认]" if config.is_global_default else ""
                            message += f"{status} {config.name_map_key} (优先级: {config.priority}){global_mark}\n"
                        message += "\n"

                if len(message.split("\n")) == 3:  # 只有标题
                    message = "没有找到任何配置"

            else:
                # 查询特定工作流
                work_id = None if args[0].lower() == "global" else int(args[0])
                configs = await self.tag_formatter.get_all_configs(work_id)

                if not configs:
                    message = f"工作流 {work_id or '全局'} 没有配置"
                else:
                    work_name = "全局" if work_id is None else f"工作流{work_id}"
                    if work_id:
                        work = await self.work_service.get_work_by_id(work_id)
                        if work and work.name:
                            work_name = work.name

                    message = f"📋 {work_name} 的 name_map 配置\n\n"
                    for config in configs:
                        status = "✅ 启用" if config.is_active else "❌ 禁用"
                        message += f"ID: {config.id}\n"
                        message += f"Key: {config.name_map_key}\n"
                        message += f"状态: {status}\n"
                        message += f"优先级: {config.priority}\n"
                        message += f"全局默认: {'是 🌐' if config.is_global_default else '否'}\n"
                        if config.description:
                            message += f"描述: {config.description}\n"
                        if config.file_path:
                            message += f"文件: {config.file_path}\n"
                        message += "\n"

            await update.message.reply_text(message)

        except ValueError:
            await update.message.reply_text("❌ work_id 必须是数字或 'global'")
        except Exception as e:
            logger.error(f"Error in list_configs_handler: {e}", exc_info=True)
            await update.message.reply_text(f"❌ 查询失败: {str(e)}")

    async def start_toggle(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """开始 toggle 交互流程
        使用方法: /name_map_toggle
        """
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 name_map_toggle 命令", user.full_name, user.id)

        # 获取所有工作流
        works = await self.work_service.get_all()

        # 构建工作流选择键盘
        keyboard: list[list[InlineKeyboardButton]] = []
        keyboard.append([InlineKeyboardButton(text="🌐 全局配置", callback_data="toggle_work|global")])

        for work in works:
            work_name = work.name or f"工作流 {work.id}"
            keyboard.append([InlineKeyboardButton(text=f"📁 {work_name}", callback_data=f"toggle_work|{work.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.reply_text(
            f"你好 {user.mention_html()} ！\n请选择要切换状态的配置所属工作流：",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return TOGGLE_SELECT_WORK

    async def toggle_select_work(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """选择工作流后，显示该工作流的配置列表"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析选择的 work_id
        work_data = callback_query.data.split("|")[1]
        work_id = None if work_data == "global" else int(work_data)

        # 获取工作流名称
        if work_id is None:
            work_name = "全局配置"
        else:
            work = await self.work_service.get_work_by_id(work_id)
            work_name = work.name if work and work.name else f"工作流 {work_id}"

        # 获取该工作流的所有配置
        configs = await self.tag_formatter.get_all_configs(work_id)

        if not configs:
            await message.edit_text(f"❌ {work_name} 没有任何配置")
            return ConversationHandler.END

        # 构建配置选择键盘
        keyboard: list[list[InlineKeyboardButton]] = []
        for config in configs:
            status_icon = "✅" if config.is_active else "❌"
            global_mark = " 🌐" if config.is_global_default else ""
            button_text = f"{status_icon} {config.name_map_key} (优先级:{config.priority}){global_mark}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"toggle_config|{config.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.edit_text(
            f"{work_name} 的配置列表\n\n请选择要切换状态的配置：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return TOGGLE_SELECT_CONFIG

    async def toggle_select_config(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """执行 toggle 操作"""
        callback_query = update.callback_query
        message = update.effective_message
        user = update.effective_user

        # 解析 config_id
        config_id = int(callback_query.data.split("|")[1])

        try:
            # 获取当前配置
            config = await self.tag_formatter.config_repo.get_by_id(config_id)
            if not config:
                await message.edit_text(f"❌ 配置 {config_id} 不存在")
                return ConversationHandler.END

            # 切换状态
            new_status = not config.is_active
            success = await self.tag_formatter.update_config_status(config_id, new_status)

            if success:
                status_text = "启用" if new_status else "禁用"
                work_name = "全局配置" if config.work_id is None else f"工作流 {config.work_id}"
                await message.edit_text(
                    f"✅ 配置状态已更新\n\n"
                    f"配置 ID：{config_id}\n"
                    f"工作流：{work_name}\n"
                    f"name_map：{config.name_map_key}\n"
                    f"新状态：{status_text}"
                )
                logger.info("用户 %s[%s] 将配置 %s 状态切换为 %s", user.full_name, user.id, config_id, status_text)
            else:
                await message.edit_text("❌ 更新失败")

        except Exception as e:
            logger.error("Error in toggle_select_config: %s", e, exc_info=True)
            await message.edit_text(f"❌ 操作失败: {str(e)}")

        return ConversationHandler.END

    async def start_delete(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """开始 delete 交互流程
        使用方法: /name_map_delete
        """
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 name_map_delete 命令", user.full_name, user.id)

        # 获取所有工作流
        works = await self.work_service.get_all()

        # 构建工作流选择键盘
        keyboard: list[list[InlineKeyboardButton]] = []
        keyboard.append([InlineKeyboardButton(text="🌐 全局配置", callback_data="delete_work|global")])

        for work in works:
            work_name = work.name or f"工作流 {work.id}"
            keyboard.append([InlineKeyboardButton(text=f"📁 {work_name}", callback_data=f"delete_work|{work.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.reply_text(
            f"你好 {user.mention_html()} ！\n⚠️ 请选择要删除配置所属的工作流：",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return DELETE_SELECT_WORK

    async def delete_select_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择工作流后，显示该工作流的配置列表"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析选择的 work_id
        work_data = callback_query.data.split("|")[1]
        work_id = None if work_data == "global" else int(work_data)

        # 保存到 context
        context.user_data["delete_work_id"] = work_id

        # 获取工作流名称
        if work_id is None:
            work_name = "全局配置"
        else:
            work = await self.work_service.get_work_by_id(work_id)
            work_name = work.name if work and work.name else f"工作流 {work_id}"

        # 获取该工作流的所有配置
        configs = await self.tag_formatter.get_all_configs(work_id)

        if not configs:
            await message.edit_text(f"❌ {work_name} 没有任何配置")
            return ConversationHandler.END

        # 构建配置选择键盘
        keyboard: list[list[InlineKeyboardButton]] = []
        for config in configs:
            status_icon = "✅" if config.is_active else "❌"
            global_mark = " 🌐" if config.is_global_default else ""
            button_text = f"{status_icon} {config.name_map_key} (优先级:{config.priority}){global_mark}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"delete_config|{config.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.edit_text(
            f"{work_name} 的配置列表\n\n⚠️ 请选择要删除的配置：",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return DELETE_SELECT_CONFIG

    async def delete_select_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择配置后，要求确认删除"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析 config_id
        config_id = int(callback_query.data.split("|")[1])

        # 保存到 context
        context.user_data["delete_config_id"] = config_id

        # 获取配置信息
        config = await self.tag_formatter.config_repo.get_by_id(config_id)
        if not config:
            await message.edit_text(f"❌ 配置 {config_id} 不存在")
            return ConversationHandler.END

        work_name = "全局配置" if config.work_id is None else f"工作流 {config.work_id}"

        # 构建确认键盘
        keyboard = [
            [
                InlineKeyboardButton(text="⚠️ 确认删除", callback_data=f"delete_confirm|{config_id}"),
                InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel"),
            ],
        ]

        await message.edit_text(
            f"⚠️ 确认删除配置？\n\n"
            f"配置 ID：{config.id}\n"
            f"工作流：{work_name}\n"
            f"name_map：{config.name_map_key}\n"
            f"优先级：{config.priority}\n"
            f"全局默认：{'是 🌐' if config.is_global_default else '否'}\n\n"
            f"此操作不可撤销！",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return DELETE_CONFIRM

    async def delete_confirm(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """确认删除配置"""
        callback_query = update.callback_query
        message = update.effective_message
        user = update.effective_user

        # 解析 config_id
        config_id = int(callback_query.data.split("|")[1])

        try:
            # 获取配置信息
            config = await self.tag_formatter.config_repo.get_by_id(config_id)
            if not config:
                await message.edit_text(f"❌ 配置 {config_id} 不存在")
                return ConversationHandler.END

            # 删除配置
            success = await self.tag_formatter.delete_config(config_id)

            if success:
                work_name = "全局配置" if config.work_id is None else f"工作流 {config.work_id}"
                await message.edit_text(f"✅ 配置已删除\n\n工作流：{work_name}\nname_map：{config.name_map_key}")
                logger.info("用户 %s[%s] 删除了配置 %s", user.full_name, user.id, config_id)
            else:
                await message.edit_text("❌ 删除失败")

        except Exception as e:
            logger.error("Error in delete_confirm: %s", e, exc_info=True)
            await message.edit_text(f"❌ 删除失败: {str(e)}")

        return ConversationHandler.END

    async def start_test(self, update: Update, _context: ContextTypes.DEFAULT_TYPE):
        """开始 test 交互流程
        使用方法: /name_map_test
        """
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 name_map_test 命令", user.full_name, user.id)

        # 获取所有工作流
        works = await self.work_service.get_all()

        # 构建工作流选择键盘
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text="🌐 全局配置", callback_data="test_work|global")]
        ]

        for work in works:
            work_name = work.name or f"工作流 {work.id}"
            keyboard.append([InlineKeyboardButton(text=f"📁 {work_name}", callback_data=f"test_work|{work.id}")])

        keyboard.append([InlineKeyboardButton(text="❌ 取消", callback_data="nm_cancel")])

        await message.reply_text(
            f"你好 {user.mention_html()} ！\n请选择要测试的工作流：",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return TEST_SELECT_WORK

    async def test_select_work(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """选择工作流后，提示输入标签"""
        callback_query = update.callback_query
        message = update.effective_message

        # 解析选择的 work_id
        work_data = callback_query.data.split("|")[1]
        work_id = None if work_data == "global" else int(work_data)

        # 保存到 context
        context.user_data["test_work_id"] = work_id

        # 获取工作流名称
        if work_id is None:
            work_name = "全局配置"
        else:
            work = await self.work_service.get_work_by_id(work_id)
            work_name = work.name if work and work.name else f"工作流 {work_id}"

        await message.edit_text(
            f"已选择：{work_name}\n\n"
            f"请直接回复要测试的标签，多个标签用空格分隔。\n"
            f"例如：胡洮 walnut 护堂\n\n"
            f"或使用 /cancel 取消测试。"
        )

        return TEST_INPUT_TAGS

    async def test_with_tags(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """执行标签测试"""
        message = update.effective_message
        user = update.effective_user

        # 获取用户输入的标签
        if not message.text:
            await message.reply_text("❌ 请输入要测试的标签")
            return TEST_INPUT_TAGS

        tags = message.text.split()
        work_id = context.user_data.get("test_work_id")

        try:
            # 获取 name_map 实例
            name_map = await self.tag_formatter.get_name_map_for_work(work_id)

            if name_map is None:
                await message.reply_text(
                    "❌ 当前工作流未配置可用的 name_map。请先使用 /name_map_config 或 /name_map_bind 配置。"
                )
                return ConversationHandler.END

            # 测试映射
            result = name_map.filter_character_tags(tags)
            identified = name_map.identify_characters(tags)

            # 构建详细信息
            details = []
            for char_key in identified:
                names = name_map.get_character_names(char_key)
                if names:
                    details.append(f"{char_key}: {', '.join(names)}")

            # 获取使用的配置信息
            config = await self.tag_formatter.get_active_config(work_id)
            config_info = "默认配置"
            if config:
                config_info = f"{config.name_map_key} (优先级: {config.priority})"

            # 构建回复消息
            response = "🧪 name_map 测试结果\n\n"
            response += f"工作流: {work_id or '全局/默认'}\n"
            response += f"使用配置: {config_info}\n"
            response += f"配置文件: {name_map.data_file.name}\n\n"
            response += f"输入标签: {' '.join(tags)}\n"
            response += f"识别结果: {', '.join(details) if details else '无匹配'}\n"
            response += f"格式化输出: {result}\n"

            # 显示缓存信息（调试）
            cache_info = self.name_map_factory.get_cached_instances_info()
            if cache_info:
                response += f"\n缓存实例: {len(cache_info)}"

            await message.reply_text(response)

            logger.info("用户 %s[%s] 测试了 work_id=%s 的标签映射", user.full_name, user.id, work_id)

        except Exception as e:
            logger.error("Error in test_with_tags: %s", e, exc_info=True)
            await message.reply_text(f"❌ 测试失败: {str(e)}")

        return ConversationHandler.END
