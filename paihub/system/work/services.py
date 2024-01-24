from typing import List

from paihub.base import BaseService
from paihub.system.work.entities import Work
from paihub.system.work.repositories import WorkRepository


class WorkService(BaseService):
    def __init__(self, work_repository: WorkRepository):
        self.work_repository = work_repository

    async def get_all(self) -> List[Work]:
        return await self.work_repository.get_all()
