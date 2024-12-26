import pytest
from src.document_extractor.chunker import Chunker
from src.document_extractor.service import DocumentExtractor
from src.document_extractor.schemas import GithubIssue, MarkdownPage
from src.common.schemas import Document
from src.config import Settings
from unittest.mock import AsyncMock, patch
from datetime import datetime


@pytest.fixture
def chunker() -> Chunker:
    return Chunker(chunk_size=512, chunk_overlap=50, uuid_namespace="test-namespace")


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def document_extractor(settings: Settings) -> DocumentExtractor:
    return DocumentExtractor(settings=settings)


def test_chunk_markdown_page(chunker: Chunker) -> None:
    page_data = MarkdownPage(
        title="Test Page",
        url="http://example.com",
        content="# Header 1\n## Header 2\n### Header 3\nContent"
    )
    chunks = chunker.chunk_markdown_page(page_data)
    assert len(chunks) > 0
    assert all(isinstance(chunk, Document) for chunk in chunks)


def test_chunk_github_issue(chunker: Chunker) -> None:
    issue = GithubIssue(
        id="1",
        url="http://example.com/issue/1",
        title="Test Issue",
        body="Issue body content",
        comments=[]
    )
    chunks = chunker.chunk_github_issue(issue)
    assert len(chunks) > 0
    assert all(isinstance(chunk, Document) for chunk in chunks)


@pytest.mark.asyncio
async def test_extract_documents_from_sitemap(document_extractor: DocumentExtractor) -> None:
    config = {
        "sitemap_url": "http://example.com/sitemap.xml",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "include_pattern": None,
        "exclude_pattern": None
    }
    with patch("src.document_extractor.clients.sitemap.SitemapClient.fetch_sitemap_pages", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = AsyncMock()
        async for doc in document_extractor.extract_documents_from_sitemap(config):
            assert isinstance(doc, Document)


@pytest.mark.asyncio
async def test_extract_documents_from_github_issues(document_extractor: DocumentExtractor) -> None:
    config = {
        "repo_owner": "test-owner",
        "repo_name": "test-repo",
        "state": "all",
        "include_labels": None,
        "exclude_labels": None,
        "max_age": None,
        "chunk_size": 512,
        "chunk_overlap": 50
    }
    with patch("src.document_extractor.clients.github_issue.GitHubIssueClient.fetch_issues", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = AsyncMock()
        async for doc in document_extractor.extract_documents_from_github_issues(config):
            assert isinstance(doc, Document)


@pytest.mark.asyncio
async def test_extract_documents_from_github_readme(document_extractor: DocumentExtractor) -> None:
    config = {
        "repo_owner": "test-owner",
        "repo_name": "test-repo",
        "include_root": True,
        "sub_dirs": None,
        "chunk_size": 512,
        "chunk_overlap": 50
    }
    with patch("src.document_extractor.clients.github_readme.GitHubReadmeClient.fetch_readmes", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = AsyncMock()
        async for doc in document_extractor.extract_documents_from_github_readme(config):
            assert isinstance(doc, Document)
