from typing import List, Optional, Any, cast, Dict

from sqlalchemy import VARCHAR, TypeDecorator, String
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.type_api import TypeEngine

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class SiteKey(VARCHAR):
    length = 16


class Tags(TypeDecorator[List[str]]):
    impl = VARCHAR
    mysql_default_length = 255

    def load_dialect_impl(self, dialect: Dialect) -> "TypeEngine[Any]":
        impl = cast(String, self.impl)
        if impl.length is None and dialect.name == "mysql":
            return dialect.type_descriptor(String(self.mysql_default_length))
        return super().load_dialect_impl(dialect)

    def process_bind_param(self, value: List[str], dialect) -> Optional[str]:
        if len(value) == 0:
            return None
        return "#".join(value)

    def process_result_value(self, value: Optional[str], dialect) -> List[str]:
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

    def process_bind_param(self, value: Optional[Dict], dialect) -> Optional[str]:
        if value is None:
            return None
        return jsonlib.dumps(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[Dict]:
        if value is None:
            return None
        return jsonlib.loads(value)
