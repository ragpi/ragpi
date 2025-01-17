import logging
from typing import AsyncIterator

from src.config import Settings
from src.common.schemas import Document
from src.extractors.exceptions import ExtractorException
from src.extractors.registry import ExtractorConfig, get_extractor_class

logger = logging.getLogger(__name__)


class ExtractorService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_documents(
        self,
        extractor_config: ExtractorConfig,
    ) -> AsyncIterator[Document]:
        try:
            extractor_class = get_extractor_class(extractor_config.type)
            extractor = extractor_class(self.settings, extractor_config)
            async for doc in extractor.extract():
                yield doc
        except ValueError as e:
            raise ExtractorException("Unsupported extractor type.") from e
