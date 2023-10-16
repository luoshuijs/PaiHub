from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, BigInteger, Integer, VARCHAR, DateTime


class Web(SQLModel):
    id: Optional[int] = Field(sa_column=Column("id", BigInteger, primary_key=True, autoincrement=True))
    web_name: Optional[str] = Field(default=None, sa_column=Column("web_name", VARCHAR(255)))
    web_key: Optional[str] = Field(default=None, sa_column=Column("web_key", VARCHAR(255)))
    create_by: Optional[int] = Field(default=None, sa_column=Column("create_by", Integer))
    create_time: Optional[datetime] = Field(default=None, sa_column=Column("create_time", DateTime))
    update_by: Optional[int] = Field(default=None, sa_column=Column("update_by", Integer))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column("update_time", DateTime))
    remark: Optional[str] = Field(default=None, sa_column=Column("remark", VARCHAR(255)))
