from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.common.schemas import Document
from src.config import Settings
from src.connectors.base.config import BaseConnectorConfig


class BaseConnector(ABC):
    """Base class for all connectors"""

    def __init__(self, settings: Settings, config: BaseConnectorConfig):
        self.settings = settings
        self.config = config

    @abstractmethod
    def extract(self) -> AsyncGenerator[Document, None]:
        """Extract and yield documents"""
        pass
