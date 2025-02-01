from pydantic import BaseModel


class MarkdownPage(BaseModel):
    url: str
    title: str
    content: str


class ExtractedDocument(BaseModel):
    url: str
    title: str
    content: str
