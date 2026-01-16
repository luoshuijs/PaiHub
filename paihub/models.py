"""
数据库模型集合

此文件导入所有 SQLModel 表，用于 Alembic 迁移。
"""

from sqlmodel import SQLModel

# 导入所有表
from paihub.sites.pixiv.entities import Pixiv
from paihub.system.push.entities import Push
from paihub.system.review.entities import Review
from paihub.system.user.entities import User
from paihub.system.work.entities import Work, WorkChannel, WorkRule

# 导出元数据供 Alembic 使用
metadata = SQLModel.metadata

__all__ = [
    "metadata",
    "Pixiv",
    "Push",
    "Review",
    "User",
    "Work",
    "WorkChannel",
    "WorkRule",
]
