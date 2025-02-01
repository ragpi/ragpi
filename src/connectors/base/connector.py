from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.config import Settings
from src.connectors.base.config import BaseConnectorConfig
from src.connectors.common.schemas import ExtractedDocument


class BaseConnector(ABC):
    """Base class for all connectors"""

    def __init__(self, settings: Settings, config: BaseConnectorConfig):
        self.settings = settings
        self.config = config

    @abstractmethod
    def extract(self) -> AsyncGenerator[ExtractedDocument, None]:
        """Extract and yield documents"""
        pass
