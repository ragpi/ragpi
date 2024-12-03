import asyncio
import logging
from types import TracebackType
import aiohttp
from typing import AsyncGenerator, Optional, Type

from src.config import settings
from src.document.schemas import GithubIssue


class GitHubIssueCrawler:
    def __init__(
        self,
    ) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.github_api_version = "2022-11-28"  # TODO: Move to settings
        self.github_token: str | None = None  # TODO: Move to settings
        self.user_agent = settings.USER_AGENT
        self.max_concurrent_requests = settings.MAX_CONCURRENT_REQUESTS

    async def __aenter__(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.github_api_version,
            "User-Agent": self.user_agent,
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        if self.session:
            await self.session.close()

    async def fetch_issues(
        self,
        repo: str,
    ) -> AsyncGenerator[GithubIssue, None]:
        base_url = "https://api.github.com/search/issues"
        per_page = 100
        page = 1
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def fetch_page(page_number: int):
            params: dict[str, str | int] = {
                "q": f"type:issue repo:{repo}",
                "per_page": per_page,
                "page": page_number,
            }

            if not self.session:
                raise ValueError("Session is not initialized")

            async with semaphore:
                async with self.session.get(base_url, params=params) as response:
                    if response.status == 403:
                        logging.error("Rate limit exceeded.")
                        return None
                    response.raise_for_status()
                    data = await response.json()
                    return data

        # Fetch the first page to get total_count
        data = await fetch_page(page)
        if not data:
            return

        # TODO: Handle when more than 1000 issues
        total_count = data.get("total_count", 0)
        items = data.get("items", [])

        for item in items:
            yield GithubIssue(
                id=str(item["id"]),
                url=item["html_url"],
                title=item["title"],
                body=item["body"] or "",
            )

        # Calculate total pages
        total_pages = (total_count // per_page) + 1

        # Create tasks for remaining pages
        tasks = [asyncio.create_task(fetch_page(p)) for p in range(2, total_pages + 1)]

        for task in asyncio.as_completed(tasks):
            page_data = await task
            if page_data:
                for item in page_data.get("items", []):
                    yield GithubIssue(
                        id=str(item["id"]),
                        url=item["html_url"],
                        title=item["title"],
                        body=item["body"] or "",
                    )
