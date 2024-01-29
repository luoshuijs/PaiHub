from functools import lru_cache
from typing import Dict, Iterator

from paihub.base import BaseService, BaseSiteService
from paihub.entities.artwork import ArtWork

from paihub.system.sites.entities import Site
from paihub.system.sites.repositories import SitesRepository


class SitesManager(BaseService):
    def __init__(self, sites_repository: SitesRepository):
        self.sites_repository = sites_repository
        self.sites_services: Dict[str, BaseSiteService] = {}
        self.sites_services_id: Dict[int, BaseSiteService] = {}

    async def initialize(self):
        for s in self.application.factor.get_components(BaseSiteService):
            site_name = s.site_name
            web_info = await self.sites_repository.get_by_key_name(site_name)
            if web_info is None:
                await self.sites_repository.add(Site(web_name=site_name, web_key=site_name))
                web_info = await self.sites_repository.get_by_key_name(site_name)
            self.sites_services.setdefault(site_name, s)
            self.sites_services_id.setdefault(web_info.id, s)

    @lru_cache(maxsize=128)
    def get_site_by_site_name(self, key_name: str) -> BaseSiteService:
        result = self.sites_services.get(key_name)
        if result is None:
            raise KeyError
        return result

    def get_all_sites(self) -> Iterator[BaseSiteService]:
        for _, value in self.sites_services.items():
            yield value

    @lru_cache(maxsize=128)
    def get_site_by_site_id(self, key_id: int) -> BaseSiteService:
        result = self.sites_services_id.get(key_id)
        if result is None:
            raise KeyError
        return result
