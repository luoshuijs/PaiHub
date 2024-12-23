from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import VARCHAR, String, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect

if TYPE_CHECKING:
    from sqlalchemy.sql.type_api import TypeEngine

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class SiteKey(VARCHAR):
    length = 16


class Tags(TypeDecorator[list[str]]):
    impl = VARCHAR
    mysql_default_length = 255

    def load_dialect_impl(self, dialect: Dialect) -> "TypeEngine[Any]":
        impl = cast(String, self.impl)
        if impl.length is None and dialect.name == "mysql":
            return dialect.type_descriptor(String(self.mysql_default_length))
        return super().load_dialect_impl(dialect)

    def process_bind_param(self, value: list[str], dialect) -> str | None:  # noqa: ARG002
        if len(value) == 0:
            return None
        return "#".join(value)

    def process_result_value(self, value: str | None, dialect) -> list[str]:  # noqa: ARG002
        if value is None:
            return []
        return value.split("#")


class JSON(TypeDecorator):
    impl = VARCHAR
    mysql_default_length = 255

    def load_dialect_impl(self, dialect: Dialect) -> "TypeEngine[Any]":
        impl = cast(String, self.impl)
        if impl.length is None and dialect.name == "mysql":
            return dialect.type_descriptor(String(self.mysql_default_length))
        return super().load_dialect_impl(dialect)

    def process_bind_param(self, value: dict | None, dialect) -> str | None:  # noqa: ARG002
        if value is None:
            return None
        return jsonlib.dumps(value).decode("utf-8")

    def process_result_value(self, value: str | None, dialect) -> dict | None:  # noqa: ARG002
        if value is None:
            return None
        return jsonlib.loads(value)
