from functools import lru_cache
from typing import Dict, Iterator

from paihub.base import BaseService, BaseSiteService


class SitesManager(BaseService):
    def __init__(self):
        self.sites_services: Dict[str, BaseSiteService] = {}

    async def initialize(self):
        for s in self.application.factor.get_components(BaseSiteService):
            site_key = s.site_key
            self.sites_services.setdefault(site_key, s)

    @lru_cache(maxsize=128)
    def get_site_by_site_key(self, key_name: str) -> BaseSiteService:
        result = self.sites_services.get(key_name)
        if result is None:
            raise KeyError
        return result

    def get_all_sites(self) -> Iterator[BaseSiteService]:
        for _, value in self.sites_services.items():
            yield value
