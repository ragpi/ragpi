from pydantic import BaseModel


class PageData(BaseModel):
    id: str
    url: str
    title: str
    content: str  # markdown
