import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, AsyncGenerator

from src.document_extractor.clients.github import GitHubClient
from src.document_extractor.schemas import GithubIssue, GithubIssueComment

logger = logging.getLogger(__name__)


class GitHubIssueClient(GitHubClient):
    def __init__(
        self,
        *,
        concurrent_requests: int,
        user_agent: str,
        github_api_version: str,
        github_token: str,
    ):
        super().__init__(
            concurrent_requests=concurrent_requests,
            user_agent=user_agent,
            github_api_version=github_api_version,
            github_token=github_token,
        )

    async def fetch_comments(self, comments_url: str) -> list[GithubIssueComment]:
        comments: list[GithubIssueComment] = []
        url = comments_url
        params: dict[str, str] | None = {"per_page": "100"}

        while True:
            data, headers = await self.request("GET", url, params=params)

            if not data:
                break

            comments.extend(
                [
                    GithubIssueComment(
                        id=str(comment["id"]),
                        url=comment["html_url"],
                        body=comment["body"] or "",
                    )
                    for comment in data
                ]
            )

            if not headers:
                break

            # Check for 'next' link in headers
            link_header = headers.get("Link")
            if link_header:
                links = self._parse_link_header(link_header)
                next_url = links.get("next")
                if next_url:
                    url = next_url
                    params = None  # Params are included in the next_url
                else:
                    break
            else:
                break
        return comments

    async def fetch_issues(
        self,
        repo_owner: str,
        repo_name: str,
        state: str = "all",
        include_labels: list[str] | None = None,
        exclude_labels: list[str] | None = None,
        max_age: int | None = None,
    ) -> AsyncGenerator[GithubIssue, None]:
        logger.info(f"Fetching issues from repo: {repo_owner}/{repo_name}")

        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

        params: dict[str, str] | None = {
            "per_page": "100",
            "state": state,
            "sort": "updated",
            "direction": "desc",
        }

        if max_age:
            cutoff_datetime = datetime.now(timezone.utc) - timedelta(days=max_age)
            cutoff_str = cutoff_datetime.strftime("%Y-%m-%d")
            assert params is not None, "params should not be None"
            params["since"] = cutoff_str

        async def process_item(item: Any) -> GithubIssue | None:
            # Skip pull requests
            if "pull_request" in item:
                return None

            labels = [label["name"] for label in item.get("labels", [])]
            if include_labels and not any(label in include_labels for label in labels):
                return None

            if exclude_labels and any(label in exclude_labels for label in labels):
                return None

            comments_count = item.get("comments", 0)
            comments: list[GithubIssueComment] = []
            if comments_count > 0:
                comments = await self.fetch_comments(item["comments_url"])

            return GithubIssue(
                id=str(item["id"]),
                url=item["html_url"],
                title=item["title"],
                body=item["body"] or "",
                comments=comments,
            )

        while True:
            data, headers = await self.request("GET", url, params=params)
            if not data:
                break

            tasks = [asyncio.create_task(process_item(item)) for item in data]
            for task in asyncio.as_completed(tasks):
                issue = await task
                if issue:
                    yield issue

            if not headers:
                break

            # Check for 'next' link in headers
            link_header = headers.get("Link")
            if link_header:
                links = self._parse_link_header(link_header)
                next_url = links.get("next")
                if next_url:
                    url = next_url
                    params = None  # Params are included in the next_url
                else:
                    break
            else:
                break
