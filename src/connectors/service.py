import logging
from typing import AsyncIterator

from src.config import Settings
from src.connectors.common.schemas import ExtractedDocument
from src.connectors.exceptions import ConnectorException
from src.connectors.registry import ConnectorConfig, get_connector_class

logger = logging.getLogger(__name__)


class ConnectorService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_documents(
        self,
        connector_config: ConnectorConfig,
    ) -> AsyncIterator[ExtractedDocument]:
        try:
            connector_class = get_connector_class(connector_config.type)
            connector = connector_class(self.settings, connector_config)
            async for doc in connector.extract():
                yield doc
        except ValueError as e:
            raise ConnectorException("Unsupported connector type.") from e
