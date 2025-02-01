from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.github_client import GitHubClient
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.github_issues.chunker import chunk_github_issue
from src.connectors.github_issues.config import GithubIssuesConfig
from src.connectors.github_issues.fetcher import GitHubIssuesFetcher


class GithubIssuesConnector(BaseConnector):
    config: GithubIssuesConfig

    def __init__(self, settings: Settings, config: GithubIssuesConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        async with GitHubClient(
            concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
            user_agent=self.settings.USER_AGENT,
            github_api_version=self.settings.GITHUB_API_VERSION,
            github_token=self.settings.GITHUB_TOKEN,
        ) as github_client:
            issues_fetcher = GitHubIssuesFetcher(github_client=github_client)

            async for issue in issues_fetcher.fetch_issues(
                repo_owner=self.config.repo_owner,
                repo_name=self.config.repo_name,
                state=self.config.state,
                include_labels=self.config.include_labels,
                exclude_labels=self.config.exclude_labels,
                issue_age_limit=self.config.issue_age_limit,
            ):
                chunks = chunk_github_issue(
                    issue=issue,
                    chunk_size=self.settings.CHUNK_SIZE,
                    chunk_overlap=self.settings.CHUNK_OVERLAP,
                )
                for chunk in chunks:
                    yield chunk
