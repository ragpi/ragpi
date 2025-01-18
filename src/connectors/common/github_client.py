import asyncio
import logging
import time
from types import TracebackType
from typing import Any, Type
from aiohttp import ClientError, ClientSession

from src.connectors.exceptions import ConnectorException


logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(
        self,
        *,
        concurrent_requests: int,
        user_agent: str,
        github_api_version: str,
        github_token: str | None,
    ):
        if not github_token:
            raise ConnectorException("GITHUB_TOKEN is required to access GitHub API")

        self.session: ClientSession = ClientSession(
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": github_api_version,
                "User-Agent": user_agent,
                "Authorization": f"Bearer {github_token}",
            }
        )
        self.semaphore = asyncio.Semaphore(concurrent_requests)
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()

    async def __aenter__(self):
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        if self.session:
            await self.session.close()

    def parse_link_header(self, header: str) -> dict[str, str]:
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

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        max_attempts: int = 5,
        retry_backoff: float = 60,
    ) -> tuple[Any | None, dict[str, str] | None]:
        retry_count = 0
        while retry_count < max_attempts:
            await self.rate_limit_event.wait()  # Wait until rate limit is lifted
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
                                # Reset time has passed
                                if wait_time < 0:
                                    wait_time = 0
                            else:
                                # Exponential backoff
                                wait_time = retry_backoff * (2**retry_count)

                            logger.warning(
                                f"Rate limit exceeded. Waiting for {wait_time} seconds."
                            )
                            await asyncio.sleep(wait_time)
                            self.rate_limit_event.set()
                            retry_count += 1
                            continue
                        elif response.status == 404:
                            raise ConnectorException(f"Resource not found at {url}")
                        elif response.status == 401:
                            raise ConnectorException(
                                f"GITHUB_TOKEN is not authorized to access {url}"
                            )
                        response.raise_for_status()
                        data = await response.json()
                        return data, dict(response.headers)
                except ConnectorException as e:
                    raise e
                except ClientError:
                    logger.exception("HTTP request failed")
                    logger.warning(f"Retrying in {retry_backoff} seconds...")
                    retry_count += 1
                    wait_time = retry_backoff * (2**retry_count)
                    await asyncio.sleep(wait_time)
                except Exception:
                    logger.exception("Unexpected error")
                    raise ConnectorException(f"Unexpected error when fetching {url}")

        logger.error(f"Failed to make request to {url} after {max_attempts} attempts.")
        return None, None
