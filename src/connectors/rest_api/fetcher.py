import json
import logging
from typing import Any, AsyncGenerator

import aiohttp

from src.connectors.exceptions import ConnectorException
from src.connectors.rest_api.config import RestApiConfig
from src.connectors.rest_api.schemas import RestApiDocument

logger = logging.getLogger(__name__)


class RestApiFetcher:
    """Fetches data from REST API endpoints."""

    def __init__(self, config: RestApiConfig, user_agent: str):
        self.config = config
        self.user_agent = user_agent

    def _extract_nested_value(self, data: Any, path: str) -> Any:
        """Extract value from nested dictionary using dot notation path.

        Args:
            data: The data structure to extract from
            path: Dot-separated path (e.g., 'data.items')

        Returns:
            The extracted value

        Raises:
            ConnectorException: If the path cannot be found
        """
        current = data
        parts = path.split(".")

        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise ConnectorException(
                        f"JSON path '{path}' not found in response. "
                        f"Missing key: '{part}'"
                    )
                current = current[part]
            else:
                raise ConnectorException(
                    f"Cannot navigate path '{path}'. "
                    f"Expected dict at '{part}', got {type(current).__name__}"
                )

        return current

    def _extract_documents_from_response(
        self, response_data: Any
    ) -> list[RestApiDocument]:
        """Extract documents from API response data.

        Args:
            response_data: The JSON response data from the API

        Returns:
            List of RestApiDocument objects

        Raises:
            ConnectorException: If data cannot be extracted properly
        """
        # If json_path is specified, navigate to that part of the response
        if self.config.json_path:
            data = self._extract_nested_value(response_data, self.config.json_path)
        else:
            data = response_data

        # Ensure data is a list
        if not isinstance(data, list):
            # If it's a single object, wrap it in a list
            data = [data]

        documents = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning(
                    f"Skipping item at index {idx}: expected dict, got {type(item).__name__}"
                )
                continue

            # Extract title
            title = item.get(self.config.title_field)
            if not title:
                logger.warning(
                    f"Item at index {idx} missing '{self.config.title_field}' field, "
                    f"using index as title"
                )
                title = f"Document {idx + 1}"

            # Extract content
            content = item.get(self.config.content_field)
            if not content:
                # If content field is missing, serialize the entire item as JSON
                logger.info(
                    f"Item at index {idx} missing '{self.config.content_field}' field, "
                    f"using entire item as content"
                )
                content = json.dumps(item, indent=2)
            elif not isinstance(content, str):
                # If content is not a string, serialize it
                content = json.dumps(content, indent=2)

            # Extract URL
            if self.config.url_field and self.config.url_field in item:
                url = item[self.config.url_field]
            else:
                url = self.config.url

            # Store remaining fields as metadata
            metadata = {
                k: v
                for k, v in item.items()
                if k not in [self.config.title_field, self.config.content_field, self.config.url_field]
            }

            documents.append(
                RestApiDocument(
                    url=url,
                    title=str(title),
                    content=content,
                    metadata=metadata,
                )
            )

        return documents

    async def fetch_documents(self) -> AsyncGenerator[RestApiDocument, None]:
        """Fetch documents from the REST API endpoint.

        Yields:
            RestApiDocument objects

        Raises:
            ConnectorException: If the request fails or data cannot be parsed
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        # Merge custom headers if provided
        if self.config.headers:
            headers.update(self.config.headers)

        try:
            async with aiohttp.ClientSession() as session:
                logger.info(
                    f"Sending {self.config.method} request to {self.config.url}"
                )

                if self.config.method == "GET":
                    async with session.get(
                        self.config.url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as response:
                        response.raise_for_status()
                        response_data = await response.json()
                elif self.config.method == "POST":
                    async with session.post(
                        self.config.url,
                        headers=headers,
                        json=self.config.body,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as response:
                        response.raise_for_status()
                        response_data = await response.json()
                else:
                    raise ConnectorException(f"Unsupported HTTP method: {self.config.method}")

                logger.info(f"Successfully fetched data from {self.config.url}")

                # Extract documents from response
                documents = self._extract_documents_from_response(response_data)
                logger.info(f"Extracted {len(documents)} documents from response")

                # Yield each document
                for doc in documents:
                    yield doc

        except aiohttp.ClientError as e:
            raise ConnectorException(
                f"Failed to fetch data from {self.config.url}: {str(e)}"
            ) from e
        except json.JSONDecodeError as e:
            raise ConnectorException(
                f"Failed to parse JSON response from {self.config.url}: {str(e)}"
            ) from e
        except Exception as e:
            raise ConnectorException(
                f"Unexpected error while fetching from {self.config.url}: {str(e)}"
            ) from e
