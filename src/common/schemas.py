from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    title: str
    url: str
    created_at: str
