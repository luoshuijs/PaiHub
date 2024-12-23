from paihub.base import BaseSiteService
from paihub.sites.twitter.api import WebClientApi
from paihub.sites.twitter.entities import TwitterArtWork
from paihub.sites.twitter.utils import compiled_patterns


class TwitterSitesService(BaseSiteService):
    site_name = "Twitter"
    site_key = "twitter"

    def __init__(self, web_api: WebClientApi):
        self.web_api = web_api

    async def get_artwork(self, artwork_id: int) -> TwitterArtWork:
        return await self.web_api.get_artwork(artwork_id)

    async def get_artwork_images(self, artwork_id: int) -> list[bytes]:
        return await self.web_api.get_artwork_images(artwork_id)

    @staticmethod
    def extract(text: str) -> int | None:
        for pattern in compiled_patterns:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None
