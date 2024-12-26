import pytest
from unittest.mock import AsyncMock, patch
from src.document_extractor.clients.github_issue import GitHubIssueClient
from src.document_extractor.clients.github_readme import GitHubReadmeClient
from src.document_extractor.clients.sitemap import SitemapClient
from src.document_extractor.schemas import GithubIssue, GithubIssueComment, MarkdownPage
from typing import AsyncGenerator


@pytest.fixture
def github_issue_client() -> GitHubIssueClient:
    return GitHubIssueClient(
        concurrent_requests=5,
        user_agent="test-agent",
        github_api_version="2022-11-28",
        github_token="test-token",
    )


@pytest.fixture
def github_readme_client() -> GitHubReadmeClient:
    return GitHubReadmeClient(
        user_agent="test-agent",
        github_api_version="2022-11-28",
        github_token="test-token",
    )


@pytest.fixture
def sitemap_client() -> SitemapClient:
    return SitemapClient(
        concurrent_requests=5,
        user_agent="test-agent",
    )


@pytest.mark.asyncio
async def test_fetch_comments(github_issue_client: GitHubIssueClient) -> None:
    comments_url = "http://example.com/comments"
    with patch.object(github_issue_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ([
            {"id": "1", "html_url": "http://example.com/comment/1", "body": "Comment 1"},
            {"id": "2", "html_url": "http://example.com/comment/2", "body": "Comment 2"},
        ], {})
        comments = await github_issue_client.fetch_comments(comments_url)
        assert len(comments) == 2
        assert all(isinstance(comment, GithubIssueComment) for comment in comments)


@pytest.mark.asyncio
async def test_fetch_issues(github_issue_client: GitHubIssueClient) -> None:
    repo_owner = "test-owner"
    repo_name = "test-repo"
    with patch.object(github_issue_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ([
            {"id": "1", "html_url": "http://example.com/issue/1", "title": "Issue 1", "body": "Body 1", "comments": 0},
            {"id": "2", "html_url": "http://example.com/issue/2", "title": "Issue 2", "body": "Body 2", "comments": 0},
        ], {})
        issues = [issue async for issue in github_issue_client.fetch_issues(repo_owner, repo_name)]
        assert len(issues) == 2
        assert all(isinstance(issue, GithubIssue) for issue in issues)


@pytest.mark.asyncio
async def test_fetch_readmes(github_readme_client: GitHubReadmeClient) -> None:
    repo_owner = "test-owner"
    repo_name = "test-repo"
    with patch.object(github_readme_client, "request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = ({"path": "README.md", "html_url": "http://example.com/readme", "content": "UmVhZG1lIGNvbnRlbnQ=", "encoding": "base64"}, {})
        readmes = [readme async for readme in github_readme_client.fetch_readmes(repo_owner, repo_name)]
        assert len(readmes) == 1
        assert all(isinstance(readme, MarkdownPage) for readme in readmes)


@pytest.mark.asyncio
async def test_fetch_sitemap_pages(sitemap_client: SitemapClient) -> None:
    sitemap_url = "http://example.com/sitemap.xml"
    with patch.object(sitemap_client, "parse_sitemap", new_callable=AsyncMock) as mock_parse_sitemap, \
         patch.object(sitemap_client, "fetch_page", new_callable=AsyncMock) as mock_fetch_page:
        mock_parse_sitemap.return_value = ["http://example.com/page1", "http://example.com/page2"]
        mock_fetch_page.return_value = MarkdownPage(url="http://example.com/page1", title="Page 1", content="Page 1 content")
        pages = [page async for page in sitemap_client.fetch_sitemap_pages(sitemap_url)]
        assert len(pages) == 2
        assert all(isinstance(page, MarkdownPage) for page in pages)
