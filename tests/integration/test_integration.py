from typing import Any, Generator
from celery import Celery
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from testcontainers.redis import RedisContainer  # type: ignore
from src.config import Settings, get_settings
from src.main import app as main_app
from src.task.celery import celery_app

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    with RedisContainer(image="redis/redis-stack-server:latest") as redis:
        yield redis


@pytest.fixture(scope="session")
def test_settings(redis_container: RedisContainer) -> Settings:
    return Settings(
        REDIS_URL=f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}",
        OPENAI_API_KEY="test-key",
        GITHUB_TOKEN="test-token",
        API_KEYS=None,
        ENABLE_OTEL=False,
    )


@pytest.fixture(autouse=True)
def patch_settings(test_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.main.settings", test_settings)


@pytest.fixture(scope="session")
def celery_config(test_settings: Settings) -> dict[str, Any]:
    return {
        "broker_url": test_settings.REDIS_URL,
        "result_backend": test_settings.REDIS_URL,
        "broker_connection_retry_on_startup": True,
        "task_always_eager": False,
        "task_store_eager_result": True,
    }


@pytest.fixture(scope="session")
def celery_app_fixture(celery_config: dict[str, Any]) -> Celery:
    celery_app.conf.update(celery_config)
    return celery_app


@pytest.fixture
def test_app(test_settings: Settings, celery_app_fixture: Celery) -> FastAPI:
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


def test_healthcheck(test_client: TestClient) -> None:
    response = test_client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["api"]["status"] == "ok"
    assert health_data["redis"]["status"] == "ok"
    assert health_data["celery"]["status"] == "ok"
