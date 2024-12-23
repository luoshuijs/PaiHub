from paihub.base import SiteService
from paihub.sites.danbooru.api import DanbooruApi
from paihub.sites.danbooru.entities import DanbooruArtWork
from paihub.sites.danbooru.utils import compiled_patterns


class DanbooruSitesService(SiteService):
    site_name = "Danbooru"
    site_key = "danbooru"

    def __init__(self, api: DanbooruApi):
        self.api = api

    async def get_artwork(self, artwork_id: int) -> DanbooruArtWork:
        return await self.api.get_artwork_info(artwork_id)

    async def get_artwork_images(self, artwork_id: int) -> list[bytes]:
        return await self.api.get_artwork_images(artwork_id)

    @staticmethod
    def extract(text: str) -> int | None:
        for pattern in compiled_patterns:
            match = pattern.search(text)
            if match:
                return int(match.group("id"))
        return None
