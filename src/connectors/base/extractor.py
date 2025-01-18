from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.common.schemas import Document
from src.config import Settings
from src.connectors.base.config import BaseExtractorConfig


class BaseExtractor(ABC):
    """Base class for all extractors"""

    def __init__(self, settings: Settings, config: BaseExtractorConfig):
        self.settings = settings
        self.config = config

    @abstractmethod
    def extract(self) -> AsyncGenerator[Document, None]:
        """Extract and yield documents"""
        pass
