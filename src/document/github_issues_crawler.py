import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time
from types import TracebackType
import aiohttp
from typing import Any, AsyncGenerator, Type

from src.config import settings
from src.document.schemas import GithubIssue, GithubIssueComment


class GitHubIssueCrawler:
    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.github_api_version = settings.GITHUB_API_VERSION
        self.github_token: str | None = settings.GITHUB_TOKEN
        self.user_agent = settings.USER_AGENT
        self.semaphore = asyncio.Semaphore(
            settings.CONCURRENT_REQUESTS
        )  # TODO: Add to input
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()

    async def __aenter__(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.github_api_version,
            "User-Agent": self.user_agent,
        }
        # TODO: Make github token required?
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        if self.session:
            await self.session.close()

    def _parse_link_header(self, header: str) -> dict[str, str]:
        links = header.split(", ")
        link_dict: dict[str, str] = {}
        for link in links:
            parts = link.split("; ")
            if len(parts) < 2:
                continue
            url_part = parts[0].strip("<>")
            rel_part = parts[1]
            rel = rel_part.split("=")[1].strip('"')
            link_dict[rel] = url_part
        return link_dict

    async def _make_request(
        self, method: str, url: str, params: dict[str, str | int] | None = None
    ):
        retry_count = 0
        max_retries = 5
        backoff = 60  # Start backoff at 60 seconds
        while retry_count < max_retries:
            await self.rate_limit_event.wait()  # Wait until rate limit is lifted
            if not self.session:
                raise ValueError("Session is not initialized")
            async with self.semaphore:
                try:
                    async with self.session.request(
                        method, url, params=params
                    ) as response:
                        if response.status in (429, 403):
                            # Handle rate limiting
                            self.rate_limit_event.clear()  # Prevent other requests
                            retry_after = response.headers.get("Retry-After")
                            rate_limit_remaining = response.headers.get(
                                "X-RateLimit-Remaining"
                            )
                            rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                            if retry_after:
                                wait_time = int(retry_after)
                            elif rate_limit_remaining == "0" and rate_limit_reset:
                                current_time = int(time.time())
                                reset_time = int(rate_limit_reset)
                                wait_time = reset_time - current_time
                                if wait_time < 0:
                                    wait_time = 0  # Reset time has passed
                            else:
                                wait_time = backoff * (
                                    2**retry_count
                                )  # Exponential backoff
                            logging.error(
                                f"Rate limit exceeded. Waiting for {wait_time} seconds."
                            )
                            await asyncio.sleep(wait_time)
                            self.rate_limit_event.set()
                            retry_count += 1
                            continue
                        response.raise_for_status()
                        data = await response.json()
                        return data, response.headers
                except aiohttp.ClientError as e:
                    logging.error(f"HTTP request failed: {e}")
                    retry_count += 1
                    wait_time = backoff * (2**retry_count)
                    await asyncio.sleep(wait_time)
        raise Exception("Max retries exceeded")

    async def fetch_comments(self, comments_url: str) -> list[GithubIssueComment]:
        comments: list[GithubIssueComment] = []
        url = comments_url
        params: dict[str, str | int] | None = {"per_page": 100}

        while True:
            data, headers = await self._make_request("GET", url, params=params)
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
        state: str | None = None,
        include_labels: list[str] | None = None,
        exclude_labels: list[str] | None = None,
        max_age: int | None = None,
    ) -> AsyncGenerator[GithubIssue, None]:
        logging.info(f"Fetching issues from repo: {repo_owner}/{repo_name}")

        base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

        params: dict[str, str | int] | None = {
            "per_page": 100,
            "state": state or "all",
            "sort": "updated",
            "direction": "desc",
        }

        if max_age:
            cutoff_datetime = datetime.now(timezone.utc) - timedelta(days=max_age)
            cutoff_str = cutoff_datetime.strftime("%Y-%m-%d")
            assert params is not None, "params should not be None"
            params["since"] = cutoff_str

        url = base_url

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
            data, headers = await self._make_request("GET", url, params=params)
            if not data:
                break

            tasks = [asyncio.create_task(process_item(item)) for item in data]
            for task in asyncio.as_completed(tasks):
                issue = await task
                if issue:
                    yield issue

            # Check for 'next' link in headers for pagination
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
