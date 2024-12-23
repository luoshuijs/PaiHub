from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import Enum, func
from sqlmodel import BigInteger, Column, DateTime, Field, Integer, SQLModel

from paihub.utils.sql_types import JSON, SiteKey

if TYPE_CHECKING:
    from sqlalchemy import Result


class ReviewStatus(IntEnum):
    """审核状态
    :var WAIT: 等待审核
    :var REJECT: 拒绝
    :var PASS: 通过
    :var MOVE: 已经移动到其他任务列表
    :var NOT_FOUND: 作品已经找不到
    :var ERROR: 出现错误
    """

    WAIT = 0
    REJECT = 1
    PASS = 2
    MOVE = 10
    NOT_FOUND = 11
    ERROR = 12


class Review(SQLModel, table=True):
    """审核 SQLModel

    注意：如果需要大量字段查询操作不建议使用 ORM 对其控制，因为会添加 Python 对其进行序列化的任务，从而压力来到了CPU。

    :var id: 数据库ID
    :var work_id: 任务ID
    :var site_key:  网站唯一标识符 长度为16
    :var artwork_id: 作品ID
    :var author_id:  该作品的作者ID
    :var status: 审核状态
    :var auto: 是否为自动审核
    :var ext: 扩展字段，长度为255，如要存储更多字段 ，荐其把该字段放在SQL字段中存储，除非不是常量。
        该字段用来存储一些扩展数据。如存储旧的字段，拒绝原因。或用于存储该作品推送前是否需要额外操作，如隐藏图片等。
        反序列化为 Str，序列化为 JSON。
    :var create_by:  创建的审核的用户ID
    :var create_time:  创建时间 留空为自动生成
    :var update_by:  更新的审核的用户ID
    :var update_time: 更新时间 留空为自动生成
    """

    __tablename__ = "review"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    work_id: int | None = Field(default=None, sa_type=BigInteger, foreign_key="work.id")
    site_key: str | None = Field(default=None, sa_type=SiteKey)
    artwork_id: int | None = Field(default=None, sa_type=BigInteger)
    author_id: int | None = Field(default=None, sa_type=BigInteger)
    status: ReviewStatus | None = Field(default=ReviewStatus.WAIT, sa_column=Column("status", Enum(ReviewStatus)))
    auto: bool | None = Field(default=False, sa_column=Column("auto", Integer))
    ext: dict | None = Field(default=None, sa_column=Column("ext", JSON))
    create_by: int | None = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: datetime | None = Field(default=None, sa_column=Column("create_time", DateTime, default=func.now()))
    update_by: int | None = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: datetime | None = Field(default=None, sa_column=Column("update_time", DateTime, onupdate=func.now()))

    def set_reject(self, update_by: int):
        """设置审核状态为拒绝
        :param update_by:更新的用户ID
        :return: None
        """
        self.status = ReviewStatus.REJECT
        self.update_by = update_by

    def set_pass(self, update_by: int):
        """设置审核状态为通过
        :param update_by: 更新的用户ID
        :return: None
        """
        self.status = ReviewStatus.PASS
        self.update_by = update_by

    def set_wait(self, update_by: int):
        """设置审核状态为等待
        :param update_by: 更新的用户ID
        :return: None
        """
        self.status = ReviewStatus.WAIT
        self.update_by = update_by

    def set_move(self, update_by: int, move_work_id: int | None = None):
        """设置审核状态为已经移动
        :param update_by: 更新的用户ID
        :param move_work_id: 设置移动打的 work
        :return: None
        """
        self.status = ReviewStatus.MOVE
        self.update_by = update_by
        if move_work_id is not None:
            self.ext["move_work_id"] = move_work_id


class StatusStatistics(BaseModel):
    wait_count: int = 0
    pass_count: int = 0
    reject_count: int = 0
    move_count: int = 0

    @classmethod
    def parse_form_result(cls, result: "Result"):
        obj = cls()
        for row in result.all():
            name = row[0]
            count = row[1]
            if name == "WAIT":
                obj.wait_count = count
            elif name == "REJECT":
                obj.reject_count = count
            elif name == "PASS":
                obj.pass_count = count
            elif name == "MOVE":
                obj.move_count = count
        return obj

    @property
    def total(self) -> int:
        return self.wait_count + self.pass_count + self.reject_count + self.move_count

    @property
    def already(self) -> int:
        return self.pass_count + self.reject_count


class AutoReviewResult(BaseModel):
    status: bool
    statistics: StatusStatistics
    description: str | None = None


class ReviewBlackAuthor(SQLModel, table=True):
    __tablename__ = "review_black_author"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    site_key: str | None = Field(default=None, sa_type=SiteKey)
    author_id: int | None = Field(default=None, sa_type=BigInteger)


class ReviewWhiteAuthor(SQLModel, table=True):
    __tablename__ = "review_white_author"

    id: int | None = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    site_key: str | None = Field(default=None, sa_type=SiteKey)
    author_id: int | None = Field(default=None, sa_type=BigInteger)


# class AutoReviewRule(SQLModel):
#     __tablename__ = "auto_review_rules"
#
#     id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
#     work_id: Optional[int] = Field(default=None, foreign_key="work.id")
#     name: Optional[str] = Field(default=None, sa_column=Column("name", VARCHAR(255)))
#     description: Optional[str] = Field(default=None, sa_column=Column("description", VARCHAR(255)))
#     action: Optional[int] = Field(default=None, sa_column=Column("action", Integer))
#     status: Optional[int] = Field(default=None, sa_column=Column("status", Integer))
#     rules: Optional[str] = Field(default=None, sa_column=Column("rules", Text))
#
#     work: Optional[Work] = Relationship(back_populates="auto_review_rules")
#
