import logging
from typing import AsyncGenerator

from src.config import Settings
from src.common.schemas import Document
from src.sources.common.exceptions import DocumentExtractorException
from src.sources.github_issues.extractor import extract_documents_from_github_issues
from src.sources.github_readme.extractor import extract_documents_from_github_readme
from src.sources.sitemap.extractor import extract_documents_from_sitemap
from src.sources.types import SourceType
from src.sources.registry import SourceConfig

logger = logging.getLogger(__name__)


class DocumentExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_documents(
        self,
        source_config: SourceConfig,
    ) -> AsyncGenerator[Document, None]:
        if source_config.type == SourceType.SITEMAP:
            async for doc in extract_documents_from_sitemap(
                source_config=source_config,
                concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
                user_agent=self.settings.USER_AGENT,
                document_uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
            ):
                yield doc
        elif source_config.type == SourceType.GITHUB_ISSUES:
            async for doc in extract_documents_from_github_issues(
                source_config=source_config,
                concurrent_requests=self.settings.MAX_CONCURRENT_REQUESTS,
                user_agent=self.settings.USER_AGENT,
                github_api_version=self.settings.GITHUB_API_VERSION,
                github_token=self.settings.GITHUB_TOKEN,
                document_uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
            ):
                yield doc
        elif source_config.type == SourceType.GITHUB_README:
            async for doc in extract_documents_from_github_readme(
                source_config=source_config,
                user_agent=self.settings.USER_AGENT,
                github_api_version=self.settings.GITHUB_API_VERSION,
                github_token=self.settings.GITHUB_TOKEN,
                document_uuid_namespace=self.settings.DOCUMENT_UUID_NAMESPACE,
            ):
                yield doc
        else:
            raise DocumentExtractorException("Unsupported source type.")
