import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv.load_dotenv()


class DatabaseConfig(BaseSettings):
    driver_name: str = "mysql+asyncmy"
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    database: str | None = None

    model_config = SettingsConfigDict(env_prefix="db_")


class RedisConfig(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    database: str | int = 0
    password: str | None = None

    model_config = SettingsConfigDict(env_prefix="redis_")


class BotConfig(BaseSettings):
    token: str
    owner: int
    base_url: str | None = None
    base_file_url: str | None = None

    model_config = SettingsConfigDict(env_prefix="bot_")


class MongodbConfig(BaseSettings):
    host: str = "localhost"
    port: int = 27017
    default_database: str = "PaiHub"

    model_config = SettingsConfigDict(env_prefix="mongodb_")


class Settings(BaseSettings):
    bot: BotConfig = BotConfig()
