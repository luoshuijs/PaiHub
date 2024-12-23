from collections.abc import Iterator

from paihub.base import Service, SiteService


class SitesManager(Service):
    def __init__(self):
        self.sites_services: dict[str, SiteService] = {}

    async def initialize(self):
        for s in self.application.factory.singleton_objects.values():
            if isinstance(s, SiteService) and hasattr(s, "site_key"):
                site_key = s.site_key
                self.sites_services.setdefault(site_key, s)

    def get_site_by_site_key(self, key_name: str) -> SiteService:
        result = self.sites_services.get(key_name)
        if result is None:
            raise KeyError
        return result

    def get_all_sites(self) -> Iterator[SiteService]:
        yield from self.sites_services.values()
