from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    title: str
    url: str
    created_at: str


class MarkdownPage(BaseModel):
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
