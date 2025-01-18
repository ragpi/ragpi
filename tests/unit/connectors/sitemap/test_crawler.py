import pytest
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, Mock
from typing import AsyncGenerator
from urllib.robotparser import RobotFileParser

from src.connectors.exceptions import ConnectorException
from src.connectors.common.schemas import MarkdownPage
from src.connectors.sitemap.crawler import SitemapCrawler, extract_markdown_page


@pytest.fixture
def sample_html() -> bytes:
    return b"""
    <!DOCTYPE html>
    <html>
        <head><title>Test Page</title></head>
        <body>
            <main>
                <h1>Main Content</h1>
                <p>Test paragraph</p>
                <nav>Navigation</nav>
                <footer>Footer content</footer>
            </main>
        </body>
    </html>
    """


@pytest.fixture
def sample_sitemap_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/page1</loc></url>
        <url><loc>https://example.com/page2</loc></url>
    </urlset>"""


@pytest.fixture
def robots_txt() -> str:
    return """
    User-agent: *
    Allow: /page1
    Disallow: /page2
    """


@pytest.fixture
async def sitemap_client() -> AsyncGenerator[SitemapCrawler, None]:
    async with SitemapCrawler(concurrent_requests=2, user_agent="test-bot") as client:
        yield client


def test_extract_markdown_page(sample_html: bytes) -> None:
    url = "https://example.com"
    page = extract_markdown_page(url, sample_html)

    assert isinstance(page, MarkdownPage)
    assert page.url == url
    assert "Test Page" in page.title
    assert "Main Content" in page.content
    assert "Test paragraph" in page.content
    assert "Navigation" not in page.content
    assert "Footer content" not in page.content


async def test_fetch_robots_txt_success(
    mocker: MockerFixture, sitemap_client: SitemapCrawler, robots_txt: str
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = robots_txt

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    result = await sitemap_client.fetch_robots_txt("https://example.com")
    assert result == robots_txt


async def test_fetch_robots_txt_not_found(
    mocker: MockerFixture, sitemap_client: SitemapCrawler
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    result = await sitemap_client.fetch_robots_txt("https://example.com")
    assert result == ""


async def test_parse_sitemap_success(
    mocker: MockerFixture, sitemap_client: SitemapCrawler, sample_sitemap_xml: str
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = sample_sitemap_xml
    mock_response.raise_for_status = Mock()

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    urls = await sitemap_client.parse_sitemap("https://example.com/sitemap.xml")
    assert urls == ["https://example.com/page1", "https://example.com/page2"]


async def test_parse_sitemap_not_found(
    mocker: MockerFixture, sitemap_client: SitemapCrawler
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 404

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ConnectorException):
        await sitemap_client.parse_sitemap("https://example.com/sitemap.xml")


async def test_fetch_page_success(
    mocker: MockerFixture, sitemap_client: SitemapCrawler, sample_html: bytes
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = sample_html

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    robots_parser = RobotFileParser()
    mocker.patch.object(robots_parser, "can_fetch", return_value=True)

    page = await sitemap_client.fetch_page("https://example.com/page1", robots_parser)
    assert isinstance(page, MarkdownPage)
    assert page.url == "https://example.com/page1"
    assert "Test Page" in page.title


async def test_fetch_page_disallowed_by_robots(
    mocker: MockerFixture, sitemap_client: SitemapCrawler
) -> None:
    robots_parser = RobotFileParser()
    mocker.patch.object(robots_parser, "can_fetch", return_value=False)

    page = await sitemap_client.fetch_page("https://example.com/page2", robots_parser)
    assert page is None


async def test_fetch_sitemap_pages_with_filters(
    sitemap_client: SitemapCrawler,
    sample_sitemap_xml: str,
    sample_html: bytes,
    mocker: MockerFixture,
) -> None:
    # Mock sitemap response
    mock_sitemap_response = AsyncMock()
    mock_sitemap_response.status = 200
    mock_sitemap_response.text.return_value = sample_sitemap_xml
    mock_sitemap_response.raise_for_status = Mock()

    # Mock page response
    mock_page_response = AsyncMock()
    mock_page_response.status = 200
    mock_page_response.read.return_value = sample_html
    mock_page_response.raise_for_status = Mock()

    # Mock session get calls
    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.side_effect = [
        mock_sitemap_response,  # First call for sitemap
        mock_page_response,  # Second call for page2
    ]

    mock_robots_txt = """
    User-agent: *
    Allow: /
    """

    # Mock robots.txt response
    mocker.patch.object(
        sitemap_client, "fetch_robots_txt", return_value=mock_robots_txt
    )

    pages: list[MarkdownPage] = []
    async for page in sitemap_client.fetch_sitemap_pages(
        "https://example.com/sitemap.xml",
        include_pattern="page2",
    ):
        pages.append(page)

    assert len(pages) == 1
    assert pages[0].url == "https://example.com/page2"
    assert "Test Page" in pages[0].title


async def test_fetch_sitemap_pages_no_matching_urls(
    mocker: MockerFixture, sitemap_client: SitemapCrawler, sample_sitemap_xml: str
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = sample_sitemap_xml
    mock_response.raise_for_status = Mock()

    mock_session = mocker.patch.object(sitemap_client.session, "get")
    mock_session.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ConnectorException):
        async for _ in sitemap_client.fetch_sitemap_pages(
            "https://example.com/sitemap.xml", include_pattern="page3"
        ):
            pass
