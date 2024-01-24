from typing import Optional, Union

import dotenv
from pydantic import BaseSettings

dotenv.load_dotenv()


class Database(BaseSettings):
    driver_name: str = "mysql+asyncmy"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    class Config(BaseSettings.Config):
        env_prefix = "db_"


class Redis(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 6379
    database: Union[str, int] = 0
    password: Optional[str] = None


class Bot(BaseSettings):
    token: str
    owner: int

    class Config(BaseSettings.Config):
        env_prefix = "bot_"


class Settings(BaseSettings):
    bot: Bot = Bot()
    database: Database = Database()
    redis: Redis = Redis()