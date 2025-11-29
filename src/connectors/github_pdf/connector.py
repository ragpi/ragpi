from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.connector import BaseConnector
from src.connectors.common.github_client import GitHubClient
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.github_pdf.config import GithubPdfConfig
from src.connectors.github_pdf.fetcher import GitHubPdfFetcher
from src.connectors.github_pdf.chunker import chunk_pdf_document


class GithubPdfConnector(BaseConnector):
    config: GithubPdfConfig

    def __init__(self, settings: Settings, config: GithubPdfConfig):
        super().__init__(settings, config)

    async def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        async with GitHubClient(
            concurrent_requests=1,
            user_agent=self.settings.USER_AGENT,
            github_api_version=self.settings.GITHUB_API_VERSION,
            github_token=self.settings.GITHUB_TOKEN,
        ) as github_client:
            pdf_fetcher = GitHubPdfFetcher(github_client=github_client)

            async for pdf_doc in pdf_fetcher.fetch_pdfs(
                repo_owner=self.config.repo_owner,
                repo_name=self.config.repo_name,
                ref=self.config.ref,
                path_filter=self.config.path_filter,
            ):
                chunks = chunk_pdf_document(
                    pdf_doc=pdf_doc,
                    chunk_size=self.settings.CHUNK_SIZE,
                    chunk_overlap=self.settings.CHUNK_OVERLAP,
                )
                for chunk in chunks:
                    yield chunk
