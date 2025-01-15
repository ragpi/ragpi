from typing import AsyncGenerator

from src.sources.common.github_client import GitHubClient
from src.sources.github_issues.chunker import chunk_github_issue
from src.sources.github_issues.config import GithubIssuesConfig
from src.sources.github_issues.fetcher import GitHubIssuesFetcher
from src.common.schemas import Document


async def extract_documents_from_github_issues(
    *,
    source_config: GithubIssuesConfig,
    concurrent_requests: int,
    user_agent: str,
    github_api_version: str,
    github_token: str | None,
    document_uuid_namespace: str,
) -> AsyncGenerator[Document, None]:
    async with GitHubClient(
        concurrent_requests=concurrent_requests,
        user_agent=user_agent,
        github_api_version=github_api_version,
        github_token=github_token,
    ) as github_client:
        issues_fetcher = GitHubIssuesFetcher(github_client=github_client)

        async for issue in issues_fetcher.fetch_issues(
            repo_owner=source_config.repo_owner,
            repo_name=source_config.repo_name,
            state=source_config.state,
            include_labels=source_config.include_labels,
            exclude_labels=source_config.exclude_labels,
            max_age=source_config.max_age,
        ):
            chunks = chunk_github_issue(
                issue=issue,
                chunk_size=source_config.chunk_size,
                chunk_overlap=source_config.chunk_overlap,
                uuid_namespace=document_uuid_namespace,
            )
            for chunk in chunks:
                yield chunk
