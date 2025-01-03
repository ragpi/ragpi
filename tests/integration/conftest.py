import os
from typing import Any, Generator
from unittest.mock import Mock
import pytest
from celery import Celery
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from testcontainers.redis import RedisContainer  # type: ignore
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.embedding import Embedding
from openai.types.create_embedding_response import CreateEmbeddingResponse, Usage

from src.config import Settings, get_settings
from src.main import app as main_app
from src.task.celery import celery_app


def pytest_sessionstart(session: pytest.Session) -> None:
    if not os.getenv("GITHUB_TOKEN"):
        pytest.exit(
            "Error: GITHUB_TOKEN environment variable is not set. Please set it before running the integration tests."
        )


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    with RedisContainer(image="redis/redis-stack-server:latest") as redis:
        yield redis


@pytest.fixture(scope="session")
def test_settings(redis_container: RedisContainer) -> Settings:
    return Settings(
        REDIS_URL=(
            f"redis://{redis_container.get_container_host_ip()}:"
            f"{redis_container.get_exposed_port(6379)}"
        ),
        OPENAI_API_KEY="test-key",
        GITHUB_TOKEN=os.getenv("GITHUB_TOKEN", ""),
        API_KEYS=None,
        ENABLE_OTEL=False,
    )


@pytest.fixture
def mock_openai_chat(mocker: MockerFixture) -> Mock:
    return mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=ChatCompletion(
            id="test-id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="Test response",
                        role="assistant",
                    ),
                )
            ],
            created=1234567890,
            model="gpt-4",
            object="chat.completion",
        ),
    )


@pytest.fixture
def mock_openai_embeddings(mocker: MockerFixture) -> Mock:
    return mocker.patch(
        "openai.resources.embeddings.Embeddings.create",
        return_value=CreateEmbeddingResponse(
            data=[Embedding(embedding=[0.1] * 1536, index=0, object="embedding")],
            model="text-embedding-3-small",
            object="list",
            usage=Usage(prompt_tokens=1, total_tokens=1),
        ),
    )


@pytest.fixture(autouse=True)
def patch_settings(test_settings: Settings, mocker: MockerFixture) -> None:
    mocker.patch("src.main.settings", test_settings)
    mocker.patch("src.task.sync_source.get_settings", lambda: test_settings)


@pytest.fixture(scope="session")
def celery_config(test_settings: Settings) -> dict[str, Any]:
    return {
        "broker_url": test_settings.REDIS_URL,
        "result_backend": test_settings.REDIS_URL,
        "broker_connection_retry_on_startup": True,
        "task_always_eager": False,
    }


# @pytest.fixture(scope="session")
# def celery_worker_pool():
#     return "prefork"


@pytest.fixture(scope="session")
def celery_app_fixture(celery_config: dict[str, Any]) -> Celery:
    celery_app.conf.update(celery_config)
    return celery_app


@pytest.fixture
def test_app(
    test_settings: Settings,
    celery_app_fixture: Celery,
    mock_openai_chat: Mock,
    mock_openai_embeddings: Mock,
) -> FastAPI:
    def get_test_settings() -> Settings:
        return test_settings

    main_app.dependency_overrides[get_settings] = get_test_settings
    return main_app


@pytest.fixture
def test_client(
    test_app: FastAPI, celery_worker: None
) -> Generator[TestClient, None, None]:
    with TestClient(test_app) as client:
        yield client
