import logging
from typing import AsyncGenerator
from src.config import Settings
from src.document_extractor.chunker import Chunker
from src.document_extractor.clients.github_issue import GitHubIssueClient
from src.document_extractor.clients.github_readme import GitHubReadmeClient
from src.document_extractor.exceptions import (
    DocumentExtractorException,
    GitHubClientException,
    SitemapClientException,
)
from src.document_extractor.clients.sitemap import SitemapClient
from src.common.schemas import Document
from src.source.config import (
    GithubIssuesConfig,
    GithubReadmeConfig,
    SitemapConfig,
    SourceConfig,
    SourceType,
)


class DocumentExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_documents_from_sitemap(
        self, config: SitemapConfig
    ) -> AsyncGenerator[Document, None]:
        try:
            async with SitemapClient(
                concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
                user_agent=self.settings.USER_AGENT,
            ) as client:
                chunker = Chunker(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
                )

                async for page in client.fetch_sitemap_pages(
                    sitemap_url=config.sitemap_url,
                    include_pattern=config.include_pattern,
                    exclude_pattern=config.exclude_pattern,
                ):
                    chunks = chunker.chunk_markdown_page(page)
                    for chunk in chunks:
                        yield chunk
        except SitemapClientException as e:
            raise DocumentExtractorException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing sitemap source.")
            raise DocumentExtractorException("Failed to create documents from sitemap")

    async def extract_documents_from_github_issues(
        self,
        config: GithubIssuesConfig,
    ) -> AsyncGenerator[Document, None]:
        try:
            async with GitHubIssueClient(
                concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
                user_agent=self.settings.USER_AGENT,
                github_api_version=self.settings.GITHUB_API_VERSION,
                github_token=self.settings.GITHUB_TOKEN,
            ) as client:
                chunker = Chunker(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
                )
                async for issue in client.fetch_issues(
                    repo_owner=config.repo_owner,
                    repo_name=config.repo_name,
                    state=config.state,
                    include_labels=config.include_labels,
                    exclude_labels=config.exclude_labels,
                    max_age=config.max_age,
                ):
                    chunks = chunker.chunk_github_issue(issue)
                    for chunk in chunks:
                        yield chunk
        except GitHubClientException as e:
            raise DocumentExtractorException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing GitHub issues source.")
            raise DocumentExtractorException(
                "Failed to create documents from GitHub issues"
            )

    async def extract_documents_from_github_readme(
        self,
        config: GithubReadmeConfig,
    ) -> AsyncGenerator[Document, None]:
        try:
            async with GitHubReadmeClient(
                user_agent=self.settings.USER_AGENT,
                github_api_version=self.settings.GITHUB_API_VERSION,
                github_token=self.settings.GITHUB_TOKEN,
            ) as client:
                chunker = Chunker(
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
                )

                async for page in client.fetch_readmes(
                    repo_owner=config.repo_owner,
                    repo_name=config.repo_name,
                    include_root=config.include_root,
                    sub_dirs=config.sub_dirs,
                ):
                    chunks = chunker.chunk_markdown_page(page)
                    for chunk in chunks:
                        yield chunk
        except GitHubClientException as e:
            raise DocumentExtractorException(str(e))
        except Exception as e:
            logging.exception("Unexpected error while processing GitHub readme source.")
            raise DocumentExtractorException(
                "Failed to create documents from GitHub readme"
            )

    async def extract_documents(
        self,
        source_config: SourceConfig,
    ) -> AsyncGenerator[Document, None]:
        if source_config.type == SourceType.SITEMAP:
            async for doc in self.extract_documents_from_sitemap(source_config):
                yield doc
        elif source_config.type == SourceType.GITHUB_ISSUES:
            async for doc in self.extract_documents_from_github_issues(source_config):
                yield doc
        elif source_config.type == SourceType.GITHUB_README:
            async for doc in self.extract_documents_from_github_readme(source_config):
                yield doc
        else:
            raise DocumentExtractorException("Unsupported source type.")
