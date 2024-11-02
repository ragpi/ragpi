import logging
from types import TracebackType
from typing import AsyncGenerator, List, Type
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import uuid
import re
import html2text

from src.document.schemas import PageData

UNWANTED_TAGS = [
    "nav",
    "header",
    "footer",
    "script",
    "style",
    "aside",
    "iframe",
    "noscript",
    "svg",
    "img",
    "form",
    "button",
    "input",
    "textarea",
    "select",
    "video",
    "audio",
]


def extract_page_data(url: str, content: bytes) -> PageData:
    page_id = str(uuid.uuid4())
    soup = BeautifulSoup(content, "html.parser")
    title = soup.title.string if soup.title and soup.title.string else url

    main_content = soup.main or soup.body

    if main_content:
        for unwanted in main_content.find_all(UNWANTED_TAGS):
            unwanted.decompose()
        page_content = html2text.html2text(str(main_content))
    else:
        page_content = html2text.html2text(str(soup))

    return PageData(id=page_id, url=url, title=title, content=page_content)


class SitemapCrawler:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        if self.session:
            await self.session.close()

    async def parse_sitemap(self, sitemap_url: str) -> List[str]:
        if not self.session:
            raise ValueError("Session is not initialized")

        async with self.session.get(sitemap_url) as response:
            if response.status == 404:
                raise ValueError(f"Sitemap not found at {sitemap_url}")

            response.raise_for_status()

            sitemap_xml = await response.text()
            soup = BeautifulSoup(sitemap_xml, "xml")
            urls = [loc.text for loc in soup.find_all("loc")]
            return urls

    async def fetch_page(self, url: str) -> PageData | None:
        if not self.session:
            raise ValueError("Session is not initialized")

        max_retries = 5
        retry_count = 0
        backoff = 1  # 1 second

        while retry_count <= max_retries:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        return extract_page_data(url, content)
                    elif response.status == 404:
                        logging.error(f"Page not found at {url}")
                        return None
                    elif response.status == 429:
                        logging.warning(
                            f"Rate limit exceeded when fetching {url}. Retrying in {backoff} seconds..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        retry_count += 1
                    else:
                        response.raise_for_status()
            except aiohttp.ClientError as e:
                logging.error(
                    f"Error fetching {url}: {e}. Retrying in {backoff} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff *= 2
                retry_count += 1
        logging.error(f"Failed to fetch {url} after {max_retries} retries.")
        return None

    async def crawl(
        self,
        sitemap_url: str,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
    ) -> AsyncGenerator[PageData, None]:
        urls = await self.parse_sitemap(sitemap_url)

        if not urls:
            raise ValueError("No URLs were found in the sitemap")

        if include_pattern:
            include_regex = re.compile(include_pattern)
            urls = [url for url in urls if include_regex.search(url)]

            if not urls:
                raise ValueError("No URLs matched the include pattern")

        if exclude_pattern:
            exclude_regex = re.compile(exclude_pattern)
            urls = [url for url in urls if not exclude_regex.search(url)]

            if not urls:
                raise ValueError("All URLs matched the exclude pattern")

        MAX_CONCURRENT_REQUESTS = 10
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_page(url)

        tasks = [asyncio.create_task(fetch_with_semaphore(url)) for url in urls]

        for task in asyncio.as_completed(tasks):
            page_data = await task
            if page_data:
                yield page_data
