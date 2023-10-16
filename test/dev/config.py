from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    driver_name: str = "mysql+aiomysql"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    class Config(BaseSettings.Config):
        env_prefix = "db_"
