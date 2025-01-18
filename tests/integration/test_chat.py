from typing import Any, Callable
import pytest
from fastapi.testclient import TestClient

from tests.integration.utils import wait_for_task_status


class TestChat:
    @pytest.fixture
    def create_source(self, test_client: TestClient) -> Callable[[str], dict[str, Any]]:
        """Create a test source and wait for sync completion."""

        def _create_source(name: str) -> dict[str, Any]:
            response = test_client.post(
                "/sources",
                json={
                    "name": name,
                    "description": "Test source for chat",
                    "connector": {
                        "type": "sitemap",
                        "sitemap_url": "https://gateweaver.io/sitemap.xml",
                        "include_pattern": "https://gateweaver.io/docs/getting-started",
                    },
                },
            )
            data = response.json()
            wait_for_task_status(test_client, data["task_id"], "SUCCESS")
            return data["source"]

        return _create_source

    def test_chat_with_source(
        self, test_client: TestClient, create_source: Callable[[str], dict[str, Any]]
    ) -> None:
        """Test successful chat interaction with a source."""
        create_source("chat-test")

        response = test_client.post(
            "/chat",
            json={
                "sources": ["chat-test"],
                "messages": [{"role": "user", "content": "What is the project about?"}],
            },
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_chat_with_all_sources(
        self, test_client: TestClient, create_source: Callable[[str], dict[str, Any]]
    ) -> None:
        """Test chat with all sources."""
        create_source("test-source-1")
        create_source("test-source-2")

        response = test_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "What are the key features?"}],
            },
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_chat_with_nonexistent_source(self, test_client: TestClient) -> None:
        """Test chat with a non-existent source."""
        response = test_client.post(
            "/chat",
            json={
                "sources": ["nonexistent-source"],
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_chat_with_conversation_history(
        self, test_client: TestClient, create_source: Callable[[str], dict[str, Any]]
    ) -> None:
        """Test chat with conversation history."""
        create_source("chat-history-test")

        response = test_client.post(
            "/chat",
            json={
                "sources": ["chat-history-test"],
                "messages": [
                    {"role": "user", "content": "What is the project about?"},
                    {"role": "assistant", "content": "It's a RAG system."},
                    {
                        "role": "user",
                        "content": "Can you tell me more about its features?",
                    },
                ],
            },
        )
        assert response.status_code == 200
        assert "message" in response.json()
