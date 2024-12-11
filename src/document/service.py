import logging
from typing import AsyncGenerator
from src.document.chunker import chunk_github_issue, chunk_markdown_page
from src.document.clients.github_issue import GitHubIssueClient
from src.document.clients.github_readme import GitHubReadmeClient
from src.document.exceptions import (
    DocumentServiceException,
    GitHubClientException,
    SitemapClientException,
)
from src.document.schemas import Document
from src.document.clients.sitemap import SitemapClient
from src.source.schemas import (
    GithubIssuesConfig,
    GithubReadmeConfig,
    SitemapConfig,
    SourceConfig,
    SourceType,
)


class DocumentService:
    async def create_documents_from_sitemap(
        self, config: SitemapConfig
    ) -> AsyncGenerator[Document, None]:
        try:
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
        except SitemapClientException as e:
            raise DocumentServiceException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing sitemap source.")
            raise DocumentServiceException("Failed to create documents from sitemap")

    async def create_documents_from_github_issues(
        self,
        config: GithubIssuesConfig,
    ) -> AsyncGenerator[Document, None]:
        try:
            async with GitHubIssueClient(config.concurrent_requests) as client:
                async for issue in client.fetch_issues(
                    repo_owner=config.repo_owner,
                    repo_name=config.repo_name,
                    state=config.state,
                    include_labels=config.include_labels,
                    exclude_labels=config.exclude_labels,
                    max_age=config.max_age,
                ):
                    chunks = chunk_github_issue(
                        issue, config.chunk_size, config.chunk_overlap
                    )
                    for chunk in chunks:
                        yield chunk
        except GitHubClientException as e:
            raise DocumentServiceException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing GitHub issues source.")
            raise DocumentServiceException(
                "Failed to create documents from GitHub issues"
            )

    async def create_documents_from_github_readme(
        self,
        config: GithubReadmeConfig,
    ) -> AsyncGenerator[Document, None]:
        try:
            async with GitHubReadmeClient() as client:
                async for page in client.fetch_readmes(
                    repo_owner=config.repo_owner,
                    repo_name=config.repo_name,
                    include_root=config.include_root,
                    sub_dirs=config.sub_dirs,
                ):
                    chunks = chunk_markdown_page(
                        page, config.chunk_size, config.chunk_overlap
                    )
                    for chunk in chunks:
                        yield chunk
        except GitHubClientException as e:
            raise DocumentServiceException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing GitHub readme source.")
            raise DocumentServiceException(
                "Failed to create documents from GitHub readme"
            )

    async def create_documents(
        self,
        source_config: SourceConfig,
    ) -> AsyncGenerator[Document, None]:
        if source_config.type == SourceType.SITEMAP:
            async for doc in self.create_documents_from_sitemap(source_config):
                yield doc
        elif source_config.type == SourceType.GITHUB_ISSUES:
            async for doc in self.create_documents_from_github_issues(source_config):
                yield doc
        elif source_config.type == SourceType.GITHUB_README:
            async for doc in self.create_documents_from_github_readme(source_config):
                yield doc
        else:
            raise DocumentServiceException("Unsupported source type.")
