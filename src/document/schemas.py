from typing import Any
from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]


class PageData(BaseModel):
    id: str
    url: str
    title: str
    content: str  # markdown


class GithubIssueComment(BaseModel):
    id: str
    url: str
    body: str


class GithubIssue(BaseModel):
    id: str
    url: str
    title: str
    body: str
    comments: list[GithubIssueComment] = []
