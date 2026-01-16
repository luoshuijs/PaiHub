from datetime import datetime
from enum import IntEnum

from sqlalchemy import Enum, func
from sqlmodel import Column, DateTime, Field, Integer, SQLModel

from paihub.utils.sql_types import JSON


class AutoPushMode(IntEnum):
    """自动推送模式
    :var BATCH: 批量模式 - 先审核指定数量，再统一推送
    :var IMMEDIATE: 即时模式 - 每审核通过一个，立即推送一个
    """

    BATCH = 0
    IMMEDIATE = 1


class AutoPushStatus(IntEnum):
    """自动推送任务状态
    :var DISABLED: 禁用
    :var ENABLED: 启用
    :var RUNNING: 运行中
    :var PAUSED: 暂停
    """

    DISABLED = 0
    ENABLED = 1
    RUNNING = 2
    PAUSED = 3


class AutoPushConfig(SQLModel, table=True):
    """自动推送配置 SQLModel

    :var id: 数据库ID
    :var work_id: 关联的任务ID
    :var name: 配置名称
    :var description: 配置描述
    :var mode: 推送模式 (BATCH=批量模式, IMMEDIATE=即时模式)
    :var status: 配置状态 (DISABLED=禁用, ENABLED=启用, RUNNING=运行中, PAUSED=暂停)
    :var cron_expression: Cron 表达式，用于定时触发（例如："0 */6 * * *" 表示每6小时执行一次）
    :var review_count: 每次自动审核的数量（BATCH模式下使用）
    :var push_to_owner: 是否同步发送到 BOT_OWNER（用于撤回和删除）
    :var run_once: 是否仅运行一次（执行完成后自动禁用）
    :var ext: 扩展字段，存储额外配置（JSON格式）
    :var create_by: 创建人用户ID
    :var create_time: 创建时间
    :var update_by: 更新人用户ID
    :var update_time: 更新时间
    :var last_run_time: 最后一次运行时间
    :var next_run_time: 下次计划运行时间
    """

    __tablename__ = "auto_push_config"

    id: int | None = Field(sa_column=Column("id", Integer, primary_key=True, autoincrement=True))
    work_id: int | None = Field(default=None, sa_type=Integer, foreign_key="work.id")
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    mode: AutoPushMode | None = Field(
        default=AutoPushMode.BATCH, sa_column=Column("mode", Enum(AutoPushMode), default=AutoPushMode.BATCH)
    )
    status: AutoPushStatus | None = Field(
        default=AutoPushStatus.DISABLED,
        sa_column=Column("status", Enum(AutoPushStatus), default=AutoPushStatus.DISABLED),
    )
    cron_expression: str | None = Field(default="0 */6 * * *", max_length=100)  # 默认每6小时执行
    review_count: int | None = Field(default=10, sa_column=Column("review_count", Integer))  # 默认每次审核10个
    push_to_owner: bool | None = Field(default=True, sa_column=Column("push_to_owner", Integer))  # 默认同步到owner
    run_once: bool | None = Field(default=False, sa_column=Column("run_once", Integer))  # 默认不是一次性任务
    ext: dict | None = Field(default=None, sa_column=Column("ext", JSON))
    create_by: int | None = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: datetime | None = Field(default=None, sa_column=Column("create_time", DateTime, default=func.now()))
    update_by: int | None = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: datetime | None = Field(default=None, sa_column=Column("update_time", DateTime, onupdate=func.now()))
    last_run_time: datetime | None = Field(default=None, sa_column=Column("last_run_time", DateTime))
    next_run_time: datetime | None = Field(default=None, sa_column=Column("next_run_time", DateTime))

    def enable(self, update_by: int):
        """启用自动推送
        :param update_by: 更新人用户ID
        """
        self.status = AutoPushStatus.ENABLED
        self.update_by = update_by

    def disable(self, update_by: int):
        """禁用自动推送
        :param update_by: 更新人用户ID
        """
        self.status = AutoPushStatus.DISABLED
        self.update_by = update_by

    def pause(self, update_by: int):
        """暂停自动推送
        :param update_by: 更新人用户ID
        """
        self.status = AutoPushStatus.PAUSED
        self.update_by = update_by

    def set_running(self):
        """设置为运行中状态"""
        self.status = AutoPushStatus.RUNNING
        self.last_run_time = datetime.now()

    def set_completed(self):
        """设置任务完成，恢复为启用状态"""
        self.status = AutoPushStatus.ENABLED
