from typing import TYPE_CHECKING, get_args

from persica.factory.component import AsyncInitializingComponent
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

if TYPE_CHECKING:
    from telegram.ext import Application as BotApplication

    from paihub.application import Application
    from paihub.entities.artwork import ArtWork


class Component(AsyncInitializingComponent):
    __order__ = 1


class BaseDependence(Component):
    __order__ = 2


class Repository[T: SQLModel](Component):
    __order__ = 3
    entity_class: type[T]
    engine: AsyncEngine

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 尝试从泛型类型参数中获取 entity_class
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if hasattr(base, "__origin__"):
                type_args = get_args(base)
                if type_args:
                    cls.entity_class = type_args[0]
                    break
        else:
            # 如果无法从泛型类型参数获取，就检查是否手动定义了 entity_class
            if not hasattr(cls, "entity_class") or cls.entity_class is None:
                raise NotImplementedError(
                    f"{cls.__name__} must specify a generic type parameter or define 'entity_class'"
                )

    def set_engine(self, engine: "AsyncEngine"):
        self.engine = engine

    async def get_by_id(self, key_id: int) -> T | None:
        async with AsyncSession(self.engine) as session:
            statement = select(self.entity_class).where(self.entity_class.id == key_id)
            results = await session.exec(statement)
            return results.first()

    async def add(self, instance: T):
        async with AsyncSession(self.engine) as session:
            session.add(instance)
            await session.commit()

    async def update(self, instance: T) -> T:
        async with AsyncSession(self.engine) as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def remove(self, instance: T):
        async with AsyncSession(self.engine) as session:
            await session.delete(instance)
            await session.commit()

    async def merge(self, value: T):
        async with AsyncSession(self.engine) as session:
            await session.merge(value)
            await session.commit()

    async def get_all(self) -> list[T]:
        async with AsyncSession(self.engine) as session:
            statement = select(self.entity_class)
            results = await session.exec(statement)
            return results.all()


class Service(Component):
    __order__ = 4
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application


class Command(Component):
    __order__ = 5
    application: "Application"
    bot: "BotApplication"

    def set_application(self, application: "Application"):
        self.application = application
        self.bot = application.bot

    def add_handlers(self):
        """Add bot handlers used by this function"""


class SiteService(Component):
    __order__ = 5
    site_name: str  # 网站名称
    site_key: str  # 网站关键标识符 最大长度不超过16
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application

    async def get_artwork(self, artwork_id: int) -> "ArtWork":
        pass

    async def get_artwork_images(self, artwork_id: int) -> list[bytes]:
        pass

    async def initialize_review(
        self,
        work_id: int,  # noqa: ARG002
        search_text: str,  # noqa: ARG002
        is_pattern: bool,  # noqa: ARG002
        lines_per_page: int = 1000,  # noqa: ARG002
        create_by: int | None = None,  # noqa: ARG002
    ) -> int:
        return 0

    @staticmethod
    def extract(text: str) -> int | None:  # noqa: ARG004
        return None


class ApiService(Component):
    __order__ = 4
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application


class Job(Component):
    """定时任务基类"""

    __order__ = 6
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application
        self.add_jobs()

    def add_jobs(self) -> None:
        """Add scheduled jobs to the application scheduler."""


class Spider(Component):
    __order__ = 6
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application
        self.add_jobs()

    def add_jobs(self) -> None:
        """Add jobs used by this function"""
