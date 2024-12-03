from typing import AsyncGenerator
from src.document.chunker import split_markdown_page
from src.document.github_issues_crawler import GitHubIssueCrawler
from src.document.schemas import Document
from src.document.sitemap_crawler import SitemapCrawler
from src.source.schemas import SourceConfig, SourceType


class DocumentService:
    async def create_documents_from_sitemap(
        self,
        sitemap_url: str,
        include_pattern: str | None,
        exclude_pattern: str | None,
        chunk_size: int,
        chunk_overlap: int,
    ) -> AsyncGenerator[Document, None]:
        async with SitemapCrawler() as crawler:
            async for page in crawler.crawl(
                sitemap_url=sitemap_url,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
            ):
                chunks = split_markdown_page(page, chunk_size, chunk_overlap)
                for chunk in chunks:
                    yield chunk

    async def create_documents_from_github_issues(
        self,
        repo: str,
        state: str | None = None,
        include_labels: list[str] | None = None,
        exclude_labels: list[str] | None = None,
        max_age: int | None = None,
    ) -> AsyncGenerator[Document, None]:
        async with GitHubIssueCrawler() as crawler:
            async for issue in crawler.fetch_issues(
                repo, state, include_labels, exclude_labels, max_age
            ):
                yield Document(
                    id=issue.id,
                    content=issue.body,
                    metadata={
                        "url": issue.url,
                        "title": issue.title,
                        "comments": issue.comments,
                    },
                )

    async def create_documents(
        self,
        source_config: SourceConfig,
    ) -> AsyncGenerator[Document, None]:
        if source_config.type == SourceType.SITEMAP:
            async for doc in self.create_documents_from_sitemap(
                sitemap_url=source_config.sitemap_url,
                include_pattern=source_config.include_pattern,
                exclude_pattern=source_config.exclude_pattern,
                chunk_size=source_config.chunk_size,
                chunk_overlap=source_config.chunk_overlap,
            ):
                yield doc
        elif source_config.type == SourceType.GITHUB_ISSUES:
            async for doc in self.create_documents_from_github_issues(
                repo=source_config.repo,
                state=source_config.state,
                include_labels=source_config.include_labels,
                exclude_labels=source_config.exclude_labels,
                max_age=source_config.max_age,
            ):
                yield doc
