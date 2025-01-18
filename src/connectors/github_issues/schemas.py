from pydantic import BaseModel


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
