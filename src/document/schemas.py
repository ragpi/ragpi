from typing import Any
from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]  # TODO: Move title and url to own fields?


class MarkdownPage(BaseModel):
    id: str
    url: str
    title: str
    content: str


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
