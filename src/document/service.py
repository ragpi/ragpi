import logging
from typing import AsyncGenerator
from src.document.chunker import chunk_github_issue_data, chunk_markdown_page
from src.document.clients.github_issue import GitHubIssueClient
from src.document.schemas import Document
from src.document.clients.sitemap import SitemapClient
from src.exceptions import (
    DocumentServiceException,
    GitHubIssueClientException,
    SitemapClientException,
)
from src.source.schemas import (
    GithubIssuesConfig,
    SitemapConfig,
    SourceConfig,
    SourceType,
)


class DocumentService:
    async def create_documents_from_sitemap(
        self, config: SitemapConfig
    ) -> AsyncGenerator[Document, None]:
        async with SitemapClient(config.concurrent_requests) as client:
            async for page in client.fetch_sitemap_pages(
                sitemap_url=config.sitemap_url,
                include_pattern=config.include_pattern,
                exclude_pattern=config.exclude_pattern,
            ):
                chunks = chunk_markdown_page(
                    page, config.chunk_size, config.chunk_overlap
                )
                for chunk in chunks:
                    yield chunk

    async def create_documents_from_github_issues(
        self,
        config: GithubIssuesConfig,
    ) -> AsyncGenerator[Document, None]:
        async with GitHubIssueClient(config.concurrent_requests) as client:
            async for issue in client.fetch_issues(
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                state=config.state,
                include_labels=config.include_labels,
                exclude_labels=config.exclude_labels,
                max_age=config.max_age,
            ):
                chunks = chunk_github_issue_data(
                    issue, config.chunk_size, config.chunk_overlap
                )
                for chunk in chunks:
                    yield chunk

    async def create_documents(
        self,
        source_config: SourceConfig,
    ) -> AsyncGenerator[Document, None]:
        if source_config.type == SourceType.SITEMAP:
            try:
                async for doc in self.create_documents_from_sitemap(source_config):
                    yield doc
            except SitemapClientException as e:
                raise DocumentServiceException(str(e))
            except Exception as e:
                logging.exception(e)
                raise DocumentServiceException(
                    "Failed to create documents from sitemap"
                )
        elif source_config.type == SourceType.GITHUB_ISSUES:
            try:
                async for doc in self.create_documents_from_github_issues(
                    source_config
                ):
                    yield doc
            except GitHubIssueClientException as e:
                raise DocumentServiceException(str(e))
            except Exception as e:
                logging.exception(e)
                raise DocumentServiceException(
                    "Failed to create documents from GitHub issues"
                )
