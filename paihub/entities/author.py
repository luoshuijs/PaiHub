from pydantic import BaseModel


class Author(BaseModel):
    auther_id: int
    name: str

    @property
    def url(self) -> str:
        return ""
