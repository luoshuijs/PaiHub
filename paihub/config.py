from typing import Optional, Union

import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv.load_dotenv()


class DatabaseConfig(BaseSettings):
    driver_name: str = "mysql+asyncmy"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="db_")


class RedisConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    database: Union[str, int] = 0
    password: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="redis_")


class BotConfig(BaseSettings):
    token: str
    owner: int
    base_url: Optional[str] = None
    base_file_url: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="bot_")


class MongodbConfig(BaseSettings):
    host: str = "localhost"
    port: int = 27017
    default_database: str = "PaiHub"

    model_config = SettingsConfigDict(env_prefix="mongodb_")


class Settings(BaseSettings):
    bot: BotConfig = BotConfig()
