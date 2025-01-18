from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.github_client import GitHubClient
from src.connectors.github_issues.chunker import chunk_github_issue
from src.connectors.github_issues.config import GithubIssuesConfig
from src.connectors.github_issues.fetcher import GitHubIssuesFetcher
from src.common.schemas import Document


class GithubIssuesConnector(BaseConnector):
    config: GithubIssuesConfig

    def __init__(self, settings: Settings, config: GithubIssuesConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[Document, None]:
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
                max_age=self.config.max_age,
            ):
                chunks = chunk_github_issue(
                    issue=issue,
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
                )
                for chunk in chunks:
                    yield chunk
