from persica.factory.interface import InterfaceFactory

from paihub.application import Application
from paihub.base import ApiService, Command, Repository, Service, SiteService, Spider
from paihub.dependence.database import DataBase


class SQLEngineFactory(InterfaceFactory[Repository]):
    def __init__(self, database: DataBase):
        self.engine = database.engine

    def get_object(self, obj: Repository | None) -> Repository:
        obj.set_engine(self.engine)
        return obj


class ServiceFactory(InterfaceFactory[Service]):
    def __init__(self, application: Application):
        self.application = application

    def get_object(self, obj: Service | None) -> Service:
        obj.set_application(self.application)
        return obj


class SiteServiceFactory(InterfaceFactory[SiteService]):
    def __init__(self, application: Application):
        self.application = application

    def get_object(self, obj: SiteService | None) -> SiteService:
        obj.set_application(self.application)
        return obj


class ApiServiceFactory(InterfaceFactory[ApiService]):
    def __init__(self, application: Application):
        self.application = application

    def get_object(self, obj: ApiService | None) -> ApiService:
        obj.set_application(self.application)
        return obj


class CommandFactory(InterfaceFactory[Command]):
    def __init__(self, application: Application):
        self.application = application

    def get_object(self, obj: Command | None) -> Command:
        obj.set_application(self.application)
        obj.add_handlers()
        return obj


class SpiderFactory(InterfaceFactory[Spider]):
    def __init__(self, application: Application):
        self.application = application

    def get_object(self, obj: Spider | None) -> Spider:
        obj.set_application(self.application)
        return obj
