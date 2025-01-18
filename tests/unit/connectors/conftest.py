from typing import AsyncGenerator

import pytest

from src.connectors.common.github_client import GitHubClient


@pytest.fixture
async def github_client() -> AsyncGenerator[GitHubClient, None]:
    async with GitHubClient(
        concurrent_requests=2,
        user_agent="test-agent",
        github_api_version="2022-11-28",
        github_token="test-token",
    ) as client:
        yield client
