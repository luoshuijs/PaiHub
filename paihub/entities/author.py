from pydantic import BaseModel


class Auther(BaseModel):
    auther_id: int
    name: str
