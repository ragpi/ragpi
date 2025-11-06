from pydantic import BaseModel


class PdfDocument(BaseModel):
    path: str
    url: str
    content: str
