from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, Boolean, Column, Index, String, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from paihub.system.work.entities import Work


class NameMapConfig(SQLModel, table=True):
    __tablename__ = "name_map_config"
    __table_args__ = (
        # 复合索引：优化 work_id + priority 查询
        Index("idx_work_id_priority", "work_id", "priority"),
        # 复合索引：优化 work_id + is_active 查询
        Index("idx_work_id_active", "work_id", "is_active"),
        # 索引：全局默认标记（用于快速查找）
        Index("idx_global_default", "is_global_default"),
    )

    id: int | None = Field(default=None, primary_key=True)
    work_id: int | None = Field(default=None, foreign_key="work.id")
    name_map_key: str = Field(sa_column=Column("name_map_key", String, nullable=False))
    file_path: str | None
    description: str | None
    priority: int = Field(default=0)
    is_active: bool = Field(default=True, sa_column=Column("is_active", Boolean, default=True, server_default="1"))
    is_global_default: bool = Field(
        default=False, sa_column=Column("is_global_default", Boolean, default=False, server_default="0", nullable=False)
    )
    created_at: datetime | None = Field(
        sa_column=Column("created_at", TIMESTAMP, default=datetime.now(UTC), server_default=text("CURRENT_TIMESTAMP"))
    )
    updated_at: datetime | None = Field(
        sa_column=Column(
            "updated_at",
            TIMESTAMP,
            default=datetime.now(UTC),
            onupdate=datetime.now(UTC),
            server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        )
    )

    work: Optional["Work"] = Relationship(back_populates="name_map_configs")
