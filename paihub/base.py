from typing import TYPE_CHECKING

from persica import BaseComponent

if TYPE_CHECKING:
    from telegram.ext import Application as BotApplication

    from paihub.application import Application
    from paihub.entities.artwork import ArtWork


class Component(BaseComponent, component=False):
    pass


class BaseDependence(BaseComponent, component=False):
    async def initialize(self) -> None:
        """Initialize resources used by this dependence"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this dependence"""


class BaseRepository(BaseComponent, component=False):
    pass


class BaseService(BaseComponent, component=False):
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application

    async def initialize(self) -> None:
        """Initialize resources used by this service"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this service"""


class BaseCommand(BaseComponent, component=False):
    application: "Application"
    bot: "BotApplication"

    def set_application(self, application: "Application"):
        self.application = application
        self.bot = application.bot

    def add_handlers(self):
        """Add bot handlers used by this function"""

    async def initialize(self) -> None:
        """Initialize resources used by this service"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this service"""


class BaseSiteService(BaseComponent, component=False):
    site_name: str  # 网站名称
    site_key: str  # 网站关键标识符 最大长度不超过16
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application

    async def initialize(self) -> None:
        """Initialize resources used by this service"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this service"""

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


class BaseApi(BaseComponent, component=False):
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application

    async def initialize(self) -> None:
        """Initialize resources used by this service"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this service"""


class BaseSpider(BaseComponent, component=False):
    application: "Application"

    def set_application(self, application: "Application"):
        self.application = application

    def add_jobs(self) -> None:
        """Add jobs used by this function"""

    async def initialize(self) -> None:
        """Initialize resources used by this service"""

    async def shutdown(self) -> None:
        """Stop & clear resources used by this service"""
