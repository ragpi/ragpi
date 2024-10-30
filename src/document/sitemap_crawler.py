import requests
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
        self.collected_pages: list[PageData] = []

    def parse_sitemap(self, sitemap_url: str) -> list[str]:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        sitemap_xml = response.text
        soup = BeautifulSoup(sitemap_xml, "xml")
        urls = [loc.text for loc in soup.find_all("loc")]
        return urls

    def fetch_page(self, url: str) -> PageData:
        response = requests.get(url)
        response.raise_for_status()
        return extract_page_data(url, response.content)

    def crawl(
        self,
        sitemap_url: str,
        include_pattern: str | None = None,
        exclude_pattern: str | None = None,
    ) -> list[PageData]:
        urls = self.parse_sitemap(sitemap_url)

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

        for url in urls:
            try:
                page_data = self.fetch_page(url)
                self.collected_pages.append(page_data)
            except Exception as e:
                print(f"Error fetching {url}: {e}")

        if not self.collected_pages:
            raise ValueError("No pages were collected during crawl")

        return self.collected_pages
